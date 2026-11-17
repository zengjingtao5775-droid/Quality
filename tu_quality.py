"""ZX source adapters for the shared IQC / PQC / FQC presentation schema."""
from zipfile import BadZipFile

import numpy as np
import pandas as pd

from quality_gate_metrics import gate_metrics


SUMMARY_COLUMNS = ['date', 'supplier', 'stage', 'po_qty', 'defect_qty', 'rework_qty', 'rework_available']
PARETO_COLUMNS = ['date', 'supplier', 'stage', 'defect_name', 'defect_qty', 'category_type']
IQC_INSPECTION_SHEET = 'IQC检验明细'
IQC_INSPECTION_FIELDS = {
    '检验日期': 'date',
    '检验数量': 'po_qty',
    '疵点数量': 'defect_qty',
    '单位': 'unit',
}


def _column(frame, name, default):
    return frame.get(name, pd.Series(default, index=frame.index))


def _dates(frame):
    dates = pd.to_datetime(_column(frame, 'date', pd.NaT), errors='coerce')
    return dates.dt.tz_localize(None)


def load_zx_iqc_inspections(path):
    """Read the complete IQC log, including inspections with zero defects."""
    fields = list(IQC_INSPECTION_FIELDS.values())
    try:
        with pd.ExcelFile(path, engine='openpyxl') as workbook:
            if IQC_INSPECTION_SHEET not in workbook.sheet_names:
                return pd.DataFrame(columns=fields)
            frame = workbook.parse(IQC_INSPECTION_SHEET).dropna(how='all')
    except (OSError, ValueError, BadZipFile):
        return pd.DataFrame(columns=fields)
    frame = frame.rename(columns=IQC_INSPECTION_FIELDS).reindex(columns=fields)
    frame['date'] = _dates(frame)
    if frame['date'].isna().any():
        # An unassigned inspection could belong to any week.
        return pd.DataFrame(columns=fields)
    return frame


def zx_iqc_weekly_rates(inspections, start_date, end_date):
    """Calculate weighted weekly defect rates from comparable inspection quantities."""
    frame = inspections
    if not frame.empty:
        frame = frame.loc[frame['date'].dt.date.between(start_date, end_date)]
    _, periods = gate_metrics(frame, 'IQC', frequency='W-SUN')
    if periods.empty:
        return periods
    units = frame['unit'].astype('string').fillna('').str.strip().str.casefold()
    known_units = units.loc[units.ne('')].unique()
    unknown_unit = frame['date'].dt.to_period('W-SUN').loc[units.eq('')]
    invalid = periods.index.isin(unknown_unit) | (len(known_units) != 1)
    periods.loc[invalid, 'complete_denominator'] = False
    periods.loc[invalid, 'defect_rate'] = np.nan
    return periods


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
