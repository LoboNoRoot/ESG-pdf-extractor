from esg_selective_mineru.extractor import _align_result_to_target_year
from esg_selective_mineru.quality import validate_and_score_result


FIELD = {
    "field_key": "employee_training_hours",
    "name_cn": "员工培训小时",
    "indicator_type": "quantitative",
    "aliases": ["培训总时长", "年度培训总时长"],
}


def _result(value: str = "36500"):
    return {
        "field_key": "employee_training_hours",
        "matched": True,
        "value": value,
        "unit": "小时",
        "year": "2022",
        "evidence": "年度培训总时长\n小时\n35,000\n36,500\n38,700",
        "source_chunk_id": "c1",
        "reason": "",
    }


def test_align_result_to_target_year_from_horizontal_table():
    contexts = {
        "employee_training_hours": [
            {
                "chunk_id": "c1",
                "text": "指标 单位 2020 2021 2022\n年度培训总时长 小时 35,000 36,500 38,700",
            }
        ]
    }

    aligned = _align_result_to_target_year(_result(), FIELD, contexts, "2022")

    assert aligned["value"] == "38700"
    assert aligned["year"] == "2022"
    assert "2022" in aligned["evidence"]
    assert "year_aligned_from_table" in aligned["reason"]


def test_align_result_to_target_year_from_wrapped_table_header():
    contexts = {
        "employee_training_hours": [
            {
                "chunk_id": "c1",
                "text": "2020 年\n2021 年\n2022 年\n年度培训总时长\n小时\n35,000\n36,500\n38,700",
            }
        ]
    }

    aligned = _align_result_to_target_year(_result(), FIELD, contexts, "2022")

    assert aligned["value"] == "38700"
    assert aligned["year"] == "2022"
    assert "2022" in aligned["evidence"]
    assert "year_aligned_from_table" in aligned["reason"]


def test_align_result_corrects_non_monotonic_pdf_year_order():
    contexts = {
        "employee_training_hours": [
            {
                "chunk_id": "c1",
                "text": "指标名称\n单位\n2021 年\n2022 年\n2020 年\n年度培训总时长\n小时\n35,000\n36,500\n38,700",
            }
        ]
    }

    aligned = _align_result_to_target_year(_result(), FIELD, contexts, "2022")

    assert aligned["value"] == "38700"
    assert aligned["year"] == "2022"
    assert "2021" in aligned["evidence"]
    assert "2022" in aligned["evidence"]
    assert "year_aligned_from_table" in aligned["reason"]


def test_align_result_ignores_numbers_before_current_field_and_dedupes_years():
    contexts = {
        "employee_training_hours": [
            {
                "chunk_id": "c1",
                "text": (
                    "2020 2020 2021 2021 2022 2022 "
                    "兼职员工人数 人 0 0 0 "
                    "年度培训总时长 小时 35,000 36,500 38,700 "
                    "中国大陆员工人数 人 7,981 8,049 8,276"
                ),
            }
        ]
    }

    aligned = _align_result_to_target_year(_result(), FIELD, contexts, "2022")

    assert aligned["value"] == "38700"
    assert aligned["year"] == "2022"
    assert "year_aligned_from_table" in aligned["reason"]


def test_align_result_uses_field_alias_not_wrong_evidence_line():
    field = {
        "field_key": "work_injury_incidents",
        "name_cn": "工伤事故",
        "indicator_type": "quantitative",
        "aliases": ["工伤", "工伤事故数", "因工受伤", "总工伤人数"],
    }
    row = {
        "field_key": "work_injury_incidents",
        "matched": True,
        "value": "10317",
        "unit": "人",
        "year": "2023",
        "evidence": "参与安全教育培训人次 人次 9,862 9,325 10,317",
        "source_chunk_id": "c1",
        "reason": "",
    }
    contexts = {
        "work_injury_incidents": [
            {
                "chunk_id": "c1",
                "text": (
                    "议题 指标 单位 2021年 2022年 2023年\n"
                    "员工培训 参与安全教育培训人次 人次 9,862 9,325 10,317\n"
                    "职业健康与安全生产 总工伤人数 人 9 5 8\n"
                ),
            }
        ]
    }

    aligned = _align_result_to_target_year(row, field, contexts, "2023")

    assert aligned["value"] == "8"
    assert "总工伤人数" in aligned["evidence"]


def test_align_result_prefers_total_water_usage_field_line():
    field = {
        "field_key": "water_consumption_total",
        "name_cn": "用水量",
        "indicator_type": "quantitative",
        "aliases": ["总用水量", "用水总量", "取水量", "耗水量", "新鲜水用量"],
    }
    row = {
        "field_key": "water_consumption_total",
        "matched": True,
        "value": "1139032",
        "unit": "吨",
        "year": "2023",
        "evidence": "地表水取水量 吨 1,269,306 1,126,641 1,139,032",
        "source_chunk_id": "c1",
        "reason": "",
    }
    contexts = {
        "water_consumption_total": [
            {
                "chunk_id": "c1",
                "text": (
                    "2021 2022 2023\n"
                    "地表水取水量 吨 1,269,306 1,126,641 1,139,032\n"
                    "地下水取水量 吨 561,742 583,273 576,879\n"
                    "总用水量 吨 73,546,206 70,439,637 69,113,761\n"
                ),
            }
        ]
    }

    aligned = _align_result_to_target_year(row, field, contexts, "2023")

    assert aligned["value"] == "69113761"
    assert "总用水量" in aligned["evidence"]


def test_quantitative_result_rejects_ambiguous_evidence_without_target_year():
    row = {
        "field_key": "employee_training_hours",
        "name_cn": "员工培训小时",
        "category": "S",
        "indicator_type": "quantitative",
        "matched": True,
        "value": "36500",
        "unit": "小时",
        "year": "2022",
        "evidence": "年度培训总时长 小时 35,000 36,500 38,700",
        "source_page": 34,
        "confidence": 0.95,
    }

    checked = validate_and_score_result(row, target_year="2022", field=FIELD)

    assert "target_year_not_in_evidence" in checked["quality_warnings"]
    assert "ambiguous_multi_number_evidence_without_target_year" in checked["quality_warnings"]
    assert "weak_evidence" in checked["quality_warnings"]
    assert "rejected_unreliable_quantitative_evidence" in checked["quality_warnings"]
    assert checked["matched"] is False
    assert checked["confidence"] == 0.35


def test_align_result_can_rescue_unmatched_quantitative_table_row():
    field = {
        "field_key": "water_consumption_total",
        "name_cn": "总用水量",
        "indicator_type": "quantitative",
        "unit_examples": ["吨", "立方米"],
        "aliases": ["总用水量", "用水总量", "新鲜水取水总量", "取水总量"],
    }
    row = {
        "field_key": "water_consumption_total",
        "matched": False,
        "value": "",
        "unit": "",
        "year": "",
        "evidence": "",
        "source_chunk_id": "c1",
        "reason": "LLM did not see a complete number.",
    }
    contexts = {
        "water_consumption_total": [
            {
                "chunk_id": "c1",
                "text": (
                    "议题 指标 单位 2021年 2022年 2023年\n"
                    "水资源管理 总用水量 吨 73,546,206 70,439,637 69,113,761\n"
                    "循环用水量 吨 71,374,306 68,384,937 66,972,236\n"
                ),
            }
        ]
    }

    aligned = _align_result_to_target_year(row, field, contexts, "2023")

    assert aligned["matched"] is True
    assert aligned["value"] == "69113761"
    assert aligned["unit"] == "吨"
    assert "deterministic_year_table_match" in aligned["reason"]


def test_quantitative_single_value_evidence_gets_calibrated_confidence():
    field = {
        "field_key": "employee_total",
        "name_cn": "员工总数",
        "indicator_type": "quantitative",
        "aliases": ["员工总人数", "员工人数", "雇员总数", "在职员工"],
    }
    row = {
        "field_key": "employee_total",
        "name_cn": "员工总数",
        "category": "S",
        "indicator_type": "quantitative",
        "matched": True,
        "value": "8401",
        "unit": "人",
        "year": "2023",
        "evidence": "员工总人数：8,401 人",
        "source_page": "",
        "confidence": 0.35,
    }

    checked = validate_and_score_result(row, target_year="2023", field=field)

    assert checked["matched"] is True
    assert checked["confidence"] == 0.8
    assert "target_year_not_in_evidence" not in checked["quality_warnings"]
    assert "field_term_not_in_evidence" not in checked["quality_warnings"]
