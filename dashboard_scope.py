"""Shared, auditable selection rules for the TU and BME dashboards.

Empty product/supplier selections mean all values in the selected community.
Unknown links never fall back to a factory total. Customer exports are fixed
N0 snapshots, separate from dated inspection and IV records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

LOGIC_VERSION = "2026-10-06-v2-net-sales"


@dataclass(frozen=True)
class DashboardScope:
    communities: tuple[str, ...] = ("TU",)
    suppliers: tuple[str, ...] = ()
    ccs: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    stages: tuple[str, ...] = ()
    owners: tuple[str, ...] = ()
    period: str = "R12M"
    start: object | None = None
    end: object | None = None

    @property
    def product_filtered(self) -> bool:
        return bool(self.ccs or self.models)

    def includes_supplier(self, supplier: str) -> bool:
        return not self.suppliers or supplier in self.suppliers

    def facts(self) -> dict:
        return {
            "communities": list(self.communities), "suppliers": list(self.suppliers),
            "ccs": list(self.ccs), "models": list(self.models),
            "stages": list(self.stages), "owners": list(self.owners),
            "period": self.period, "start": str(self.start), "end": str(self.end),
        }


def identifiers(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.strip().str.replace(r"\.0$", "", regex=True).replace({"nan": "", "None": ""})


def business_dates(values: pd.Series) -> pd.Series:
    """Retain the inspection's local business day when removing timezone data."""
    dates = pd.to_datetime(values, errors="coerce", format="mixed")
    if isinstance(dates.dtype, pd.DatetimeTZDtype):
        return dates.dt.tz_localize(None)
    if pd.api.types.is_datetime64_any_dtype(dates):
        return dates
    return pd.to_datetime(dates.map(lambda value: pd.Timestamp(value).tz_localize(None) if pd.notna(value) else pd.NaT))


def filter_records(
    frame: pd.DataFrame,
    scope: DashboardScope,
    *,
    supplier: str | None = None,
    supplier_col: str = "supplier",
    cc_col: str = "product_code",
    model_col: str = "model_code",
    date_col: str | None = "date",
    item_models: dict[str, frozenset[str]] | None = None,
) -> pd.DataFrame:
    """AND between dimensions, OR within each multi-selection; exact IDs only."""
    if frame.empty:
        return frame.copy()
    keep = pd.Series(True, index=frame.index)
    if scope.suppliers:
        if supplier is not None:
            keep &= supplier in scope.suppliers
        elif supplier_col in frame:
            keep &= identifiers(frame[supplier_col]).isin(scope.suppliers)
        else:
            keep &= False
    codes = identifiers(frame.get(cc_col, pd.Series("", index=frame.index)))
    models = identifiers(frame.get(model_col, pd.Series("", index=frame.index)))
    if scope.ccs:
        keep &= codes.isin(scope.ccs)
    if scope.models:
        matched = models.isin(scope.models)
        if item_models is not None:
            chosen = set(scope.models)
            matched |= codes.map(lambda code: bool(chosen.intersection(item_models.get(code, ()))))
        keep &= matched
    if date_col and scope.start is not None and scope.end is not None:
        if date_col not in frame:
            keep &= False
        else:
            dates = business_dates(frame[date_col])
            # Include the entire final day, including timestamped measurements.
            keep &= dates.ge(pd.Timestamp(scope.start)) & dates.lt(pd.Timestamp(scope.end).normalize() + pd.Timedelta(days=1))
    return frame.loc[keep].copy()


def customer_totals(frame: pd.DataFrame) -> dict[str, float | None]:
    """Recompute RPM from quantities; do not average RPM or add CC and Model."""
    result: dict[str, float | None] = {}
    for suffix in ("now", "prev"):
        returned = pd.to_numeric(frame.get(f"returned_{suffix}", pd.Series(dtype=float)), errors="coerce")
        sold = pd.to_numeric(frame.get(f"sold_{suffix}", pd.Series(dtype=float)), errors="coerce")
        # The source's RPM sales field is net sales and can contain signed
        # adjustments by model. Retain them in SUM; only the final denominator
        # must be positive. Missing quantities remain different from zero.
        valid = returned.ge(0) & sold.notna()
        # A missing numerator must not silently turn into zero returns.
        complete = len(frame) > 0 and bool(valid.all())
        total_sold = float(sold.loc[valid].sum()) if complete else None
        total_returned = float(returned.loc[valid].sum()) if complete else None
        result[f"sold_{suffix}"] = total_sold
        result[f"returned_{suffix}"] = total_returned
        result[f"rpm_{suffix}"] = total_returned / total_sold * 1_000_000 if total_sold is not None and total_sold > 0 else None
        nqc = pd.to_numeric(frame.get(f"nqc_{suffix}", pd.Series(dtype=float)), errors="coerce")
        result[f"nqc_{suffix}"] = float(nqc.sum()) if len(frame) > 0 and len(nqc) == len(frame) and nqc.notna().all() else None
    return result


def select_customer_grain(voice: pd.DataFrame, scope: DashboardScope) -> pd.DataFrame:
    grain = "Model" if scope.models else "CC"
    selected = voice.loc[voice.get("customer_grain", pd.Series("", index=voice.index)).eq(grain)].copy()
    return filter_records(selected, scope, supplier="ZX", date_col=None)


def count_iv_cases(cases: pd.DataFrame, scope: DashboardScope) -> int | None:
    if cases.empty:
        return None  # no connected case source; different from zero matches
    selected = filter_records(cases, scope, supplier="ZX")
    before = selected.get("responsibility_stage", pd.Series("", index=selected.index)).fillna("").astype(str).str.casefold().str.startswith("before")
    return int(selected.loc[before, "case_id"].nunique())


def fsd_item_model_links(mapping: pd.DataFrame, rpm_codes: Iterable[str]) -> dict[str, frozenset[str]]:
    """Reuse the cluster's exact raw-frame/raw-fork master-data relationship."""
    codes = set(rpm_codes)
    bikes = mapping.loc[mapping["record_type"].astype(str).str.strip().str.casefold().eq("bike") & mapping["model_code"].isin(codes)]
    frames: dict[str, set[str]] = {}
    forks: dict[str, set[str]] = {}
    for row in bikes.itertuples(index=False):
        if row.raw_frame_key:
            frames.setdefault(row.raw_frame_key, set()).add(row.model_code)
        if row.raw_fork_key:
            forks.setdefault(row.raw_fork_key, set()).add(row.model_code)
    links: dict[str, frozenset[str]] = {}
    for code, rows in mapping.loc[mapping["item_code"].ne("")].groupby("item_code"):
        models: set[str] = set()
        for row in rows.itertuples(index=False):
            if row.model_code in codes:
                models.add(row.model_code)
            models.update(frames.get(row.raw_frame_key, ()))
            models.update(forks.get(row.raw_fork_key, ()))
        links[str(code)] = frozenset(models)
    return links


def select_fsd_customer(rpm: pd.DataFrame, scope: DashboardScope, links: dict[str, frozenset[str]]) -> pd.DataFrame:
    if not scope.includes_supplier("FSD"):
        return rpm.iloc[0:0].copy()
    # The customer workbook includes bikes from several vendors. Restrict the
    # default universe to models auditable through the FSD master, counted once.
    codes = set().union(*links.values()) if links else set()
    if scope.ccs:
        codes &= set().union(*(links.get(code, frozenset()) for code in scope.ccs))
    if scope.models:
        codes &= set(scope.models)
    return rpm.loc[identifiers(rpm["product_code"]).isin(codes)].drop_duplicates("product_code").copy()


def ranked_cc_risk(frame: pd.DataFrame, code_col: str, score_col: str, top_only: bool = True) -> tuple[pd.DataFrame, dict]:
    """Rank the existing cluster scores; never rescale them for a Pareto view."""
    if frame.empty:
        return pd.DataFrame(columns=["cc", "risk_score"]), {"total": 0, "selected": 0, "share": None}
    result = pd.DataFrame({"cc": identifiers(frame[code_col]), "risk_score": pd.to_numeric(frame[score_col], errors="coerce")})
    result = result.loc[result["cc"].ne("") & result["risk_score"].notna()].sort_values(["risk_score", "cc"], ascending=[False, True]).reset_index(drop=True)
    total = len(result)
    count = max(1, int(np.ceil(total * 0.2))) if total else 0
    selected = result.head(count) if top_only else result
    denominator = result["risk_score"].sum()
    return selected, {"total": total, "selected": len(selected), "share": float(selected["risk_score"].sum() / denominator) if denominator > 0 else None}
