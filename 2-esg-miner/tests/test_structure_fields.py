from configs.schema.a_share_v5 import A_SHARE_SCHEMA
from esg_selective_mineru.quality import validate_and_score_result


def test_employee_structure_field_clears_scalar_value():
    field = A_SHARE_SCHEMA["employee_age_structure"]
    row = {
        "field_key": "employee_age_structure",
        "name_cn": "员工年龄结构",
        "category": "S",
        "indicator_type": field["indicator_type"],
        "matched": True,
        "value": "8401",
        "unit": "人",
        "year": "2023",
        "summary": "",
        "evidence": "员工总人数：8,401 人 按年龄划分(人） 30岁以下：1,309 30-40岁：2,783 40-50岁：2,215 50岁及以上：2,094",
        "confidence": 0.9,
    }

    checked = validate_and_score_result(row, target_year="2023", field=field)

    assert checked["matched"] is True
    assert checked["value"] == ""
    assert checked["unit"] == ""
    assert "30岁以下" in checked["summary"]
    assert checked["confidence"] == 0.65
    assert "structure_field_scalar_value_cleared" in checked["quality_warnings"]


def test_pollutant_emissions_clears_single_pollutant_value():
    field = A_SHARE_SCHEMA["pollutant_emissions"]
    row = {
        "field_key": "pollutant_emissions",
        "name_cn": "污染物排放",
        "category": "E",
        "indicator_type": field["indicator_type"],
        "matched": True,
        "value": "28.7",
        "unit": "吨",
        "year": "2023",
        "summary": "",
        "evidence": "化学需氧量(COD) 吨 28.70 氨氮(NH3-N) 吨 2.31 废气排放量 万立方米 492,105.62 氮氧化物 吨 286.45",
        "confidence": 0.9,
    }

    checked = validate_and_score_result(row, target_year="2023", field=field)

    assert checked["matched"] is True
    assert checked["value"] == ""
    assert checked["unit"] == ""
    assert "氨氮" in checked["summary"]
    assert "structure_field_scalar_value_cleared" in checked["quality_warnings"]


def test_board_structure_clears_single_director_count():
    field = A_SHARE_SCHEMA["board_structure"]
    row = {
        "field_key": "board_structure",
        "name_cn": "董事会结构",
        "category": "G",
        "indicator_type": field["indicator_type"],
        "matched": True,
        "value": "5",
        "unit": "人",
        "year": "2023",
        "summary": "",
        "evidence": "截至2023年12月31日，公司董事会有5名董事，其中4名为独立董事。",
        "confidence": 0.9,
    }

    checked = validate_and_score_result(row, target_year="2023", field=field)

    assert checked["matched"] is True
    assert checked["value"] == ""
    assert checked["unit"] == ""
    assert "独立董事" in checked["summary"]
    assert "structure_field_scalar_value_cleared" in checked["quality_warnings"]
