"""Source quantities and Top-N shares for the unified defect Pareto."""
import unittest
import numpy as np
import pandas as pd
from dashboard_scope import DashboardScope, filter_records, ranked_cc_risk, ranked_inspection_defects
from quality_insights import build_chart_insight


class InspectionParetoTests(unittest.TestCase):
    def rows(self):
        return pd.DataFrame({
            "stage": ["PQC", "FQC", "PQC", "FQC", "IQC", "IV", "PQC", "FQC", "PQC"],
            "defect_name": ["线头", "线头", "跳线", "线头；跳线", "线头", "线头", "", "/", "Family"],
            "defect_qty": [20, 5, 10, 4, 99, 49, 3, 2, 7],
            "category_type": ["defect"] * 8 + ["product_family"],
        })

    def test_merge_exact_names_but_not_composite_descriptions(self):
        r = ranked_inspection_defects(self.rows()).set_index("issue_type")
        self.assertEqual(r.loc["线头", "defect_qty"], 25)
        self.assertEqual(r.loc["线头", "pqc_qty"], 20)
        self.assertEqual(r.loc["线头", "aql_qty"], 5)
        self.assertEqual(r.loc["线头；跳线", "defect_qty"], 4)
        self.assertEqual(r.loc["跳线", "defect_qty"], 10)

    def test_defect_description_is_not_cleaned_as_a_numeric_identifier(self):
        rows = pd.DataFrame({'stage':['PQC','FQC'], 'defect_name':['Mark 4.0','Mark 4'], 'defect_qty':[2,3]})
        r = ranked_inspection_defects(rows).set_index('issue_type')
        self.assertEqual(r.loc['Mark 4.0','defect_qty'],2)
        self.assertEqual(r.loc['Mark 4','defect_qty'],3)

    def test_keep_unclassified_quantities_and_family_is_not_defect_name(self):
        r = ranked_inspection_defects(self.rows()).set_index("issue_type")
        self.assertEqual(r.loc["未分类", "defect_qty"], 5)
        self.assertEqual(r.loc["未分类（仅有产品族）", "defect_qty"], 7)
        self.assertNotIn("Family", r.index)
        self.assertEqual(r.defect_qty.sum(), 51)

    def test_iqc_and_iv_are_never_added_to_inspection_quantity(self):
        r = ranked_inspection_defects(self.rows())
        self.assertEqual(r.defect_qty.sum(), 51)
        self.assertEqual(r.pqc_qty.sum(), 40)
        self.assertEqual(r.aql_qty.sum(), 11)

    def test_source_switch_recomputes_full_population(self):
        p = ranked_inspection_defects(self.rows(), ("PQC",))
        a = ranked_inspection_defects(self.rows(), ("AQL",))
        self.assertEqual(p.defect_qty.sum(), 40)
        self.assertEqual(a.defect_qty.sum(), 11)
        self.assertEqual(p.aql_qty.sum(), 0)
        self.assertEqual(a.pqc_qty.sum(), 0)
        self.assertAlmostEqual(p.cumulative_share.iloc[-1], 1)
        self.assertAlmostEqual(a.cumulative_share.iloc[-1], 1)

    def test_top_ten_does_not_renormalize_its_cumulative_share(self):
        rows = pd.DataFrame({"stage": ["PQC"] * 12, "defect_name": list("abcdefghijkl"), "defect_qty": list(range(1, 13))})
        r = ranked_inspection_defects(rows)
        self.assertEqual(len(r.head(10)), 10)
        self.assertAlmostEqual(r.head(10).cumulative_share.iloc[-1], 75/78)
        self.assertAlmostEqual(r.cumulative_share.iloc[-1], 1)

    def test_missing_zero_negative_and_infinite_quantities_not_imputed(self):
        rows = pd.DataFrame({"stage": ["PQC"] * 6, "defect_name": list("abcdef"), "defect_qty": [None, 0, -1, np.inf, 'bad', 2]})
        r = ranked_inspection_defects(rows)
        self.assertEqual(r.issue_type.tolist(), ['f'])
        self.assertEqual(r.defect_qty.tolist(), [2])
        self.assertTrue(ranked_inspection_defects(pd.DataFrame()).empty)

    def test_product_and_date_filter_changes_ranked_source_quantities(self):
        rows = pd.DataFrame({"stage": ["PQC", "FQC", "PQC"], "defect_name": ['a','a','b'], "defect_qty": [2,3,9],
                             "product_code": ['111111','111111','222222'], "model_code": ['1000001']*3,
                             "date": ['2026-06-01','2026-06-30T23:59:59','2026-07-01']})
        s = DashboardScope(ccs=('111111',), start='2026-06-01', end='2026-06-30')
        self.assertEqual(ranked_inspection_defects(filter_records(rows,s,supplier='ZX')).defect_qty.sum(), 5)
        self.assertTrue(ranked_inspection_defects(filter_records(rows,DashboardScope(ccs=('999999',)),supplier='ZX')).empty)

    def test_cc_top_ten_all_and_small_populations(self):
        f = pd.DataFrame({'code':[str(i) for i in range(12)],'score':list(range(12))})
        top, stats = ranked_cc_risk(f,'code','score')
        all_rows,_ = ranked_cc_risk(f,'code','score',False)
        self.assertEqual(len(top),10)
        self.assertEqual(len(all_rows),12)
        self.assertAlmostEqual(stats['share'],65/66)
        self.assertAlmostEqual(top.cumulative_share.iloc[-1],65/66)
        small,_ = ranked_cc_risk(f.head(3),'code','score')
        self.assertEqual(len(small),3)

    def test_insight_retains_repeated_inspections_and_separate_iv_unit(self):
        facts={'evidence':{'kind':'pareto','ranked':[['a',5]],'total':10,'top_share':.5,'shown_share':.5,'inspection_quantities':True}}
        insight=build_chart_insight(facts)
        self.assertIn('不代表唯一不良件数',insight['interpretation'])
        self.assertIn('IV 案例单独统计',insight['interpretation'])


if __name__ == '__main__':
    unittest.main()
