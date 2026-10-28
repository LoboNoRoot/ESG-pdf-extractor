from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List

from openai import OpenAI

TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]")
SOURCE_BONUS = {
    "mineru": 0.35,
    "pymupdf_layout": 0.25,
}


def tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def _field_terms(field: Dict[str, Any]) -> List[str]:
    terms: List[str] = []
    for key in ["name_cn", "field_key", "topic", "domain_knowledge"]:
        value = field.get(key)
        if value:
            terms.append(str(value))
    for key in ["aliases", "search_terms", "required_any", "expected_units", "unit_examples"]:
        values = field.get(key) or []
        if isinstance(values, list):
            terms.extend(str(item) for item in values if item)
    return terms


def _field_match_score(text: str, field: Dict[str, Any]) -> float:
    lowered = (text or "").lower()
    penalty = 0.0
    for term in field.get("forbidden_any") or []:
        value = str(term or "").strip().lower()
        if value and value in lowered:
            penalty += 8.0
    score = 0.0
    for key, weight in [
        ("name_cn", 8.0),
        ("aliases", 6.0),
        ("required_any", 5.0),
        ("search_terms", 4.0),
        ("unit_examples", 1.0),
        ("expected_units", 1.0),
    ]:
        values = field.get(key) if key != "name_cn" else [field.get("name_cn")]
        if not isinstance(values, list):
            values = [values]
        for value in values:
            term = str(value or "").strip().lower()
            if len(term) >= 2 and term in lowered:
                score += weight + min(len(term), 12) / 10
    return score - penalty


def _dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for item in results:
        normalized = re.sub(r"\s+", "", str(item.get("text") or ""))[:220]
        if normalized and normalized in seen:
            continue
        if normalized:
            seen.add(normalized)
        deduped.append(item)
    return deduped


def _rerank_field_results(results: List[Dict[str, Any]], field: Dict[str, Any], *, top_k: int) -> List[Dict[str, Any]]:
    reranked: List[Dict[str, Any]] = []
    for item in results:
        candidate = dict(item)
        candidate["field_match_score"] = round(_field_match_score(str(candidate.get("text") or ""), field), 3)
        if candidate["field_match_score"] <= -1000:
            continue
        reranked.append(candidate)
    reranked.sort(
        key=lambda item: (
            item.get("field_match_score", 0),
            len(set(item.get("retrieval_sources", []))) if isinstance(item.get("retrieval_sources"), list) else 0,
            float(item.get("score") or 0),
        ),
        reverse=True,
    )
    return _dedupe_results(reranked)[:top_k]


def _exact_field_candidates(chunks: List[Dict[str, Any]], field: Dict[str, Any], *, limit: int = 30) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for chunk in chunks:
        field_score = _field_match_score(str(chunk.get("text") or ""), field)
        if field_score <= 0:
            continue
        item = dict(chunk)
        item["score"] = round(field_score / 100, 6)
        item["retrieval_source"] = "field_exact"
        item["retrieval_sources"] = ["field_exact"]
        candidates.append(item)
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:limit]


class SimpleRetriever:
    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        self.doc_tokens = [tokenize(item.get("text", "")) for item in chunks]
        self.doc_freq: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            self.doc_freq.update(set(tokens))
        self.total_docs = max(len(chunks), 1)
        self.avg_len = sum(len(tokens) for tokens in self.doc_tokens) / self.total_docs if chunks else 1.0

    def _idf(self, token: str) -> float:
        return math.log(1 + (self.total_docs - self.doc_freq.get(token, 0) + 0.5) / (self.doc_freq.get(token, 0) + 0.5))

    def search(self, query: str, *, top_k: int = 5) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        query_counts = Counter(query_tokens)
        scored: List[Dict[str, Any]] = []
        for chunk, tokens in zip(self.chunks, self.doc_tokens):
            if not tokens:
                continue
            counts = Counter(tokens)
            score = 0.0
            for token, qf in query_counts.items():
                tf = counts.get(token, 0)
                if tf == 0:
                    continue
                denom = tf + 1.5 * (1 - 0.75 + 0.75 * len(tokens) / max(self.avg_len, 1.0))
                score += self._idf(token) * tf * 2.5 / denom * min(qf, 3)
            text = chunk.get("text", "")
            for raw_term in set(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9 ]{2,}", query)):
                if raw_term and raw_term in text:
                    score += 2.0
            score += SOURCE_BONUS.get(str(chunk.get("source") or ""), 0.0)
            if score > 0:
                item = dict(chunk)
                item["score"] = round(score, 4)
                scored.append(item)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def search_field(self, field: Dict[str, Any], *, top_k: int = 5) -> List[Dict[str, Any]]:
        pool = self.search(" ".join(_field_terms(field)), top_k=max(top_k * 4, 20))
        pool.extend(_exact_field_candidates(self.chunks, field, limit=max(top_k * 3, 20)))
        return _rerank_field_results(pool, field, top_k=top_k)


class LocalVectorRetriever:
    """Dependency-free vector-style retriever for hybrid recall experiments.

    This is intentionally local and deterministic: it builds TF-IDF weighted
    character n-gram vectors, then ranks chunks by cosine similarity. It is not
    a replacement for embedding/FAISS recall, but it gives the pipeline a safe
    hybrid retrieval test path without adding network calls or model cost.
    """

    def __init__(self, chunks: List[Dict[str, Any]], *, min_n: int = 2, max_n: int = 4):
        self.chunks = chunks
        self.min_n = min_n
        self.max_n = max_n
        self.doc_vectors = [self._vectorize(item.get("text", "")) for item in chunks]
        self.doc_freq: Counter[str] = Counter()
        for vector in self.doc_vectors:
            self.doc_freq.update(vector.keys())
        self.total_docs = max(len(chunks), 1)
        self.weighted_doc_vectors = [self._apply_idf(vector) for vector in self.doc_vectors]

    def _features(self, text: str) -> List[str]:
        features: List[str] = []
        for segment in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", (text or "").lower()):
            if re.fullmatch(r"[A-Za-z0-9]+", segment):
                features.append(f"tok:{segment}")
                for n in range(self.min_n, self.max_n + 1):
                    if len(segment) < n:
                        continue
                    features.extend(f"en:{segment[index:index + n]}" for index in range(0, len(segment) - n + 1))
                continue
            for n in range(self.min_n, self.max_n + 1):
                if len(segment) < n:
                    continue
                features.extend(f"zh:{segment[index:index + n]}" for index in range(0, len(segment) - n + 1))
        return features

    def _vectorize(self, text: str) -> Counter[str]:
        return Counter(self._features(text))

    def _idf(self, feature: str) -> float:
        return math.log(1 + (self.total_docs + 1) / (self.doc_freq.get(feature, 0) + 1))

    def _apply_idf(self, vector: Counter[str]) -> Dict[str, float]:
        return {feature: count * self._idf(feature) for feature, count in vector.items()}

    @staticmethod
    def _cosine(left: Dict[str, float], right: Dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        common = set(left).intersection(right)
        numerator = sum(left[key] * right[key] for key in common)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    def search(self, query: str, *, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self._apply_idf(self._vectorize(query))
        if not query_vector:
            return []
        scored: List[Dict[str, Any]] = []
        for chunk, vector in zip(self.chunks, self.weighted_doc_vectors):
            score = self._cosine(query_vector, vector)
            score += SOURCE_BONUS.get(str(chunk.get("source") or ""), 0.0)
            if score > 0:
                item = dict(chunk)
                item["score"] = round(score, 4)
                scored.append(item)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def search_field(self, field: Dict[str, Any], *, top_k: int = 5) -> List[Dict[str, Any]]:
        pool = self.search(" ".join(_field_terms(field)), top_k=max(top_k * 4, 20))
        pool.extend(_exact_field_candidates(self.chunks, field, limit=max(top_k * 3, 20)))
        return _rerank_field_results(pool, field, top_k=top_k)


class EmbeddingVectorRetriever:
    def __init__(
        self,
        chunks: List[Dict[str, Any]],
        *,
        api_key: str,
        base_url: str,
        model: str,
        batch_size: int = 16,
    ):
        if not api_key:
            raise RuntimeError("缺少 DASHSCOPE_API_KEY，无法启用 embedding 向量召回。")
        self.chunks = chunks
        self.model = model
        self.batch_size = max(1, batch_size)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.doc_vectors = self._embed_texts([item.get("text", "") for item in chunks])

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = [text or " " for text in texts[start:start + self.batch_size]]
            response = self.client.embeddings.create(model=self.model, input=batch)
            by_index = sorted(response.data, key=lambda item: item.index)
            vectors.extend([list(item.embedding) for item in by_index])
        return vectors

    @staticmethod
    def _cosine(left: List[float], right: List[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    def search(self, query: str, *, top_k: int = 5) -> List[Dict[str, Any]]:
        if not query.strip():
            return []
        query_vector = self._embed_texts([query])[0]
        scored: List[Dict[str, Any]] = []
        for chunk, vector in zip(self.chunks, self.doc_vectors):
            score = self._cosine(query_vector, vector)
            score += SOURCE_BONUS.get(str(chunk.get("source") or ""), 0.0)
            if score > 0:
                item = dict(chunk)
                item["score"] = round(score, 6)
                scored.append(item)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def search_field(self, field: Dict[str, Any], *, top_k: int = 5) -> List[Dict[str, Any]]:
        pool = self.search(" ".join(_field_terms(field)), top_k=max(top_k * 4, 20))
        pool.extend(_exact_field_candidates(self.chunks, field, limit=max(top_k * 3, 20)))
        return _rerank_field_results(pool, field, top_k=top_k)


class HybridRetriever:
    def __init__(
        self,
        chunks: List[Dict[str, Any]],
        *,
        bm25_top_k: int = 30,
        vector_top_k: int = 30,
        rrf_k: int = 60,
        vector_backend: str = "local",
        embedding_api_key: str = "",
        embedding_base_url: str = "",
        embedding_model: str = "text-embedding-v4",
        embedding_batch_size: int = 16,
    ):
        self.bm25 = SimpleRetriever(chunks)
        self.chunks = chunks
        self.vector_backend = vector_backend
        self.vector_error = ""
        if vector_backend == "embedding":
            try:
                self.vector = EmbeddingVectorRetriever(
                    chunks,
                    api_key=embedding_api_key,
                    base_url=embedding_base_url,
                    model=embedding_model,
                    batch_size=embedding_batch_size,
                )
            except Exception as exc:
                self.vector_backend = "local_fallback"
                self.vector_error = str(exc)
                self.vector = LocalVectorRetriever(chunks)
        else:
            self.vector = LocalVectorRetriever(chunks)
        self.bm25_top_k = bm25_top_k
        self.vector_top_k = vector_top_k
        self.rrf_k = rrf_k

    def _fuse(self, bm25_results: List[Dict[str, Any]], vector_results: List[Dict[str, Any]], *, top_k: int) -> List[Dict[str, Any]]:
        fused: Dict[str, Dict[str, Any]] = {}

        def add_results(results: List[Dict[str, Any]], source: str) -> None:
            for rank, item in enumerate(results, start=1):
                chunk_id = str(item.get("chunk_id") or f"{source}_{rank}")
                if chunk_id not in fused:
                    fused[chunk_id] = dict(item)
                    fused[chunk_id]["score"] = 0.0
                current = fused[chunk_id]
                current.setdefault("retrieval_sources", [])
                current["retrieval_sources"].append(source)
                current[f"{source}_rank"] = rank
                current[f"{source}_score"] = item.get("score", 0)
                current["score"] = current.get("score", 0.0) + 1.0 / (self.rrf_k + rank)

        add_results(bm25_results, "bm25")
        add_results(vector_results, "vector")
        ranked = sorted(fused.values(), key=lambda item: item["score"], reverse=True)
        for index, item in enumerate(ranked, start=1):
            item["score"] = round(item["score"], 6)
            item["hybrid_rank"] = index
            item["retrieval_source"] = "+".join(sorted(set(item.get("retrieval_sources", []))))
            item["vector_backend"] = self.vector_backend
            if self.vector_error:
                item["vector_error"] = self.vector_error[:200]
        return ranked[:top_k]

    def search(self, query: str, *, top_k: int = 5) -> List[Dict[str, Any]]:
        bm25_results = self.bm25.search(query, top_k=max(top_k, self.bm25_top_k))
        vector_results = self.vector.search(query, top_k=max(top_k, self.vector_top_k))
        return self._fuse(bm25_results, vector_results, top_k=top_k)

    def search_field(self, field: Dict[str, Any], *, top_k: int = 5) -> List[Dict[str, Any]]:
        pool = self.search(" ".join(_field_terms(field)), top_k=max(top_k * 8, self.bm25_top_k, self.vector_top_k))
        pool.extend(_exact_field_candidates(self.chunks, field, limit=max(top_k * 4, 30)))
        return _rerank_field_results(pool, field, top_k=top_k)
