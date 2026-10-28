from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator


YEAR_RE = re.compile(r"20[0-3][0-9]")
NUMBER_RE = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?")

UNIT_ALIASES = {
    "吨": "吨",
    "t": "吨",
    "ton": "吨",
    "tons": "吨",
    "千克": "千克",
    "kg": "千克",
    "立方米": "立方米",
    "m3": "立方米",
    "m³": "立方米",
    "万立方米": "万立方米",
    "吨标准煤": "吨标准煤",
    "万元": "万元",
    "亿元": "亿元",
    "元": "元",
    "tco2e": "tCO2e",
    "吨co2e": "tCO2e",
    "吨二氧化碳当量": "tCO2e",
    "万吨co2e": "万吨CO2e",
    "万吨二氧化碳当量": "万吨CO2e",
    "千瓦时": "kWh",
    "kwh": "kWh",
    "兆瓦时": "MWh",
    "mwh": "MWh",
    "%": "%",
    "％": "%",
    "人": "人",
    "人次": "人次",
    "小时": "小时",
    "人均小时": "人均小时",
    "次": "次",
    "起": "起",
    "件": "件",
    "项": "项",
    "家": "家",
    "宗": "宗",
    "场次": "场次",
    "日": "日",
    "天": "天",
}

STRUCTURE_FIELD_KEYS = {
    "employee_gender_structure",
    "employee_age_structure",
    "employee_education_structure",
}


class ExtractionResult(BaseModel):
    field_key: str = ""
    name_cn: str = ""
    category: str = ""
    indicator_type: str = ""
    matched: bool = False
    value: str = ""
    unit: str = ""
    year: str = ""
    summary: str = ""
    evidence: str = ""
    source_chunk_id: str = ""
    source_page: str | int = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""

    @field_validator(
        "field_key",
        "name_cn",
        "category",
        "indicator_type",
        "value",
        "unit",
        "year",
        "summary",
        "evidence",
        "source_chunk_id",
        "source_page",
        "reason",
        mode="before",
    )
    @classmethod
    def stringify(cls, value: Any) -> str:
        return "" if value is None else str(value).strip()

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> float:
        try:
            numeric = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if numeric > 1:
            numeric = numeric / 100
        return max(0.0, min(1.0, numeric))


def normalize_unit(unit: Any) -> tuple[str, str]:
    raw = str(unit or "").strip()
    if not raw:
        return "", "missing_unit"
    key = raw.lower().replace(" ", "")
    normalized = UNIT_ALIASES.get(key)
    if normalized:
        return normalized, ""
    return raw, "unknown_unit"


def normalize_value(value: Any) -> str:
    text = str(value or "").strip()
    match = NUMBER_RE.search(text.replace(",", ""))
    return match.group(0) if match else ""


def _is_quantitative(row: Dict[str, Any]) -> bool:
    return str(row.get("indicator_type") or "").lower() in {"quantitative", "定量"}


def _is_structure_field(row: Dict[str, Any], field: Dict[str, Any] | None = None) -> bool:
    if str(row.get("field_key") or "") in STRUCTURE_FIELD_KEYS:
        return True
    if field and str(field.get("value_type") or "").lower() == "structure":
        return True
    return str(row.get("value_type") or "").lower() == "structure"


def _field_terms(row: Dict[str, Any], field: Dict[str, Any] | None = None) -> List[str]:
    terms = [row.get("name_cn"), row.get("field_key")]
    if field:
        terms.extend(field.get("aliases") or [])
        terms.extend(field.get("required_any") or [])
    cleaned: List[str] = []
    for term in terms:
        text = str(term or "").strip()
        if len(text) >= 2 and text not in cleaned:
            cleaned.append(text)
    return cleaned


def evidence_has_field_term(row: Dict[str, Any], field: Dict[str, Any] | None = None) -> bool:
    evidence = str(row.get("evidence") or "")
    return bool(evidence and any(term in evidence for term in _field_terms(row, field)))


def evidence_score(row: Dict[str, Any], *, target_year: str = "", field: Dict[str, Any] | None = None) -> int:
    evidence = str(row.get("evidence") or "")
    if not evidence.strip():
        return 0
    score = 20
    if evidence_has_field_term(row, field):
        score += 20
    normalized_value = normalize_value(row.get("value"))
    if normalized_value and normalized_value in evidence.replace(",", ""):
        score += 25
    unit = str(row.get("unit") or "")
    if unit and unit in evidence:
        score += 15
    year = str(row.get("year") or "")
    if target_year and target_year in evidence:
        score += 10
    elif year and year in evidence:
        score += 5
    if row.get("source_page"):
        score += 10
    return min(score, 100)


def evidence_number_count(row: Dict[str, Any]) -> int:
    evidence = str(row.get("evidence") or "").strip()
    return len([item for item in NUMBER_RE.findall(evidence.replace(",", "")) if not YEAR_RE.fullmatch(item)])


def has_ambiguous_numbers_without_target_year(row: Dict[str, Any], *, target_year: str) -> bool:
    if not target_year or not row.get("matched") or not _is_quantitative(row):
        return False
    evidence = str(row.get("evidence") or "").strip()
    if not evidence or target_year in evidence:
        return False
    return evidence_number_count(row) >= 2


def calibrate_confidence(clean: Dict[str, Any], score: int, warnings: List[str]) -> float:
    current = float(clean.get("confidence") or 0)
    if not clean.get("matched"):
        return current
    calibrated = max(current, score / 100)
    if "weak_evidence" in warnings:
        calibrated = min(calibrated, 0.49)
    if "ambiguous_multi_number_evidence_without_target_year" in warnings:
        calibrated = min(calibrated, 0.45)
    elif "target_year_not_in_evidence" in warnings:
        calibrated = min(calibrated, 0.75)
    if "field_term_not_in_evidence" in warnings:
        calibrated = min(calibrated, 0.65)
    if "unknown_unit" in warnings:
        calibrated = min(calibrated, 0.85)
    if "structure_field_scalar_value_cleared" in warnings:
        calibrated = min(calibrated, 0.65)
    return round(max(0.0, min(1.0, calibrated)), 4)


def validate_year(year: Any, *, target_year: str, matched: bool) -> tuple[str, str]:
    text = str(year or "").strip()
    if not matched:
        return text, ""
    if not text:
        return text, "missing_year"
    years = YEAR_RE.findall(text)
    if target_year and target_year not in years:
        return text, f"year_mismatch:{target_year}"
    return target_year if target_year else text, ""


def validate_and_score_result(
    row: Dict[str, Any],
    *,
    target_year: str = "2024",
    field: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    warnings: List[str] = []
    try:
        model = ExtractionResult(**row)
        clean = model.model_dump()
    except Exception as exc:
        clean = ExtractionResult().model_dump()
        clean.update({key: "" if value is None else value for key, value in row.items()})
        warnings.append(f"schema_error:{exc}")

    is_quantitative = _is_quantitative(clean)
    is_structure = _is_structure_field(clean, field)
    normalized_unit, unit_warning = normalize_unit(clean.get("unit"))
    normalized_value = normalize_value(clean.get("value"))

    if clean.get("matched") and is_structure:
        if str(clean.get("value") or "").strip() or str(clean.get("unit") or "").strip():
            warnings.append("structure_field_scalar_value_cleared")
            clean["value"] = ""
            clean["unit"] = ""
            normalized_value = ""
            normalized_unit = ""
            clean["confidence"] = min(float(clean.get("confidence") or 0), 0.65)
        if not str(clean.get("summary") or "").strip() and str(clean.get("evidence") or "").strip():
            clean["summary"] = str(clean.get("evidence") or "").strip()[:240]

    if unit_warning and clean.get("matched") and is_quantitative:
        warnings.append(unit_warning)

    checked_year, year_warning = validate_year(clean.get("year"), target_year=target_year, matched=bool(clean.get("matched")))
    clean["year"] = checked_year
    if year_warning:
        warnings.append(year_warning)

    if (
        clean.get("matched")
        and target_year
        and is_quantitative
        and str(clean.get("evidence") or "").strip()
        and target_year not in str(clean.get("evidence") or "")
        and evidence_number_count(clean) >= 2
    ):
        warnings.append("target_year_not_in_evidence")

    if clean.get("matched") and is_quantitative and str(clean.get("evidence") or "").strip():
        if not evidence_has_field_term(clean, field):
            warnings.append("field_term_not_in_evidence")

    score = evidence_score(clean, target_year=target_year, field=field)
    if has_ambiguous_numbers_without_target_year(clean, target_year=target_year):
        warnings.append("ambiguous_multi_number_evidence_without_target_year")
        clean["confidence"] = min(float(clean.get("confidence") or 0), 0.45)
        score = min(score, 45)
    if clean.get("matched") and not is_structure and score < 50:
        warnings.append("weak_evidence")

    clean["confidence"] = calibrate_confidence(clean, score, warnings)

    fatal_warnings = {"ambiguous_multi_number_evidence_without_target_year"}
    if score < 50:
        fatal_warnings.add("field_term_not_in_evidence")
    if clean.get("matched") and is_quantitative and fatal_warnings.intersection(warnings):
        clean["matched"] = False
        clean["confidence"] = min(float(clean.get("confidence") or 0), 0.35)
        warnings.append("rejected_unreliable_quantitative_evidence")

    return {
        **clean,
        "target_year": target_year,
        "normalized_value": normalized_value,
        "normalized_unit": normalized_unit,
        "unit_warning": unit_warning,
        "year_warning": year_warning,
        "evidence_score": score,
        "quality_warnings": warnings,
    }


def enrich_results(
    rows: List[Dict[str, Any]],
    *,
    pdf_path: str | Path = "",
    target_year: str = "2024",
    expected_year: str = "",
    fields: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    # expected_year is kept for backward compatibility; target_year is the active policy.
    active_year = target_year or expected_year or "2024"
    fields_by_key = {str(field.get("field_key") or ""): field for field in fields or []}
    return [
        validate_and_score_result(
            row,
            target_year=active_year,
            field=fields_by_key.get(str(row.get("field_key") or "")),
        )
        for row in rows
    ]


def quality_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    review_counts: Dict[str, int] = {}
    target_year = ""
    for row in rows:
        review = row.get("review") or {}
        status = str(review.get("status") or "pending")
        review_counts[status] = review_counts.get(status, 0) + 1
        target_year = target_year or str(row.get("target_year") or "")
    return {
        "target_year": target_year,
        "fields": total,
        "matched": sum(1 for row in rows if row.get("matched")),
        "pending_review": review_counts.get("pending", 0) + review_counts.get("edited", 0),
        "review_status_counts": review_counts,
        "low_confidence": sum(1 for row in rows if float(row.get("confidence") or 0) < 0.7),
        "missing_evidence": sum(1 for row in rows if not str(row.get("evidence") or "").strip()),
        "weak_evidence": sum(1 for row in rows if int(row.get("evidence_score") or 0) < 50),
        "year_warnings": sum(1 for row in rows if row.get("year_warning")),
        "unit_warnings": sum(1 for row in rows if row.get("unit_warning") and row.get("unit_warning") != "missing_unit"),
        "schema_warnings": sum(1 for row in rows if any(str(item).startswith("schema_error") for item in row.get("quality_warnings") or [])),
        "average_evidence_score": round(sum(int(row.get("evidence_score") or 0) for row in rows) / total, 2) if total else 0,
    }
