import unittest

import pandas as pd
import plotly.express as px

from quality_chart_ui import build_quality_pareto, quality_pareto_rows_html, style_quality_trend


class SharedQualityChartTest(unittest.TestCase):
    def test_risk_score_pareto_preserves_decimal_scores_and_full_share(self):
        ranked = pd.DataFrame({"cc": ["111111", "222222"], "score": [38.7, 37.0], "cum": [.18, .36]})
        fig = build_quality_pareto(ranked, name_col="cc", qty_col="score", cumulative_col="cum", value_format=".1f")
        self.assertEqual(list(fig.data[0].y), [38.7, 37.0])
        self.assertEqual(list(fig.data[0].x), ["1", "2"])
        self.assertEqual(list(fig.data[1].y), [.18, .36])
        self.assertEqual(fig.data[0].texttemplate, "%{text:.1f}")
        self.assertIn("38.7", quality_pareto_rows_html(ranked, name_col="cc", qty_col="score", value_format=".1f"))

    def test_top_subset_keeps_supplied_full_population_share(self):
        ranked = pd.DataFrame({"name": ["Seam", "Stain"], "qty": [40, 20], "cum": [.4, .6]})
        fig = build_quality_pareto(ranked, name_col="name", qty_col="qty", cumulative_col="cum")
        self.assertEqual(list(fig.data[0].y), [40, 20])
        self.assertEqual(list(fig.data[1].y), [.4, .6])
        self.assertEqual(list(fig.data[0].customdata[:, 0]), ["Seam", "Stain"])
        self.assertEqual(fig.data[1].yaxis, "y2")
        # Truncated TU data must not appear to account for 100% of all defects.
        self.assertLess(fig.data[1].y[-1], 1)

    def test_bme_display_population_share_is_preserved(self):
        ranked = pd.DataFrame({"name": ["Brake", "Fork"], "qty": [3, 1], "cum": [.75, 1]})
        fig = build_quality_pareto(ranked, name_col="name", qty_col="qty", cumulative_col="cum")
        self.assertEqual(list(fig.data[1].y), [.75, 1])

    def test_style_does_not_change_rates_or_click_evidence(self):
        data = pd.DataFrame({"week": ["2026-W01", "2026-W02"], "rate": [.1, None], "cc": ["A", "A"], "inspected": [100, 0]})
        fig = px.line(data, x="week", y="rate", color="cc", custom_data=["cc", "inspected"], markers=True)
        before = fig.data[0].customdata.copy()
        style_quality_trend(fig, height=330)
        self.assertEqual(fig.data[0].y[0], .1)
        self.assertTrue(pd.isna(fig.data[0].y[1]))
        self.assertEqual(fig.data[0].customdata.tolist(), before.tolist())
        self.assertEqual(list(fig.data[0].x), ["2026-W01", "2026-W02"])

    def test_full_defect_labels_are_escaped_and_remain_accessible(self):
        ranked = pd.DataFrame({"name": ['1. <script>bad</script> "quote"'], "qty": [8]})
        markup = quality_pareto_rows_html(ranked, name_col="name", qty_col="qty")
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;", markup)
        self.assertIn("&quot;quote&quot;", markup)
        self.assertIn("#1", markup)


if __name__ == "__main__":
    unittest.main()
