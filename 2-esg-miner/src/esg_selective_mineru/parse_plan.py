from __future__ import annotations

from typing import Any, Dict, List


def _low_text_only(row: Dict[str, Any]) -> bool:
    reasons = set(row.get("reasons") or [])
    return (
        reasons == {"low_text_layer"}
        and int(row.get("number_count") or 0) == 0
        and int(row.get("table_like_lines") or 0) == 0
        and not row.get("table_hits")
        and not row.get("esg_hits")
        and not row.get("year_hits")
    )


def _evenly_spaced_pages(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    if limit <= 0 or not rows:
        return []
    ordered = sorted(rows, key=lambda row: int(row["page_number"]))
    if len(ordered) <= limit:
        return ordered
    if limit == 1:
        return [ordered[len(ordered) // 2]]
    last_index = len(ordered) - 1
    selected_indexes = {
        round(index * last_index / (limit - 1))
        for index in range(limit)
    }
    return [ordered[index] for index in sorted(selected_indexes)]


def build_parse_plan(
    page_scans: List[Dict[str, Any]],
    *,
    mineru_score_threshold: int,
    max_mineru_pages: int,
    llm_selected_pages: List[int] | None = None,
    llm_review_low_threshold: int | None = None,
    llm_review_high_threshold: int | None = None,
    llm_review: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    high_threshold = llm_review_high_threshold or mineru_score_threshold
    llm_pages = set(llm_selected_pages or [])
    ranked = sorted(page_scans, key=lambda row: (row["mineru_score"], row["number_count"]), reverse=True)
    selected_pages = set()
    decision_sources: Dict[int, str] = {}

    signal_candidates = []
    low_text_candidates = []
    for row in ranked:
        score = int(row.get("mineru_score") or 0)
        page_number = row["page_number"]
        if score >= high_threshold:
            decision_sources[page_number] = "rule_high_score"
        elif page_number in llm_pages:
            decision_sources[page_number] = "llm_gray_zone"
        else:
            continue
        if _low_text_only(row):
            low_text_candidates.append(row)
        else:
            signal_candidates.append(row)

    for row in signal_candidates[:max_mineru_pages]:
        selected_pages.add(row["page_number"])

    remaining = max_mineru_pages - len(selected_pages)
    for row in _evenly_spaced_pages(low_text_candidates, remaining):
        selected_pages.add(row["page_number"])

    pages = []
    visual_fallback = []
    for row in page_scans:
        page_number = row["page_number"]
        if page_number in selected_pages:
            strategy = "mineru_required"
        else:
            strategy = "pymupdf_only"
        if row.get("scan_quality") == "scanned_or_low_text" and page_number not in selected_pages:
            visual_fallback.append(page_number)
        score = int(row.get("mineru_score") or 0)
        if page_number in decision_sources:
            decision_source = decision_sources[page_number]
        elif llm_review_low_threshold is not None and score < llm_review_low_threshold:
            decision_source = "rule_low_score"
        elif llm_review_low_threshold is not None and score < high_threshold:
            decision_source = "llm_gray_zone_rejected"
        else:
            decision_source = "rule_below_threshold"
        pages.append({**row, "parse_strategy": strategy, "mineru_decision_source": decision_source})

    return {
        "page_count": len(page_scans),
        "mineru_pages": sorted(selected_pages),
        "visual_fallback_pages": visual_fallback,
        "llm_review": llm_review or {"enabled": False},
        "pages": pages,
    }
