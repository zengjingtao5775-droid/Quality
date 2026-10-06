"""ZX source adapters for the shared IQC / PQC / FQC presentation schema."""
import numpy as np
import pandas as pd


SUMMARY_COLUMNS = ['date', 'supplier', 'stage', 'po_qty', 'defect_qty', 'rework_qty', 'rework_available']
PARETO_COLUMNS = ['date', 'supplier', 'stage', 'defect_name', 'defect_qty', 'category_type']


def _column(frame, name, default):
    return frame.get(name, pd.Series(default, index=frame.index))


def _dates(frame):
    dates = pd.to_datetime(_column(frame, 'date', pd.NaT), errors='coerce')
    return dates.dt.tz_localize(None)


def _description(row):
    names = []
    for key in ['gtd_issue', 'visual_issue', 'functional_issue', 'liner_issue', 'size_issue', 'important_issue']:
        value = row.get(key)
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text.lower() in ['', '0', '0.0', 'nan', 'none', 'n/a', '/', '-', '无', '无疵点', '无不良']:
            continue
        if text not in names:
            names.append(text)
    return '；'.join(names)


def build_zx_quality_gates(incoming, process, final):
    """Keep exception records, defect points and inspected units distinct.

    Inputs already carry their business scope. IQC has no complete denominator;
    mixed material units must never be added to create one. Composite source
    descriptions stay intact because counts per individual defect are unknown.
    """
    summaries, paretos = [], []
    for stage, source, quantity, description in [
        ('IQC', incoming, None, 'issue'),
        ('PQC', process, 'qty_inspected', 'defect_type'),
        ('FQC', final, 'sampling_size', None),
    ]:
        if source.empty:
            continue
        source = source.copy()
        if 'factory_code' in source:
            source = source[source['factory_code'].eq('ZX')]
        if stage == 'PQC' and 'inspection_stage' in source:
            source = source[source['inspection_stage'].isin(['Online QC', 'End QC / FQC'])]
        source = source.loc[_dates(source).notna()].copy()
        if source.empty:
            continue
        summary = pd.DataFrame(index=source.index)
        summary['date'] = _dates(source)
        summary['supplier'] = 'ZX'
        summary['stage'] = stage
        summary['po_qty'] = pd.to_numeric(_column(source, quantity, np.nan), errors='coerce') if quantity else np.nan
        summary['defect_qty'] = 1.0 if stage == 'IQC' else pd.to_numeric(_column(source, 'defect_qty', np.nan), errors='coerce')
        # No structured rework quantities exist in these inputs.
        summary['rework_qty'] = np.nan
        summary['rework_available'] = False
        summaries.append(summary)
        names = _column(source, description, '').fillna('').astype(str).str.strip() if description else source.apply(_description, axis=1)
        ranked = summary[['date', 'supplier', 'stage', 'defect_qty']].copy()
        ranked['defect_name'] = names
        ranked['category_type'] = 'defect'
        paretos.append(ranked[PARETO_COLUMNS])
    summary = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame(columns=SUMMARY_COLUMNS)
    pareto = pd.concat(paretos, ignore_index=True) if paretos else pd.DataFrame(columns=PARETO_COLUMNS)
    for frame in [summary, pareto]:
        frame['date'] = pd.to_datetime(frame['date'])
    return summary[SUMMARY_COLUMNS], pareto[PARETO_COLUMNS]
