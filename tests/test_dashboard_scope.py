import unittest

import pandas as pd

from dashboard_scope import (
    DashboardScope, count_iv_cases, customer_totals, filter_records,
    fsd_item_model_links, ranked_cc_risk, select_customer_grain,
    select_fsd_customer,
)


class DashboardSelectionTests(unittest.TestCase):
    def test_multiselect_union_and_cross_field_intersection(self):
        records = pd.DataFrame({
            "supplier": ["ZX", "ZX", "ZX", "CMW"],
            "product_code": ["111111", "111111", "222222", "111111"],
            "model_code": ["1000001", "1000002", "2000001", "1000001"],
            "date": ["2026-07-01", "2026-07-31 23:59:59", "2026-07-31", "2026-07-31"],
            "qty": [100, 200, 300, 900],
        })
        scope = DashboardScope(suppliers=("ZX",), ccs=("111111", "222222"), models=("1000002", "2000001"), start="2026-07-01", end="2026-07-31")
        self.assertEqual(filter_records(records, scope).qty.tolist(), [200, 300])

    def test_model_selection_does_not_inherit_sibling_models(self):
        cases = pd.DataFrame({
            "case_id": ["case1", "case1", "case2", "case3", "case4"],
            "product_code": ["111111"] * 5,
            "model_code": ["1000001", "1000001", "1000002", "1000001", "1000001"],
            "date": ["2026-01-01"] * 4 + ["2025-01-01"],
            "responsibility_stage": ["Before Sales"] * 3 + ["After Sales", "Before Sales"],
        })
        scope = DashboardScope(models=("1000001",), start="2026-01-01", end="2026-12-31")
        self.assertEqual(count_iv_cases(cases, scope), 1)
        self.assertEqual(count_iv_cases(cases, DashboardScope(models=("9999999",), start=scope.start, end=scope.end)), 0)
        self.assertIsNone(count_iv_cases(cases.iloc[:0], scope))

    def test_calendar_filters_preserve_local_inspection_day(self):
        frame = pd.DataFrame({"date": ["2026-07-01T00:00:00+08:00", "2026-07-01T23:59:59+08:00", "2026-07-02T00:00:00+08:00"], "qty": [1, 2, 3]})
        selected = filter_records(frame, DashboardScope(start="2026-07-01", end="2026-07-01"))
        self.assertEqual(selected.qty.tolist(), [1, 2])

    def test_rpm_is_quantity_weighted_and_cc_model_totals_are_not_added(self):
        source = pd.DataFrame({
            "customer_grain": ["CC", "Model", "Model"],
            "product_code": ["111111"] * 3,
            "model_code": ["", "1000001", "1000002"],
            "returned_now": [20, 10, 10], "sold_now": [1100, 1000, 100],
            "nqc_now": [600, 100, 500],
        })
        cc = customer_totals(select_customer_grain(source, DashboardScope()))
        both = customer_totals(select_customer_grain(source, DashboardScope(models=("1000001", "1000002"))))
        self.assertAlmostEqual(cc["rpm_now"], 20 / 1100 * 1_000_000)
        self.assertEqual(cc["nqc_now"], 600)
        self.assertEqual(cc, both)
        one = customer_totals(select_customer_grain(source, DashboardScope(models=("1000001",))))
        self.assertEqual(one["rpm_now"], 10_000)
        self.assertEqual(one["nqc_now"], 100)

    def test_missing_link_or_denominator_never_returns_factory_metric(self):
        data = pd.DataFrame({"product_code": ["111111"], "returned_now": [10], "sold_now": [None], "nqc_now": [None]})
        self.assertIsNone(customer_totals(data)["rpm_now"])
        self.assertIsNone(customer_totals(data)["nqc_now"])
        selected = filter_records(data, DashboardScope(models=("1000001",)), date_col=None)
        self.assertTrue(selected.empty)
        self.assertIsNone(customer_totals(selected)["rpm_now"])

    def test_zero_sales_row_is_included_in_sum_formula(self):
        data = pd.DataFrame({"returned_now": [2, 3], "sold_now": [100, 0], "nqc_now": [10, 0]})
        self.assertEqual(customer_totals(data)["rpm_now"], 50_000)
        self.assertEqual(customer_totals(data)["nqc_now"], 10)

    def test_net_sales_adjustments_remain_in_aggregated_denominator(self):
        data = pd.DataFrame({"returned_now": [2, 3], "sold_now": [100, -5], "nqc_now": [10, 0]})
        self.assertAlmostEqual(customer_totals(data)["rpm_now"], 5 / 95 * 1_000_000)
        self.assertIsNone(customer_totals(data.iloc[[1]])["rpm_now"])

    def test_exact_fsd_mapping_counts_shared_finished_model_once(self):
        mapping = pd.DataFrame({
            "item_code": ["partA", "partB", "bikeA", "bikeB"],
            "model_code": ["", "", "1000001", "1000002"],
            "record_type": ["Frame", "Frame", "Bike", "Bike"],
            "raw_frame_key": ["RAW-A", "RAW-A", "RAW-A", "RAW-B"],
            "raw_fork_key": [""] * 4,
        })
        rpm = pd.DataFrame({"product_code": ["1000001", "1000002", "otherVendor"], "returned_now": [2, 8, 999], "sold_now": [100, 400, 1], "nqc_now": [20, 80, 999]})
        links = fsd_item_model_links(mapping, rpm.product_code)
        selected = select_fsd_customer(rpm, DashboardScope(ccs=("partA", "partB")), links)
        self.assertEqual(selected.product_code.tolist(), ["1000001"])
        self.assertEqual(customer_totals(selected)["rpm_now"], 20_000)
        self.assertEqual(customer_totals(selected)["nqc_now"], 20)
        self.assertTrue(select_fsd_customer(rpm, DashboardScope(ccs=("unknown",)), links).empty)
        self.assertTrue(select_fsd_customer(rpm, DashboardScope(suppliers=("CMW",)), links).empty)

    def test_top_twenty_percent_retains_cluster_scores_and_excludes_missing(self):
        frame = pd.DataFrame({"code": [str(i) for i in range(11)] + ["unknown"], "score": list(range(1, 12)) + [None]})
        ranked, meta = ranked_cc_risk(frame, "code", "score")
        self.assertEqual(ranked.cc.tolist(), ["10", "9", "8"])
        self.assertEqual(ranked.risk_score.tolist(), [11, 10, 9])
        self.assertEqual(meta["total"], 11)
        self.assertAlmostEqual(meta["share"], 30 / 66)


if __name__ == "__main__":
    unittest.main()
