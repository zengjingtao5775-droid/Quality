"""Reader-facing metrics and axis contracts shared by TU and BME."""
import unittest
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from quality_chart_ui import build_quality_pareto, style_quality_trend
from quality_gate_metrics import gate_metrics
from quality_insights import chart_evidence, chart_signal


class GateDisplayTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({'date':pd.to_datetime(['2026-01-10','2026-01-20','2026-02-10']),
                             'po_qty':[100,900,500],'defect_qty':[10,9,5]})

    def test_iqc_is_quantity_even_when_a_complete_denominator_exists(self):
        result,months=gate_metrics(self.frame(),'IQC')
        self.assertFalse(result['is_rate'])
        self.assertEqual(result['quantity'],24)
        self.assertTrue(np.isnan(result['rate']))
        self.assertEqual(months.defect_qty.tolist(),[19,5])

    def test_pqc_fqc_sum_numerators_and_denominators_not_mean_percentages(self):
        for stage in ['PQC','FQC']:
            result,months=gate_metrics(self.frame(),stage)
            self.assertTrue(result['is_rate'])
            self.assertAlmostEqual(result['rate'],24/1500)
            self.assertAlmostEqual(months.defect_rate.iloc[0],19/1000)

    def test_missing_denominator_cannot_be_count_or_partial_rate(self):
        frame=self.frame();frame.loc[0,'po_qty']=np.nan
        result,months=gate_metrics(frame,'FQC')
        self.assertTrue(np.isnan(result['rate']))
        self.assertTrue(np.isnan(months.defect_rate.iloc[0]))
        self.assertAlmostEqual(months.defect_rate.iloc[1],.01)
        self.assertEqual(result['quantity'],24)

    def test_missing_numerator_is_not_zero_defects(self):
        frame=self.frame();frame.loc[0,'defect_qty']=np.nan
        result,months=gate_metrics(frame,'PQC')
        self.assertTrue(np.isnan(result['rate']))
        self.assertTrue(np.isnan(result['quantity']))
        self.assertTrue(np.isnan(months.defect_qty.iloc[0]))

    def test_invalid_denominators_and_infinite_values_are_unavailable(self):
        for value in [0,-1,np.inf,'not a quantity']:
            frame=self.frame();frame['po_qty']=frame.po_qty.astype(object);frame.loc[0,'po_qty']=value
            result,_=gate_metrics(frame,'PQC')
            self.assertTrue(np.isnan(result['rate']))

    def test_missing_month_remains_a_line_gap(self):
        frame=self.frame();frame.loc[2,'date']=pd.Timestamp('2026-03-10')
        _,months=gate_metrics(frame,'PQC')
        self.assertEqual([str(m) for m in months.index],['2026-01','2026-02','2026-03'])
        self.assertTrue(np.isnan(months.defect_rate.iloc[1]))

    def test_empty_data_does_not_become_zero(self):
        for stage in ['IQC','PQC','FQC']:
            result,months=gate_metrics(pd.DataFrame(),'IQC')
            self.assertTrue(np.isnan(result['quantity']))
            self.assertTrue(np.isnan(result['rate']))
            self.assertTrue(months.empty)

    def test_pareto_has_three_visible_named_axes_and_full_population_shares(self):
        rows=pd.DataFrame({'cc':['a','b'],'score':[9,8],'share':[.3,.5666667]})
        fig=build_quality_pareto(rows,name_col='cc',qty_col='score',cumulative_col='share',
            quantity_label='风险分',cumulative_label='累计贡献占比（%）',x_label='CC 排名')
        self.assertEqual(fig.layout.xaxis.title.text,'CC 排名')
        self.assertEqual(fig.layout.yaxis.title.text,'风险分')
        self.assertEqual(fig.layout.yaxis2.title.text,'累计贡献占比（%）')
        self.assertEqual(list(fig.data[1].y),[.3,.5666667])

    def test_trend_axis_titles_and_formats_match_qty_and_rate(self):
        for rate,title,fmt in [(False,'数量（QTY）',',.0f'),(True,'疵点率（%）','.2%')]:
            fig=style_quality_trend(go.Figure(go.Scatter(x=['Jan','Feb'],y=[1,2],mode='lines')),
                height=245,is_rate=rate,monthly=True,x_label='月份',y_label=title)
            self.assertEqual(fig.layout.xaxis.title.text,'月份')
            self.assertEqual(fig.layout.yaxis.title.text,title)
            self.assertEqual(fig.layout.yaxis.tickformat,fmt)

    def test_gap_does_not_make_previous_observation_a_month_on_month_change(self):
        monthly=[{'month':'2026-01','numerator':2,'denominator':100},
                 {'month':'2026-02','numerator':3,'denominator':None},
                 {'month':'2026-03','numerator':1,'denominator':100},
                 {'month':'2026-04','numerator':3,'denominator':None}]
        traces=[{'type':'scatter','mode':'lines+markers','x':['2026-01-01','2026-02-01','2026-03-01','2026-04-01'],'y':[.02,None,.01,None]}]
        evidence=chart_evidence(traces,'.2%',{'kind':'trend','monthly':monthly})
        self.assertEqual(evidence['latest_volume']['month'],'2026-03')
        self.assertEqual(evidence['previous_volume']['month'],'2026-01')
        self.assertIsNone(evidence['change'])
        self.assertTrue(evidence['latest_period_missing'])
        self.assertEqual(chart_signal({'evidence':evidence})['tone'],'warning')


if __name__=='__main__':unittest.main()
