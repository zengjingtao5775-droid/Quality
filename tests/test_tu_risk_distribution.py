"""Presentation groups preserve score values, unknowns and filter membership."""
import unittest
import numpy as np
import pandas as pd
from tu_risk_poc_ui import risk_distribution_groups, build_risk_distribution_figure


class DistributionTests(unittest.TestCase):
    def rows(self):
        return pd.DataFrame({'entity':['335330','335331','335332','335333','335334','335335'],
            'supplier_score':[8.,10.,42.,45.,75.,80.], 'client_score':[7.,10.,44.,48.,78.,84.],
            'risk_lower':[7.,9.,40.,44.,70.,80.], 'risk_upper':[17.,19.,50.,54.,80.,90.],
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
        self.assertEqual(set(fig.data[0].text),set(grouped.loc[grouped.risk_group.eq('high'),'entity']))
        self.assertEqual(len(build_risk_distribution_figure(grouped,'CC',selected_groups=[]).data),0)

    def test_missing_axes_are_not_imputed_as_zero(self):
        rows=self.rows();rows.loc[0,'supplier_score']=np.nan;rows.loc[1,'client_score']=np.inf
        grouped=risk_distribution_groups(rows)
        self.assertNotIn('335330',grouped.entity.tolist());self.assertNotIn('335331',grouped.entity.tolist())
        self.assertTrue(pd.isna(rows.loc[0,'supplier_score']))

    def test_one_position_and_empty_selection_do_not_invent_high_risk(self):
        row=self.rows().iloc[:1].copy()
        self.assertEqual(risk_distribution_groups(row).risk_group.tolist(),['single'])
        grouped=risk_distribution_groups(pd.DataFrame())
        self.assertTrue(grouped.empty)
        self.assertEqual(len(build_risk_distribution_figure(grouped,'CC').data),0)

    def test_boundary_axes_and_english_hover_retain_pending_bounds(self):
        rows=self.rows();rows.loc[0,['supplier_score','client_score']]=[100.,100.]
        fig=build_risk_distribution_figure(risk_distribution_groups(rows),'Model',lambda zh,en:en)
        self.assertIn('PQC + AQL',fig.layout.xaxis.title.text)
        self.assertIn('RPM + IV',fig.layout.yaxis.title.text)
        self.assertGreater(fig.layout.xaxis.range[1],100)
        self.assertGreater(fig.layout.yaxis.range[1],100)
        self.assertIn('Risk Score',fig.data[0].hovertemplate)
        self.assertTrue(all(x.marker.size==18 for x in fig.data))


if __name__=='__main__':unittest.main()
