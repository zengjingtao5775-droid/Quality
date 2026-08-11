from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from bme_quality import (
    build_bme_issue_pareto,
    build_imr_chart_data,
    build_p_chart_data,
    build_xbar_r_chart_data,
    calculate_fsd_customer_ppm,
    load_bme_customer_quality,
    load_bme_quality_events,
    spc_run_rule_flags,
)


ROOT = Path(__file__).resolve().parents[1]


class BmeAnalysisFormulaTest(unittest.TestCase):
    def test_imr_uses_standard_constants_and_excludes_suspect(self) -> None:
        frame = pd.DataFrame({
            "measured_value": [10, 12, 11, 13, 999],
            "event_timestamp": pd.date_range("2026-01-01", periods=5),
            "date": pd.date_range("2026-01-01", periods=5),
            "source_row": range(5),
            "data_quality_flag": ["", "", "", "", "suspect"],
            "spec_low": [0] * 5,
            "spec_high": [20] * 5,
        })
        chart, limits = build_imr_chart_data(frame)
        self.assertAlmostEqual(limits["center"], 11.5)
        self.assertAlmostEqual(limits["mrbar"], (2 + 1 + 2) / 3)
        self.assertAlmostEqual(limits["ucl"], 11.5 + 2.66 * limits["mrbar"])
        self.assertEqual(len(chart), 5)

    def test_run_rules_find_eight_on_one_side_and_six_point_trend(self) -> None:
        flags = spc_run_rule_flags(pd.Series(range(1, 10)), center=0, ucl=100, lcl=-100)
        self.assertTrue(flags["eight_one_side"].any())
        self.assertTrue(flags["six_trend"].any())
        self.assertEqual(int(flags["eight_one_side"].sum()), 2)
        self.assertEqual(int(flags["six_trend"].sum()), 4)

    def test_p_chart_uses_weighted_center_and_variable_limits(self) -> None:
        source = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-08"]), "inspected_qty": [10, 100], "defect_qty": [1, 2]})
        chart, limits = build_p_chart_data(source)
        self.assertAlmostEqual(limits["center"], 3 / 110)
        self.assertNotEqual(chart.loc[0, "ucl"], chart.loc[1, "ucl"])


class BmeAnalysisDataRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = load_bme_quality_events(ROOT)
        cls.customer, cls.orders = load_bme_customer_quality(ROOT)

    def test_fsd_dkl_excludes_other_parts_suppliers(self) -> None:
        dkl = self.events[(self.events["supplier"].eq("FSD")) & (self.events["stage"].eq("DKL"))]
        self.assertEqual(len(dkl), 335)
        self.assertEqual(int(dkl["date"].notna().sum()), 335)

    def test_cmw_iqc_blank_template_rows_are_excluded(self) -> None:
        iqc = self.events[(self.events["supplier"].eq("CMW")) & (self.events["stage"].eq("IQC"))]
        self.assertEqual(len(iqc), 3329)
        self.assertFalse(iqc["date"].isna().any())

    def test_tektro_parameter_retains_hose_length(self) -> None:
        pqc = self.events[(self.events["supplier"].eq("TEKTRO")) & (self.events["stage"].eq("PQC"))]
        self.assertTrue({"850", "950", "1000"}.issubset(set(pqc["family"])))
        self.assertEqual(int(pqc["measured_value"].notna().sum()), 1776)

    def test_combined_issue_pareto_includes_tektro_component_nc(self) -> None:
        start, end = pd.Timestamp("2025-08-11"), pd.Timestamp("2026-08-11")
        period_events = self.events[
            self.events["date"].notna() & self.events["date"].between(start, end)
        ]
        period_customer = self.customer[
            self.customer["date"].notna() & self.customer["date"].between(start, end)
        ]
        pareto, _ = build_bme_issue_pareto(period_events, period_customer, limit=0)
        tektro_w = pareto[
            pareto["supplier"].eq("TEKTRO")
            & pareto["source_scope"].eq("Component")
            & pareto["issue_driver"].eq("Defect Code W")
        ]
        self.assertEqual(float(tektro_w["defect_qty"].iloc[0]), 2681.0)
        self.assertTrue({"CMW", "FSD", "TEKTRO"}.issubset(set(pareto["supplier"])))

    def test_component_source_and_fsd_po_coverage_are_usable(self) -> None:
        self.assertEqual(set(self.customer["supplier"]), {"FSD", "TEKTRO"})
        result = calculate_fsd_customer_ppm(self.customer, self.orders, "2024-01-01", "2026-12-31")
        self.assertGreaterEqual(result["coverage"], 0.90)
        self.assertTrue(np.isfinite(result["ppm"]))
        self.assertTrue(self.orders["subcontractor"].str.contains("FUJI-TA", case=False).all())
        self.assertEqual(float(self.orders.loc[self.orders["po"].eq("751701224"), "ordered_qty"].iloc[0]), 192.0)

    def test_current_period_fsd_kpis_match_source_recalculation(self) -> None:
        start, end = pd.Timestamp("2025-08-10"), pd.Timestamp("2026-08-10")
        period = self.events[self.events["date"].notna() & self.events["date"].between(start, end)]
        inspected = period[
            period["supplier"].eq("FSD")
            & period["stage"].isin(["AQL", "DKL"])
            & period["inspected_qty"].gt(0)
        ]
        self.assertEqual(float(inspected["defect_qty"].sum()), 746.0)
        self.assertEqual(float(inspected["inspected_qty"].sum()), 13826.0)
        ppm = calculate_fsd_customer_ppm(self.customer, self.orders, start, end)
        self.assertEqual(ppm["nc_qty"], 7875.0)
        self.assertEqual(ppm["ordered_qty"], 2320884.0)
        self.assertAlmostEqual(ppm["ppm"], 3393.103662225256)

    def test_tektro_lab_uses_complete_subgroups_of_five(self) -> None:
        lab = self.events[(self.events["supplier"].eq("TEKTRO")) & (self.events["stage"].eq("LAB"))]
        chart, limits = build_xbar_r_chart_data(lab)
        self.assertEqual(len(chart), 164)
        self.assertEqual(int(limits["incomplete_groups"]), 8)
        self.assertIn("range_signal", chart.columns)

    def test_torque_suspects_remain_visible_but_are_flagged(self) -> None:
        torque = self.events[(self.events["supplier"].eq("CMW")) & (self.events["stage"].eq("MACHINE"))]
        self.assertEqual(int(torque["data_quality_flag"].ne("").sum()), 2)
        self.assertTrue(torque["trace_number"].astype(str).str.strip().ne("").any())
        self.assertIn("comments", torque.columns)


if __name__ == "__main__":
    unittest.main()
