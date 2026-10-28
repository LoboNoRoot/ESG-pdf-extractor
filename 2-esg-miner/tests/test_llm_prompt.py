from esg_selective_mineru.llm_client import _build_prompt


def test_prompt_uses_configured_context_chars():
    fields = [
        {
            "field_key": "employee_training_hours",
            "name_cn": "员工培训小时",
            "category": "S",
            "indicator_type": "quantitative",
            "value_type": "number",
            "expected_units": ["小时"],
            "aliases": ["培训总时长"],
        }
    ]
    long_text = "培训总时长 " + ("A" * 1300) + " 2023 39600 小时"
    contexts = {
        "employee_training_hours": [
            {"chunk_id": "c1", "source": "mineru", "page": 1, "score": 1, "text": long_text}
        ]
    }

    prompt = _build_prompt(fields, contexts, target_year="2023", context_chars=1800)

    assert "39600 小时" in prompt
