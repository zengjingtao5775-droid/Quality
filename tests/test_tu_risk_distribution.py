"""Presentation groups preserve score values, unknowns and filter membership."""
import unittest
import numpy as np
import pandas as pd
from tu_risk_poc_ui import risk_distribution_groups, build_risk_distribution_figure
from tu_cluster_selection import FOCUS_KEY, OVERLAP_KEY, select_overlap_member, sync_cluster_focus


class DistributionTests(unittest.TestCase):
    def rows(self):
        return pd.DataFrame({'entity':['335330','335331','335332','335333','335334','335335'],
            'supplier_score':[8.,10.,42.,45.,75.,80.], 'client_score':[7.,10.,44.,48.,78.,84.],
            'risk_lower':[7.,9.,25.,34.,35.,80.], 'risk_upper':[17.,19.,50.,54.,80.,90.],
            'strategy_status':['pending']*6})

    def test_pending_strategy_still_has_risk_colors_and_preserves_scores(self):
        rows=self.rows();before=rows.copy(deep=True)
        grouped=risk_distribution_groups(rows)
        pd.testing.assert_frame_equal(rows,before)
        self.assertEqual(set(grouped.risk_group),{'high','medium','low'})
        for field in ['supplier_score','client_score','risk_lower','risk_upper']:
            self.assertEqual(grouped.set_index('entity')[field].to_dict(),before.set_index('entity')[field].to_dict())
        fig=build_risk_distribution_figure(grouped,'CC')
        self.assertEqual({x.marker.color for x in fig.data},{'#e85d68','#f0a94a','#2aa876'})
        self.assertTrue(all(x.mode=='markers' for x in fig.data))
        self.assertTrue(set(rows.entity).issubset({x.text for x in fig.layout.annotations}))
        points={(float(x),float(y)) for trace in fig.data for x,y in zip(trace.x,trace.y)}
        self.assertEqual(points,set(zip(rows.supplier_score,rows.client_score)))

    def test_groups_are_stable_under_input_reordering_and_display_filter(self):
        rows=self.rows();grouped=risk_distribution_groups(rows)
        shuffled=risk_distribution_groups(rows.sample(frac=1,random_state=4))
        self.assertEqual(grouped.set_index('entity').risk_group.to_dict(),shuffled.set_index('entity').risk_group.to_dict())
        fig=build_risk_distribution_figure(grouped,'CC',selected_groups=['high'])
        self.assertEqual(len(fig.data),1)
        shown = {entity for entity, _ in fig.data[0].customdata}
        self.assertEqual(shown, set(grouped.loc[grouped.risk_group.eq('high'), 'entity']))
        self.assertEqual(len(build_risk_distribution_figure(grouped,'CC',selected_groups=[]).data),0)

    def test_missing_axes_are_not_imputed_as_zero(self):
        rows=self.rows();rows.loc[0,'supplier_score']=np.nan;rows.loc[1,'client_score']=np.inf
        grouped=risk_distribution_groups(rows)
        self.assertNotIn('335330',grouped.entity.tolist());self.assertNotIn('335331',grouped.entity.tolist())
        self.assertTrue(pd.isna(rows.loc[0,'supplier_score']))

    def test_single_model_uses_its_score_and_empty_results_are_supported(self):
        row=self.rows().iloc[:1].copy()
        self.assertEqual(risk_distribution_groups(row).risk_group.tolist(),['low'])
        self.assertEqual(risk_distribution_groups(row.assign(risk_lower=70.)).risk_group.tolist(),['high'])
        grouped=risk_distribution_groups(pd.DataFrame())
        self.assertTrue(grouped.empty)
        self.assertEqual(len(build_risk_distribution_figure(grouped,'CC').data),0)

    def test_same_coordinates_can_have_different_levels_at_custom_boundaries(self):
        rows = self.rows().iloc[:4].assign(
            supplier_score=50., client_score=50., risk_lower=[24.99, 25., 34.99, 35.],
        )
        levels = risk_distribution_groups(rows, (25., 35.))
        self.assertEqual(levels.risk_group.tolist(), ['low', 'medium', 'medium', 'high'])
        pd.testing.assert_frame_equal(levels.drop(columns='risk_group'), rows)
        self.assertEqual(risk_distribution_groups(rows, (40., 70.)).risk_group.tolist(), ['low'] * 4)

    def test_overlapping_markers_show_count_and_open_exact_member_selection(self):
        rows = self.rows().iloc[:4].assign(
            supplier_score=50., client_score=50., risk_lower=[24.99, 25., 34.99, 35.],
            cc=['123451', '123452', '123453', '123454'],
        )
        levels = risk_distribution_groups(rows)
        fig = build_risk_distribution_figure(levels, 'Model', focused_cc='123451')
        self.assertEqual(len(fig.data), 1)
        point = fig.data[0]
        self.assertEqual((list(point.x), list(point.y)), ([50.], [50.]))
        self.assertEqual(point.name, '高风险')
        self.assertEqual(tuple(point.selectedpoints), (0,))
        self.assertEqual(list(point.text), ['×4'])
        self.assertEqual(point.mode, 'markers+text')
        self.assertTrue(all(model in point.hovertext[0] for model in rows.entity))
        filtered = build_risk_distribution_figure(levels, 'Model', selected_groups=['medium', 'low'])
        self.assertEqual(filtered.data[0].name, '中风险')
        self.assertEqual(list(filtered.data[0].text), ['×3'])

        marker = str(rows.entity.iloc[-1])
        state = {'chart': {'selection': {'points': [{'customdata': list(point.customdata[0])}]}}}
        sync_cluster_focus(state, 'chart', list(rows.cc), {marker})
        self.assertEqual(state[OVERLAP_KEY], marker)
        self.assertEqual(state[FOCUS_KEY], '')
        state['choice'] = str(rows.entity.iloc[0])
        select_overlap_member(state, 'choice', dict(zip(rows.entity, rows.cc)))
        self.assertEqual(state[FOCUS_KEY], '123451')

    def test_boundary_axes_and_english_hover_retain_pending_bounds(self):
        rows=self.rows();rows.loc[0,['supplier_score','client_score']]=[100.,100.]
        rows.loc[1,['supplier_score','client_score']]=[0.,0.]
        fig=build_risk_distribution_figure(risk_distribution_groups(rows),'Model',lambda zh,en:en)
        self.assertIn('PQC + AQL',fig.layout.xaxis.title.text)
        self.assertIsNone(fig.layout.yaxis.title.text)
        axis_title = next(a for a in fig.layout.annotations if a.xref == 'paper')
        self.assertIn('Return Qty + IV Qty', axis_title.text)
        self.assertEqual((axis_title.x, axis_title.y, axis_title.yanchor), (0, 1, 'bottom'))
        for axis, side in ((fig.layout.xaxis, 'bottom'), (fig.layout.yaxis, 'left')):
            self.assertEqual(axis.range, (0, 100))
            self.assertEqual(axis.side, side)
            self.assertTrue(axis.showline)
            self.assertEqual(axis.layer, 'below traces')
        points = {(float(x), float(y)) for trace in fig.data for x, y in zip(trace.x, trace.y)}
        self.assertTrue({(0., 0.), (100., 100.)}.issubset(points))
        self.assertTrue(all(trace.cliponaxis is False for trace in fig.data))
        labels = {annotation.text: annotation for annotation in fig.layout.annotations if annotation.xref == 'x'}
        self.assertEqual(set(labels), set(rows.entity))
        self.assertLess(labels[rows.entity.iloc[1]].ay, 0)
        self.assertGreater(labels[rows.entity.iloc[0]].ay, 0)
        self.assertIn('Risk Score',fig.data[0].hovertext[0])
        self.assertTrue(all(x.marker.size==18 for x in fig.data))


if __name__=='__main__':unittest.main()
