import unittest

import pandas as pd

from quality_insights import (
    chart_evidence, build_chart_insight, gate_totals,
    supplier_summary, validate_ai_response,
)


class QualityInsightTests(unittest.TestCase):
    def test_exception_trend_detects_rebound_instead_of_first_last_only(self):
        trace = {"type": "scatter", "mode": "lines+markers", "x": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"], "y": [19, 6, 11, 14, 14, 16]}
        e = chart_evidence([trace], context={"exception_only": True})
        insight = build_chart_insight({"evidence": e})
        self.assertEqual(e["change"], 2)
        self.assertEqual(e["peak"], ("2026-01", 19.0))
        self.assertIn("反弹", insight["interpretation"])
        self.assertIn("总体不良率", insight["interpretation"])
        self.assertIn("2026-06", insight["action"])

    def test_rate_changes_are_percentage_points_and_use_denominator(self):
        trace = {"type": "scatter", "mode": "lines", "x": ["2026-05", "2026-06"], "y": [.03, .02]}
        e = chart_evidence([trace], ".2%", {"kind": "trend", "monthly": [{"numerator": 3, "denominator": 100}, {"numerator": 4, "denominator": 200}]})
        insight = build_chart_insight({"evidence": e})
        self.assertIn("-1.00 个百分点", insight["finding"])
        self.assertIn("4/200", insight["interpretation"])
        self.assertIn("记录量未下降", insight["interpretation"])

    def test_latest_zero_is_observed_zero(self):
        trace = {"type": "scatter", "mode": "lines", "x": ["May", "Jun"], "y": [3, 0]}
        e = chart_evidence([trace])
        self.assertEqual(e["latest"][1], 0)
        self.assertIn("为 0", build_chart_insight({"evidence": e})["finding"])

    def test_partial_month_cannot_be_interpreted_as_full_month(self):
        trace = {"type": "scatter", "mode": "lines", "x": ["2026-06-01", "2026-07-01"], "y": [.01, .02]}
        e = chart_evidence([trace], ".2%", {"cutoff": "2026-07-01"})
        self.assertTrue(e["partial_latest"])
        insight = build_chart_insight({"evidence": e})
        self.assertIn("末月未完整", insight["interpretation"])
        self.assertIn("相同天数", insight["action"])

    def test_iqc_action_does_not_pretend_cc_traceability_exists(self):
        traces = [{"type": "bar", "x": ["1"], "y": [8]}]
        e = chart_evidence(traces, context={"kind": "pareto", "total": 80, "names": ["印刷不良"], "traceability_missing": True})
        self.assertIn("当前没有 CC/Model 链路", build_chart_insight({"evidence": e})["action"])

    def test_pareto_uses_full_population_before_top_subset(self):
        traces = [{"type": "bar", "x": ["1", "2"], "y": [30, 20]}, {"type": "scatter", "mode": "lines+markers", "x": ["1", "2"], "y": [.3, .5]}]
        e = chart_evidence(traces, context={"kind": "pareto", "total": 100, "names": ["A", "B"], "measure": "risk_score"})
        self.assertEqual(e["shown_share"], .5)
        self.assertEqual(e["top_share"], .3)
        insight = build_chart_insight({"evidence": e})
        self.assertIn("不是产品不良概率", insight["interpretation"])
        self.assertIn("30.0", insight["finding"])

    def test_pareto_statistics_are_not_truncated_to_first_twelve_bars(self):
        traces = [{"type": "bar", "x": list(range(20)), "y": [1] * 20}, {"type": "scatter", "mode": "lines", "x": list(range(20)), "y": [(i + 1) / 20 for i in range(20)]}]
        e = chart_evidence(traces)
        self.assertEqual(e["shown_total"], 20)
        self.assertEqual(e["shown_share"], 1)

    def test_incomplete_denominator_cannot_become_a_rate(self):
        frame = pd.DataFrame({"stage": ["FQC", "FQC"], "defect_qty": [3, 2], "po_qty": [100, None]})
        result = gate_totals(frame)
        self.assertIsNone(result["rate"])
        self.assertIsNone(result["denominator"])
        row, _ = supplier_summary("TU", "ZX", "FG", frame)
        self.assertEqual(row["FQC"], "5 疵点")
        self.assertEqual(row["RPM"], "—")

    def test_supplier_row_reuses_weighted_counts_and_retains_zero_iv(self):
        frame = pd.DataFrame({"stage": ["PQC", "PQC"], "defect_qty": [1, 9], "po_qty": [10, 90]})
        row, details = supplier_summary("TU", "ZX", "FG", frame, {"rpm_now": 747, "nqc_now": 22281}, iv=0)
        self.assertEqual(row["PQC"], "10.00%")
        self.assertEqual(row["IV (案例)"], "0")
        self.assertEqual(details[1]["denominator"], 100)

    def test_empty_and_spc_do_not_assert_zero_or_root_cause(self):
        missing = build_chart_insight({"empty": True})
        self.assertIn("缺失数据不能解释为零问题", missing["interpretation"])
        spc = build_chart_insight({"evidence": {"kind": "spc"}})
        self.assertIn("两类信号", spc["interpretation"])
        self.assertIn("量具", spc["action"])

    def response(self):
        return {"actions": [{"action": "复核当前批次的检验及客户反馈记录", "priority_ccs": ["356209"]}] * 3,
                "charts": [{"id": "trend", "interpretation": "先确认观察期与检验覆盖一致后再判断近期回落。", "action": "复核最新批次及检验样本，并使用相同口径复测。"}]}

    def test_provider_schema_requires_exactly_three_actions_and_complete_charts(self):
        valid = validate_ai_response(self.response(), ["trend"], ["356209"])
        self.assertEqual(len(valid["actions"]), 3)
        for change in ["actions", "charts"]:
            bad = self.response()
            bad[change] = bad[change][1:]
            with self.assertRaises(ValueError):
                validate_ai_response(bad, ["trend"], ["356209"])

    def test_provider_cannot_add_new_cc_or_numbers(self):
        bad = self.response()
        bad["actions"][0]["priority_ccs"] = ["999999"]
        with self.assertRaises(ValueError):
            validate_ai_response(bad, ["trend"], ["356209"])

    def test_existing_aql_reference_is_allowed_but_new_target_is_rejected(self):
        response = self.response()
        response["actions"][0]["action"] = "复核批准的抽样方案，并评估源建议 AQL 1.5 的适用性"
        facts = {"aql_recommendations": [{"recommendation": "AQL 1.5"}]}
        validate_ai_response(response, ["trend"], ["356209"], facts)
        response["charts"][0]["interpretation"] = "承诺下月减少50%的问题，无需额外验证。"
        with self.assertRaises(ValueError):
            validate_ai_response(response, ["trend"], ["356209"], facts)
        bad = self.response()
        bad["actions"][0]["action"] = "下月下降50%"
        with self.assertRaises(ValueError):
            validate_ai_response(bad, ["trend"], ["356209"])


if __name__ == "__main__":
    unittest.main()
