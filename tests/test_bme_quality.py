from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from bme_quality import (
    bme_events_to_alerts,
    load_bme_quality_events,
    summarize_spc_process_risk,
)


ROOT = Path(__file__).resolve().parents[1]


class BmeQualityDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = load_bme_quality_events(ROOT)

    def test_all_requested_suppliers_and_gates_are_loaded(self) -> None:
        self.assertEqual(set(self.events["supplier"]), {"FSD", "CMW", "TEKTRO"})
        self.assertTrue({"IQC", "PQC", "AQL", "DKL", "MACHINE", "LAB", "REWORK"}.issubset(set(self.events["stage"])))

    def test_fsd_uses_only_the_canonical_workbook(self) -> None:
        fsd_sources = set(self.events.loc[self.events["supplier"].eq("FSD"), "source_file"])
        self.assertEqual(fsd_sources, {"BME Database/FSD/FSD P2 data input.xlsx"})

    def test_end_qc_is_not_invented(self) -> None:
        self.assertNotIn("END_QC", set(self.events.loc[self.events["supplier"].eq("FSD"), "stage"]))

    def test_missing_tektro_pqc_spec_does_not_trigger_ng(self) -> None:
        view = self.events[(self.events["supplier"].eq("TEKTRO")) & (self.events["stage"].eq("PQC"))]
        self.assertGreater(len(view), 0)
        self.assertTrue(view["spec_low"].isna().all() and view["spec_high"].isna().all())
        self.assertFalse(view["is_alert"].any())

    def test_tektro_lab_uses_source_200_kgf_limit(self) -> None:
        view = self.events[(self.events["supplier"].eq("TEKTRO")) & (self.events["stage"].eq("LAB"))]
        self.assertGreater(len(view), 0)
        self.assertTrue(view["spec_low"].dropna().eq(200).all())
        expected = view["measured_value"].lt(200) & view["measured_value"].notna()
        pd.testing.assert_series_equal(view["is_alert"].reset_index(drop=True), expected.reset_index(drop=True), check_names=False)

    def test_cmw_torque_range_is_not_treated_as_a_negative_number(self) -> None:
        view = self.events[(self.events["supplier"].eq("CMW")) & (self.events["stage"].eq("MACHINE"))]
        bounded = view[view["spec_low"].notna() & view["spec_high"].notna() & view["measured_value"].notna()]
        self.assertGreater(len(bounded), 0)
        self.assertLess(int(view["is_alert"].sum()), len(view) // 10)
        outside = bounded["measured_value"].lt(bounded["spec_low"]) | bounded["measured_value"].gt(bounded["spec_high"])
        self.assertTrue(bounded.loc[outside, "is_alert"].all())

    def test_fsd_aql_dkl_week_is_converted_to_date(self) -> None:
        view = self.events[(self.events["supplier"].eq("FSD")) & (self.events["stage"].isin(["AQL", "DKL"]))]
        self.assertGreater(view["date"].notna().sum(), 0)

    def test_alert_interface_retains_real_or_unavailable_status(self) -> None:
        alerts = bme_events_to_alerts(self.events)
        required = {"community", "supplier_dpp", "alert_type", "risk_level", "status", "spec_text", "source"}
        self.assertTrue(required.issubset(alerts.columns))
        self.assertFalse(alerts["status"].fillna("").eq("").any())
        self.assertTrue(alerts["status"].isin(["Open", "In progress", "Closed", "Status unavailable"]).all())


class BmeSpcRiskSummaryTest(unittest.TestCase):
    def test_imr_summary_separates_specification_breaches_from_spc_signals(self) -> None:
        frame = pd.DataFrame({
            "event_timestamp": pd.date_range("2026-01-01", periods=6, freq="D"),
            "date": pd.date_range("2026-01-01", periods=6, freq="D"),
            "source_row": range(2, 8),
            "measured_value": [10.0, 10.1, 9.9, 10.0, 10.2, 12.0],
            "spec_low": [9.0] * 6,
            "spec_high": [11.0] * 6,
            "data_quality_flag": [""] * 6,
        })

        summary = summarize_spc_process_risk("imr", frame)

        self.assertTrue(summary["has_specification"])
        self.assertEqual(summary["measurement_count"], 6)
        self.assertEqual(summary["specification_breaches"], 1)
        self.assertAlmostEqual(summary["specification_rate"], 1 / 6)
        self.assertIn("signal_count", summary)

    def test_stability_only_sequence_does_not_invent_product_specification(self) -> None:
        frame = pd.DataFrame({
            "event_timestamp": pd.date_range("2026-01-01", periods=6, freq="D"),
            "date": pd.date_range("2026-01-01", periods=6, freq="D"),
            "source_row": range(2, 8),
            "measured_value": [10.0, 10.1, 9.9, 10.0, 10.2, 10.1],
            "spec_low": [None] * 6,
            "spec_high": [None] * 6,
            "data_quality_flag": [""] * 6,
        })

        summary = summarize_spc_process_risk("imr_stability", frame)

        self.assertFalse(summary["has_specification"])
        self.assertEqual(summary["specification_breaches"], 0)


if __name__ == "__main__":
    unittest.main()
