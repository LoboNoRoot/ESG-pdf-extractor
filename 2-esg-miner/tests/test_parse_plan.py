import unittest

from esg_selective_mineru.page_scan import score_page
from esg_selective_mineru.parse_plan import build_parse_plan


class SelectivePlanTests(unittest.TestCase):
    def test_score_page_detects_table_like_esg_page(self):
        scan = score_page(1, "环境绩效 指标 单位 2024 用水量 吨 100 温室气体排放总量 吨 200")
        self.assertGreaterEqual(scan.mineru_score, 35)
        self.assertIn("table_terms", scan.reasons)

    def test_build_parse_plan_selects_high_score_pages(self):
        scans = [
            {"page_number": 1, "mineru_score": 10, "number_count": 0, "scan_quality": "text_layer_ok"},
            {"page_number": 2, "mineru_score": 60, "number_count": 20, "scan_quality": "text_layer_ok"},
        ]
        plan = build_parse_plan(scans, mineru_score_threshold=35, max_mineru_pages=5)
        self.assertEqual(plan["mineru_pages"], [2])

    def test_build_parse_plan_spreads_low_text_pages_across_report(self):
        scans = [
            {
                "page_number": page,
                "mineru_score": 30,
                "number_count": 0,
                "table_like_lines": 0,
                "table_hits": [],
                "esg_hits": [],
                "year_hits": [],
                "scan_quality": "scanned_or_low_text",
                "reasons": ["low_text_layer"],
            }
            for page in range(1, 90)
        ]

        plan = build_parse_plan(
            scans,
            mineru_score_threshold=30,
            max_mineru_pages=20,
            llm_selected_pages=list(range(1, 90)),
            llm_review_low_threshold=25,
            llm_review_high_threshold=45,
        )

        self.assertEqual(len(plan["mineru_pages"]), 20)
        self.assertNotEqual(plan["mineru_pages"], list(range(1, 21)))
        self.assertGreaterEqual(max(plan["mineru_pages"]), 80)


if __name__ == "__main__":
    unittest.main()
