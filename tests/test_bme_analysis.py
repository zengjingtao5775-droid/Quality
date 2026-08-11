from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from bme_quality import (
    build_bme_issue_pareto,
    build_bme_product_master,
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
        suspect = chart.loc[chart["is_data_quality_suspect"]].iloc[0]
        self.assertFalse(bool(suspect["signal"]))
        self.assertTrue(pd.isna(suspect["moving_range"]))
        self.assertTrue(bool(limits["stable"]))

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

    def test_fsd_dkl_reads_final_decision_and_all_control_columns(self) -> None:
        dkl = self.events[(self.events["supplier"].eq("FSD")) & (self.events["stage"].eq("DKL"))]
        period = dkl[dkl["date"].between(pd.Timestamp("2025-08-11"), pd.Timestamp("2026-08-11"))]
        self.assertEqual(period["result"].value_counts().to_dict(), {"OK": 124, "NOK": 28})
        nok_items = int(
            period.loc[period["result"].eq("NOK"), "issue_driver"]
            .map(lambda value: len([item for item in str(value).split(" / ") if item]))
            .sum()
        )
        self.assertEqual(nok_items, 81)

    def test_fsd_aql_no_decisions_are_alerts_even_when_nc_quantity_is_zero(self) -> None:
        aql = self.events[(self.events["supplier"].eq("FSD")) & (self.events["stage"].eq("AQL"))]
        no_decisions = aql[aql["result"].str.upper().eq("NO")]
        self.assertEqual(int(no_decisions["defect_qty"].eq(0).sum()), 7)
        self.assertTrue(no_decisions["is_alert"].all())

    def test_cmw_iqc_blank_template_rows_are_excluded(self) -> None:
        iqc = self.events[(self.events["supplier"].eq("CMW")) & (self.events["stage"].eq("IQC"))]
        self.assertEqual(len(iqc), 3329)
        self.assertFalse(iqc["date"].isna().any())

    def test_tektro_parameter_retains_hose_length(self) -> None:
        pqc = self.events[(self.events["supplier"].eq("TEKTRO")) & (self.events["stage"].eq("PQC"))]
        self.assertTrue({"850", "950", "1000"}.issubset(set(pqc["family"])))
        self.assertEqual(int(pqc["measured_value"].notna().sum()), 1776)
        self.assertTrue(pqc["spec_low"].isna().all())
        self.assertTrue(pqc["spec_high"].isna().all())
        self.assertFalse(pqc["result"].astype(str).str.strip().ne("").any())

    def test_product_master_links_only_auditable_quality_gates(self) -> None:
        master = build_bme_product_master(self.events)
        self.assertEqual(set(master["quality_gate"]), {"IQC", "PQC", "FQC"})
        mpa25 = master[master["product_key"].eq("FSD|MPA25")]
        self.assertEqual(set(mpa25["quality_gate"]), {"PQC", "FQC"})
        fsd_iqc = master[master["supplier"].eq("FSD") & master["quality_gate"].eq("IQC")]
        self.assertTrue(fsd_iqc["product_key"].str.match(r"FSD\|IQC_ITEM\|[A-Z0-9]+$").all())
        self.assertTrue(fsd_iqc["product_label"].str.match(r"料号 .+").all())
        self.assertTrue(fsd_iqc["product_group"].eq("IQC 来料料号").all())
        self.assertTrue(fsd_iqc["product_link_method"].eq("FSD IQC source item code; no BOM link to bike model").all())
        expl100_grey = master[master["product_key"].eq("CMW|5535130")]
        self.assertEqual(set(expl100_grey["quality_gate"]), {"FQC"})
        self.assertTrue(expl100_grey["product_label"].str.startswith("整车料号 5535130 ·").all())
        self.assertTrue(expl100_grey["product_link_method"].eq("CMW FQC whole-bike item code").all())
        cmw_fqc = master[master["supplier"].eq("CMW") & master["quality_gate"].eq("FQC")]
        self.assertTrue(cmw_fqc["product_key"].str.match(r"CMW\|\d+$").all())
        cmw_pqc = master[master["supplier"].eq("CMW") & master["quality_gate"].eq("PQC")]
        self.assertTrue(cmw_pqc["product_link_method"].eq("CMW PQC model; no exact whole-bike item-code link").all())
        self.assertTrue(cmw_pqc["product_group"].eq("PQC 车型（未对应整车料号）").all())
        cmw_iqc = master[master["supplier"].eq("CMW") & master["quality_gate"].eq("IQC")]
        self.assertTrue(cmw_iqc["product_link_method"].eq("CMW component code; no BOM link to bike model").all())
        self.assertTrue(cmw_iqc["product_group"].eq("来料零部件").all())
        self.assertFalse(cmw_iqc["model_item_code"].astype(str).str.endswith(".0").any())

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
        process_source_total = float(
            period_events.loc[
                period_events["is_alert"]
                & period_events["defect_qty"].gt(0)
                & ~period_events["issue_driver"].fillna("").str.fullmatch(
                    r"|No recorded NOK control|Inspection result|Not recorded|未记录",
                    case=False,
                    na=True,
                ),
                "defect_qty",
            ].sum()
        )
        self.assertEqual(
            float(pareto.loc[pareto["source_scope"].eq("Process"), "defect_qty"].sum()),
            process_source_total,
        )

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
