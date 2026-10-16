"""Shared gate metric policy: IQC quantities, PQC/FQC weighted defect rates.

Inputs retain their source units/populations. No missing denominator or
numerator is imputed, and no count series substitutes for a requested rate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GATE_METRICS_VERSION = "2026-10-16-v2-weekly-gates"


def gate_metrics(frame: pd.DataFrame, stage: str, *, frequency: str = "M") -> tuple[dict, pd.DataFrame]:
    if stage not in {"IQC", "PQC", "FQC"}:
        raise ValueError("Unsupported inspection gate")
    if frequency not in {"M", "W-SUN"}:
        raise ValueError("Unsupported gate reporting frequency")
    frame = frame.copy()
    defects = pd.to_numeric(frame.get("defect_qty", pd.Series(np.nan, index=frame.index)), errors="coerce")
    inspected = pd.to_numeric(frame.get("po_qty", pd.Series(np.nan, index=frame.index)), errors="coerce")
    valid_qty = defects.ge(0) & np.isfinite(defects)
    valid_rate = valid_qty & inspected.gt(0) & np.isfinite(inspected)
    complete_qty = bool(len(frame) and valid_qty.all())
    complete_rate = bool(len(frame) and valid_rate.all())
    total = float(defects.sum()) if complete_qty else np.nan
    denominator = float(inspected.sum()) if complete_rate else np.nan
    rate = total / denominator if complete_rate else np.nan
    metrics = {"is_rate": stage != "IQC", "quantity": total, "denominator": denominator,
               "rate": rate if stage != "IQC" else np.nan,
               "complete_quantity": complete_qty, "complete_denominator": complete_rate,
               "rows": len(frame), "valid_rate_rows": int(valid_rate.sum())}
    if frame.empty:
        return metrics, pd.DataFrame(columns=["defect_qty", "po_qty", "defect_rate", "complete_denominator"])
    frame["_defects"], frame["_inspected"] = defects, inspected
    frame["_valid_qty"], frame["_valid_rate"] = valid_qty, valid_rate
    frame["period"] = pd.to_datetime(frame["date"]).dt.to_period(frequency)
    periods = frame.groupby("period").agg(
        defect_qty=("_defects", lambda values: values.sum(min_count=1)),
        po_qty=("_inspected", lambda values: values.sum(min_count=1)),
        complete_quantity=("_valid_qty", "all"),
        complete_denominator=("_valid_rate", "all"),
    )
    # Retain unmeasured periods as gaps. W-SUN is Monday through Sunday,
    # including ISO weeks that cross calendar years.
    if not periods.empty:
        periods = periods.reindex(pd.period_range(periods.index.min(), periods.index.max(), freq=frequency))
    periods.loc[~periods.complete_quantity.eq(True), "defect_qty"] = np.nan
    periods["defect_rate"] = periods.defect_qty / periods.po_qty.where(periods.complete_denominator.eq(True))
    return metrics, periods
