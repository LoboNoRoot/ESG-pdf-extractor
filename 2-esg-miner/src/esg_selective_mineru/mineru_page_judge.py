from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, List

import fitz
from openai import OpenAI

from .config import Settings


def review_mineru_pages_with_llm(
    page_scans: List[Dict[str, Any]],
    settings: Settings,
    *,
    pdf_path: Path | None = None,
) -> Dict[str, Any]:
    if not page_scans:
        return {"enabled": True, "attempted": False, "selected_pages": [], "decisions": [], "error": ""}
    if not settings.dashscope_api_key:
        return {
            "enabled": True,
            "attempted": False,
            "selected_pages": [],
            "decisions": [],
            "error": "missing_dashscope_api_key",
        }

    client = OpenAI(api_key=settings.dashscope_api_key, base_url=settings.openai_base_url)
    use_visual_review = bool(pdf_path) and any(_needs_visual_review(row) for row in page_scans)
    try:
        if use_visual_review:
            data = _review_pages_with_vlm(client, Path(pdf_path), page_scans, settings)
            model = settings.vlm_model
        else:
            data = _review_pages_with_text_llm(client, page_scans, settings)
            model = settings.schema_judge_model or settings.text_model
    except Exception as exc:
        return {
            "enabled": True,
            "attempted": True,
            "selected_pages": [],
            "decisions": [],
            "error": str(exc),
        }

    decisions = data.get("decisions", [])
    if not isinstance(decisions, list):
        decisions = []
    selected_pages = []
    normalized = []
    candidate_pages = {int(row["page_number"]) for row in page_scans}
    for item in decisions:
        if not isinstance(item, dict):
            continue
        try:
            page_number = int(item.get("page_number"))
        except (TypeError, ValueError):
            continue
        if page_number not in candidate_pages:
            continue
        needs_mineru = bool(item.get("needs_mineru"))
        if needs_mineru:
            selected_pages.append(page_number)
        normalized.append({
            "page_number": page_number,
            "needs_mineru": needs_mineru,
            "reason": str(item.get("reason") or "")[:300],
        })
    return {
        "enabled": True,
        "attempted": True,
        "model": model,
        "review_mode": "vlm" if use_visual_review else "text",
        "selected_pages": sorted(set(selected_pages)),
        "decisions": normalized,
        "error": "",
    }


def _review_pages_with_text_llm(client: OpenAI, page_scans: List[Dict[str, Any]], settings: Settings) -> Dict[str, Any]:
    completion = client.chat.completions.create(
        model=settings.schema_judge_model or settings.text_model,
        messages=[
            {
                "role": "system",
                "content": "你是 ESG 报告解析路由器，只判断页面是否值得调用 MinerU 深度解析。请严格输出 JSON。",
            },
            {"role": "user", "content": _build_prompt(page_scans)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    return json.loads(content)


def _review_pages_with_vlm(client: OpenAI, pdf_path: Path, page_scans: List[Dict[str, Any]], settings: Settings) -> Dict[str, Any]:
    decisions: List[Dict[str, Any]] = []
    for row in page_scans:
        page_number = int(row["page_number"])
        image_url = _page_thumbnail_data_url(pdf_path, page_number)
        completion = client.chat.completions.create(
            model=settings.vlm_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是 ESG 报告页面筛选器。根据页面截图判断该页是否值得交给 MinerU 解析。只输出 JSON。",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "判断这页是否包含 ESG 数据表、关键绩效表、指标表、环境/员工/治理量化数据、"
                                "多年份表格或需要 OCR/版式解析的重要信息。"
                                "封面、目录、章节标题、纯宣传图、普通正文页通常不要选择。"
                                "只输出 JSON：{\"needs_mineru\":true,\"reason\":\"...\"}"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {"needs_mineru": False, "reason": "invalid_vlm_json"}
        decisions.append({
            "page_number": page_number,
            "needs_mineru": bool(data.get("needs_mineru")),
            "reason": str(data.get("reason") or "")[:300],
        })
    return {"decisions": decisions}


def _needs_visual_review(row: Dict[str, Any]) -> bool:
    return row.get("scan_quality") == "scanned_or_low_text" and int(row.get("text_length") or 0) < 80


def _page_thumbnail_data_url(pdf_path: Path, page_number: int) -> str:
    with fitz.open(pdf_path) as doc:
        page = doc[page_number - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False)
        data = pix.tobytes("jpeg", jpg_quality=65)
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _build_prompt(page_scans: List[Dict[str, Any]]) -> str:
    compact_pages = []
    for row in page_scans:
        compact_pages.append({
            "page_number": row.get("page_number"),
            "text_length": row.get("text_length"),
            "number_count": row.get("number_count"),
            "year_hits": row.get("year_hits", []),
            "esg_hits": row.get("esg_hits", []),
            "table_hits": row.get("table_hits", []),
            "index_hits": row.get("index_hits", []),
            "table_like_lines": row.get("table_like_lines"),
            "scan_quality": row.get("scan_quality"),
            "mineru_score": row.get("mineru_score"),
            "reasons": row.get("reasons", []),
        })
    return (
        "请判断这些 ESG 报告页面是否值得调用 MinerU 深度解析。\n"
        "应该选择的页面通常包含：ESG 数据表、关键绩效表、指标表、环境/员工/治理量化数据、"
        "图文混排导致 PyMuPDF 可能漏读的关键信息、扫描或低文本层页面。\n"
        "不应选择的页面通常是：封面、目录、章节标题页、致辞、纯宣传案例、附录问卷、低价值索引页。\n"
        "请只输出 JSON，格式为：\n"
        "{\"decisions\":[{\"page_number\":1,\"needs_mineru\":true,\"reason\":\"...\"}]}\n\n"
        f"页面特征：\n{json.dumps(compact_pages, ensure_ascii=False)}"
    )
