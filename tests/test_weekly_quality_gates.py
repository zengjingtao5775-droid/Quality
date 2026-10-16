"""Weekly TU contracts: ISO boundaries, weighted rates, gaps and disclosures."""
import unittest

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from quality_gate_metrics import gate_metrics
from quality_chart_ui import style_quality_trend
from quality_insights import chart_evidence, chart_signal, build_chart_insight, build_gate_insight_facts


class WeeklyGateTests(unittest.TestCase):
    def frame(self, dates, quantities, defects):
        return pd.DataFrame({"date": pd.to_datetime(dates), "po_qty": quantities, "defect_qty": defects})

    def evidence(self, frame, stage="PQC", cutoff="2026-01-25", start="2025-12-29"):
        _, weeks = gate_metrics(frame, stage, frequency="W-SUN")
        rate = stage != "IQC"
        values = weeks.defect_rate if rate else weeks.defect_qty
        context = {"kind": "trend", "frequency": "W-SUN", "cutoff": cutoff, "start": start,
                   "exception_only": stage == "IQC", "periods": [
                       {"period": str(period.start_time.date()), "numerator": None if pd.isna(row.defect_qty) else row.defect_qty,
                        "denominator": row.po_qty if row.complete_denominator is True or row.complete_denominator == True else None}
                       for period, row in weeks.iterrows()]}
        trace = {"type": "scatter", "mode": "lines+markers", "x": weeks.index.to_timestamp().astype(str).tolist(),
                 "y": [None if pd.isna(value) else value for value in values]}
        return chart_evidence([trace], ".2%" if rate else ",.0f", context)

    def test_monday_through_sunday_and_iso_year_boundary(self):
        frame = self.frame(["2025-12-28", "2025-12-29", "2026-01-04", "2026-01-05"], [10]*4, [1, 2, 3, 4])
        total, weeks = gate_metrics(frame, "IQC", frequency="W-SUN")
        self.assertEqual(weeks.index.start_time.strftime("%Y-%m-%d").tolist(), ["2025-12-22", "2025-12-29", "2026-01-05"])
        self.assertEqual(weeks.defect_qty.tolist(), [1, 5, 4])
        self.assertEqual(total["quantity"], 10)
        self.assertTrue(np.isnan(total["rate"]))

    def test_weekly_rates_are_weighted_and_totals_preserved(self):
        frame = self.frame(["2026-01-05", "2026-01-07", "2026-01-12"], [100, 900, 500], [10, 9, 5])
        for stage in ("PQC", "FQC"):
            total, weeks = gate_metrics(frame, stage, frequency="W-SUN")
            self.assertAlmostEqual(weeks.defect_rate.iloc[0], 19/1000)
            self.assertAlmostEqual(total["rate"], 24/1500)
            self.assertNotAlmostEqual(weeks.defect_rate.iloc[0], (.1+.01)/2)

    def test_missing_weeks_are_gaps_not_zeroes(self):
        frame = self.frame(["2026-01-05", "2026-01-19"], [100, 100], [2, 1])
        for stage in ("IQC", "PQC", "FQC"):
            _, weeks = gate_metrics(frame, stage, frequency="W-SUN")
            self.assertEqual(len(weeks), 3)
            self.assertTrue(pd.isna(weeks.defect_qty.iloc[1]))
            e = self.evidence(frame, stage)
            self.assertIsNone(e["change"])
            self.assertEqual(e["missing_periods"], 1)
            for language in ("中文", "English"):
                text = build_chart_insight({"evidence": e}, language)
                self.assertIn("周" if language == "中文" else "week", text["interpretation"])
                self.assertNotIn("vs 2026-W02", text["finding"])

    def test_missing_denominator_affects_only_its_week(self):
        frame = self.frame(["2026-01-05", "2026-01-06", "2026-01-12"], [100, None, 200], [2, 1, 4])
        total, weeks = gate_metrics(frame, "FQC", frequency="W-SUN")
        self.assertTrue(pd.isna(total["rate"]))
        self.assertTrue(pd.isna(weeks.defect_rate.iloc[0]))
        self.assertAlmostEqual(weeks.defect_rate.iloc[1], .02)
        e = self.evidence(frame)
        self.assertEqual(e["latest_volume"]["numerator"], 4)
        self.assertEqual(e["latest_volume"]["denominator"], 200)

    def test_each_week_uses_its_own_volume_within_same_month(self):
        frame = self.frame(["2026-01-05", "2026-01-12"], [100, 400], [2, 4])
        e = self.evidence(frame)
        self.assertEqual(e["previous_volume"]["denominator"], 100)
        self.assertEqual(e["latest_volume"]["denominator"], 400)
        self.assertEqual(e["period_count"], 2)
        self.assertIn("2026-W03", build_chart_insight({"evidence": e})["finding"])
        self.assertEqual(chart_signal({"evidence": e})["tone"], "good")

    def test_partial_boundary_weeks_are_explicit(self):
        frame = self.frame(["2026-01-07", "2026-01-12"], [100, 200], [2, 4])
        e = self.evidence(frame, cutoff="2026-01-14", start="2026-01-07")
        self.assertTrue(e["partial_first"])
        self.assertTrue(e["partial_latest"])
        self.assertIn("末周未完整", chart_signal({"evidence": e})["label"])
        text = build_chart_insight({"evidence": e})
        self.assertIn("首周", text["interpretation"])
        self.assertIn("末周未完整", text["interpretation"])
        self.assertIn("完整周", text["action"])
        self.assertNotIn("完整月", text["action"])

    def test_missing_latest_week_cannot_be_presented_as_latest_observation(self):
        frame = self.frame(["2026-01-05", "2026-01-12"], [100, None], [2, 4])
        e = self.evidence(frame)
        self.assertTrue(e["latest_period_missing"])
        self.assertEqual(e["latest_volume"]["period"], "2026-01-05")
        self.assertEqual(chart_signal({"evidence": e})["label"], "最新周数据待补齐")

    def test_real_zero_is_retained_and_missing_numerator_is_not_zero(self):
        frame = self.frame(["2026-01-05", "2026-01-12", "2026-01-19"], [100]*3, [2, 0, None])
        _, weeks = gate_metrics(frame, "IQC", frequency="W-SUN")
        self.assertEqual(weeks.defect_qty.iloc[1], 0)
        self.assertTrue(pd.isna(weeks.defect_qty.iloc[2]))

    def test_filter_boundary_does_not_pull_records_from_outside_selection(self):
        frame = self.frame(["2026-01-05", "2026-01-07", "2026-01-11", "2026-01-12"], [100]*4, [7, 2, 3, 9])
        frame = frame.loc[frame.date.between("2026-01-07", "2026-01-11")]
        total, weeks = gate_metrics(frame, "PQC", frequency="W-SUN")
        self.assertEqual(total["quantity"], 5)
        self.assertEqual(weeks.defect_qty.tolist(), [5])
        self.assertEqual(weeks.po_qty.tolist(), [200])

    def test_axes_and_hover_show_iso_week_and_date_range(self):
        for rate in (True, False):
            fig = go.Figure(go.Scatter(x=pd.to_datetime(["2025-12-29", "2026-01-05"]), y=[.1, None], mode="lines+markers", connectgaps=False))
            style_quality_trend(fig, height=245, weekly=True, is_rate=rate, x_label="周次")
            self.assertEqual(fig.layout.xaxis.title.text, "周次")
            self.assertEqual(list(fig.layout.xaxis.ticktext), ["W01<br>2026", "W02<br>2026"])
            self.assertIn("2026-W01", fig.data[0].hovertext[0])
            self.assertIn("2026-01-04", fig.data[0].hovertext[0])
            self.assertFalse(fig.data[0].connectgaps)
            self.assertEqual(fig.data[0].y[0], .1)

    def test_quality_gate_keeps_one_interpretation_and_weekly_causality_boundary(self):
        e = self.evidence(self.frame(["2026-01-05", "2026-01-12"], [100, 200], [2, 3]))
        facts = build_gate_insight_facts("PQC", "pqc_gate", [
            {"id": "pqc_trend", "empty": False, "evidence": e},
            {"id": "pqc_pareto", "empty": False, "evidence": {"kind": "pareto", "ranked": [["Seam", 5]], "total": 5, "top_share": 1, "shown_share": 1}}])
        text = build_chart_insight(facts)
        self.assertEqual(len(text["parts"]), 2)
        self.assertIn("同周明细", text["interpretation"])
        self.assertNotIn("最新月", text["interpretation"])

    def test_narrow_cards_have_evenly_spaced_week_labels_including_endpoints(self):
        dates = pd.date_range("2025-12-29", periods=27, freq="7D")
        fig = go.Figure(go.Scatter(x=dates, y=list(range(27)), mode="lines"))
        style_quality_trend(fig, height=245, weekly=True)
        ticks = list(fig.layout.xaxis.tickvals)
        self.assertEqual(len(ticks), 5)
        self.assertEqual(ticks[0], dates[0])
        self.assertEqual(ticks[-1], dates[-1])
        self.assertTrue(all(b-a >= pd.Timedelta(weeks=6) for a, b in zip(ticks, ticks[1:])))

    def test_monthly_default_for_bme_is_preserved(self):
        frame = self.frame(["2026-01-05", "2026-01-12", "2026-02-02"], [100, 200, 100], [2, 4, 1])
        _, monthly = gate_metrics(frame, "PQC")
        self.assertEqual(monthly.index.astype(str).tolist(), ["2026-01", "2026-02"])
        self.assertAlmostEqual(monthly.defect_rate.iloc[0], .02)

    def test_zero_sample_zero_defect_records_are_neutral_in_pooled_rate(self):
        frame = self.frame(["2026-01-05", "2026-01-06", "2026-01-12"], [100, 0, 200], [2, 0, 4])
        result, weeks = gate_metrics(frame, "FQC", frequency="W-SUN")
        self.assertEqual(result["zero_exposure_rows"], 1)
        self.assertEqual(result["valid_rate_rows"], 2)
        self.assertEqual(result["rows"], 3)
        self.assertAlmostEqual(result["rate"], 6/300)
        self.assertAlmostEqual(weeks.defect_rate.iloc[0], .02)

    def test_zero_exposure_only_week_remains_unavailable(self):
        frame = self.frame(["2026-01-05"], [0], [0])
        result, weeks = gate_metrics(frame, "FQC", frequency="W-SUN")
        self.assertTrue(pd.isna(result["rate"]))
        self.assertTrue(pd.isna(weeks.defect_rate.iloc[0]))
        self.assertFalse(weeks.complete_denominator.iloc[0])

    def test_missing_sample_or_positive_defects_with_zero_sample_still_block_rate(self):
        for sample, defect in ((None, 0), (0, 2)):
            frame = self.frame(["2026-01-05", "2026-01-06"], [100, sample], [2, defect])
            result, weeks = gate_metrics(frame, "FQC", frequency="W-SUN")
            self.assertTrue(pd.isna(result["rate"]))
            self.assertTrue(pd.isna(weeks.defect_rate.iloc[0]))


if __name__ == "__main__":
    unittest.main()
