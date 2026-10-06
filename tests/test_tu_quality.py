import unittest

import pandas as pd

from tu_quality import build_zx_quality_gates


class ZXGateSourceTest(unittest.TestCase):
    def test_iqc_counts_records_without_summing_mixed_units_or_inventing_denominator(self):
        incoming = pd.DataFrame({'date': ['2026-01-03', '2026-01-04'],
                                 'issue': ['印刷不良', '残次'], 'material_qty': [960, 150.6], 'unit': ['片', '米']})
        summary, pareto = build_zx_quality_gates(incoming, pd.DataFrame(), pd.DataFrame())
        self.assertEqual(summary.defect_qty.sum(), 2)
        self.assertTrue(summary.po_qty.isna().all())
        self.assertEqual(pareto.defect_qty.tolist(), [1, 1])
        self.assertFalse(summary.rework_available.any())

    def test_pqc_keeps_weighted_inspection_denominator_and_source_description(self):
        process = pd.DataFrame({'date': ['2026-01-03', '2026-01-04'], 'factory_code': ['ZX', 'ZX'],
                                'inspection_stage': ['Online QC', 'End QC / FQC'],
                                'qty_inspected': [100, 10], 'defect_qty': [2, 1],
                                'defect_type': ['线头', '线头；针洞']})
        summary, pareto = build_zx_quality_gates(pd.DataFrame(), process, pd.DataFrame())
        self.assertAlmostEqual(summary.defect_qty.sum() / summary.po_qty.sum(), 3 / 110)
        self.assertEqual(pareto.defect_name.tolist(), ['线头', '线头；针洞'])
        self.assertEqual(pareto.defect_qty.sum(), 3)

    def test_fqc_uses_sample_size_not_po_size_and_keeps_composite_counts_intact(self):
        final = pd.DataFrame({'date': pd.to_datetime(['2026-01-03T00:00:00+08:00']),
                              'po_qty': [10000], 'sampling_size': [32], 'defect_qty': [4],
                              'visual_issue': ['线头，扭指'], 'size_issue': ['尺寸超差']})
        summary, pareto = build_zx_quality_gates(pd.DataFrame(), pd.DataFrame(), final)
        self.assertEqual(summary.po_qty.sum(), 32)
        self.assertEqual(pareto.defect_qty.sum(), 4)
        self.assertEqual(len(pareto), 1)
        self.assertEqual(pareto.defect_name.iloc[0], '线头，扭指；尺寸超差')
        self.assertTrue(summary.rework_qty.isna().all())

    def test_missing_data_stays_empty_with_filterable_dates(self):
        summary, pareto = build_zx_quality_gates(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        self.assertTrue(summary.empty and pareto.empty)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(summary.date))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(pareto.date))

    def test_fqc_placeholder_names_do_not_become_defect_types(self):
        final = pd.DataFrame({'date': ['2026-01-03', '2026-01-04'], 'defect_qty': [2, 3],
                              'visual_issue': ['0', '线头'], 'important_issue': ['0.0', '线头']})
        summary, pareto = build_zx_quality_gates(pd.DataFrame(), pd.DataFrame(), final)
        self.assertEqual(pareto.defect_name.tolist(), ['', '线头'])
        self.assertEqual(summary.defect_qty.sum(), 5)


if __name__ == '__main__':
    unittest.main()
