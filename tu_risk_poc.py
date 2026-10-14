"""Textile three-dimension risk POC; source facts and trial policy are separate.

Client = RPM/IV. Product = confirmed Strategy identity. Supplier = PQC/AQL.
Unknown weighted inputs stay unknown: show the known contribution and a bound,
never silently allocate their weight to another input. Scores are priorities,
not defect probabilities. The defaults are proposals, not calibrated standards.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd

from dashboard_scope import DashboardScope, filter_records, identifiers, customer_totals

RISK_POC_VERSION = "2026-10-13-v1-three-dimensions"
DEPARTMENTS = ("Hugss", "Knit", "Woven")
GRAINS = ("Model", "CC", "Supplier")


@dataclass(frozen=True)
class RiskProfile:
    client_weight: float = 30
    product_weight: float = 10
    supplier_weight: float = 60
    rpm_weight: float = 50
    iv_weight: float = 50
    pqc_weight: float = 80
    aql_weight: float = 20
    pqc_warning_pct: float = 4
    pqc_critical_pct: float = 8
    pqc_prior_defects: float = 8
    pqc_prior_samples: float = 200
    aql_warning_pct: float = 10
    aql_critical_pct: float = 20
    rpm_warning: float = 646
    rpm_critical: float = 1292
    iv_warning: float = 5
    iv_critical: float = 10

    def validate(self):
        for weights in ((self.client_weight, self.product_weight, self.supplier_weight),
                        (self.rpm_weight, self.iv_weight), (self.pqc_weight, self.aql_weight)):
            if any(not math.isfinite(v) or v < 0 for v in weights) or not math.isclose(sum(weights), 100):
                raise ValueError("Each weight group must contain non-negative values summing to 100%")
        for warning, critical in ((self.pqc_warning_pct, self.pqc_critical_pct),
                                  (self.aql_warning_pct, self.aql_critical_pct),
                                  (self.rpm_warning, self.rpm_critical), (self.iv_warning, self.iv_critical)):
            if not (math.isfinite(warning) and math.isfinite(critical) and 0 < warning < critical):
                raise ValueError("Every warning threshold must be positive and below its critical threshold")
        if not (math.isfinite(self.pqc_prior_samples) and math.isfinite(self.pqc_prior_defects)
                and self.pqc_prior_samples >= 0 and self.pqc_prior_defects >= 0):
            raise ValueError("PQC smoothing inputs must be finite and non-negative")
        return self


def default_profile(grain="Model"):
    if grain not in GRAINS:
        raise ValueError("Unsupported risk grain")
    # Strategy is a product characteristic, not a whole-supplier attribute.
    return replace(RiskProfile(), product_weight=0, supplier_weight=70) if grain == "Supplier" else RiskProfile()


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def threshold_score(value, warning, critical):
    value = number(value)
    if value is None or value < 0:
        return None
    if not 0 < warning < critical:
        raise ValueError("Invalid scoring thresholds")
    return min(100., 50 * value / warning if value <= warning else 50 + 50 * (value-warning)/(critical-warning))


def weighted_bounds(parts):
    """Combine (score/None, percent weight); zero-weight missing parts are valid."""
    known = coverage = 0.
    for score, weight in parts:
        if weight == 0:
            continue
        score = number(score)
        if score is not None:
            known += min(100., max(0., score)) * weight / 100
            coverage += weight
    missing = max(0., 100.-coverage)
    return {"score": known if math.isclose(missing, 0) else None,
            "lower": known, "upper": min(100., known+missing), "coverage": coverage}


def identifier(value, digits):
    text = "" if value is None or pd.isna(value) else str(value).strip()
    text = re.sub(r"\.0$", "", text)
    return text if re.fullmatch(r"\d{"+str(digits)+r"}", text) else ""


def id_tokens(value, digits):
    """Only a numeric ID or an explicit separator-delimited ID list is usable."""
    if value is None or pd.isna(value):
        return frozenset()
    pieces = re.split(r"[,;/|\s、，；]+", str(value).strip())
    codes = [identifier(piece, digits) for piece in pieces if piece]
    return frozenset(codes) if codes and all(codes) else frozenset()


def load_strategy_workbook(path):
    """Read only the formal follow-up input sheet, not archives or formula tabs.

    The user's supplied follow-up is partial; missing matches cannot mean No.
    PE move, planned milestones, sport and development codes do not add risk.
    Preserve row-level ID sets without inventing CC/Model Cartesian links.
    """
    from openpyxl import load_workbook
    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        sheet = workbook["Strategic FG homologation"]
        header = next(sheet.iter_rows(min_row=3, max_row=3, values_only=True))
        if not all(term in str(header[index]).casefold() for index, term in
                   ((8, "supplier"), (11, "conception"), (12, "model"), (14, "season"))):
            raise ValueError("Strategic workbook schema changed")
        records = []
        for row_num, row in enumerate(sheet.iter_rows(min_row=4, values_only=True), 4):
            models, ccs = id_tokens(row[12], 7), id_tokens(row[11], 6)
            if not models and not ccs:
                continue
            supplier = re.match(r"^\s*(\d{5,6})(?:\s*-|\s*$)", str(row[8] or ""))
            records.append({"models": sorted(models), "ccs": sorted(ccs),
                            "supplier_code": supplier.group(1) if supplier else "",
                            "season": str(row[14] or "").strip().upper(),
                            "strategic": True, "source_row": row_num,
                            "source": "Strategic FG homologation"})
        return records
    finally:
        workbook.close()


def strategic_identity(models, cc, registry, supplier_code="49425", season=""):
    models = set(models) - {""}
    if not models:
        return {"status": "pending", "score": None, "matched_models": 0, "model_count": 0,
                "reason": "No verified Model identity", "source_rows": []}
    statuses, rows = [], []
    for model in sorted(models):
        exact = [record for record in registry
                 if model in record.get("models", ())
                 and record.get("supplier_code") == supplier_code
                 and season and str(record.get("season", "")).upper() == season.upper()]
        flags = {record.get("strategic") for record in exact if isinstance(record.get("strategic"), bool)}
        statuses.append(next(iter(flags)) if len(flags) == 1 else None)
        rows.extend(record.get("source_row") for record in exact)
    known = sum(status is not None for status in statuses)
    # A CC score requires all contributing Model identities. One confirmed Yes
    # cannot erase unresolved models or act as a supplier-wide label.
    if known == len(statuses):
        return {"status": "yes" if any(statuses) else "no", "score": 100. if any(statuses) else 0.,
                "matched_models": known, "model_count": len(models), "reason": "All Models confirmed; CC uses highest Strategy priority",
                "source_rows": sorted(set(row for row in rows if row is not None))}
    candidates = any(model in rec.get("models", ()) or (cc and cc in rec.get("ccs", ()))
                     for rec in registry for model in models)
    return {"status": "candidate" if candidates else "pending", "score": None,
            "matched_models": known, "model_count": len(models), "reason": "Partial follow-up; exact supplier/Model/season confirmation required",
            "source_rows": sorted(set(row for row in rows if row is not None))}


def normalize_source(frame, kind):
    result = frame.copy()
    cc = result.get("product_code", result.get("cc", pd.Series("", index=result.index)))
    model = result.get("model_code", result.get("model", pd.Series("", index=result.index)))
    if kind == "pqc":
        fallback = result.get("product_label", pd.Series("", index=result.index)).fillna("").astype(str).str.extract(r"^(\d{7})(?!\d)", expand=False)
        model = model.where(model.fillna("").astype(str).str.strip().ne(""), fallback)
    result["cc"] = cc.map(lambda value: identifier(value, 6))
    result["model"] = model.map(lambda value: identifier(value, 7))
    # This adapter is deliberately ZX/Hugss-only. More factories require an
    # authoritative department and supplier mapping, not process-name guesses.
    result["supplier_code"] = "49425"
    return result


def pqc_facts(frame, profile):
    d = pd.to_numeric(frame.get("defect_qty", pd.Series(dtype=float)), errors="coerce")
    n = pd.to_numeric(frame.get("qty_inspected", pd.Series(dtype=float)), errors="coerce")
    valid = d.ge(0) & n.gt(0) & np.isfinite(d) & np.isfinite(n)
    complete = len(frame) > 0 and bool(valid.all())
    defects, inspected = float(d[valid].sum()), float(n[valid].sum())
    smoothed = ((defects + profile.pqc_prior_defects) / (inspected + profile.pqc_prior_samples)) if complete else None
    return {"pqc_defects": defects, "pqc_inspected": inspected, "pqc_rows": len(frame),
            "pqc_valid_rows": int(valid.sum()), "pqc_dpu": defects/inspected if complete else None,
            "pqc_smoothed": smoothed, "pqc_score": threshold_score(smoothed*100, profile.pqc_warning_pct, profile.pqc_critical_pct) if smoothed is not None else None}


def aql_facts(frame, profile):
    frame = frame.copy()
    # Ignore exact duplicate export records; conflicting copies of a record ID
    # make its first-result status unresolved, not another independent check.
    if "record_id" in frame:
        frame["_id"] = identifiers(frame.record_id)
        frame.loc[frame._id.eq(""), "_id"] = [f"missing-{i}" for i in frame.index[frame._id.eq("")]]
    else:
        frame["_id"] = [f"row-{i}" for i in range(len(frame))]
    text = frame.get("result_raw", frame.get("result", pd.Series("", index=frame.index))).fillna("").astype(str)
    failed = text.str.contains(r"FAIL|NG|NOK|不合格|拒|RE-CHECK|RECHECK|重验", case=False, regex=True)
    passed = text.str.contains(r"PASS|合格", case=False, regex=True) & ~failed
    frame["_status"] = np.where(failed, "fail", np.where(passed, "pass", "unknown"))
    states = frame.groupby("_id")["_status"].agg(lambda values: next(iter(set(values))) if len(set(values)) == 1 else "unknown")
    total, valid, fail = len(states), int(states.ne("unknown").sum()), int(states.eq("fail").sum())
    rate = fail/valid if total and valid == total else None
    return {"aql_records": total, "aql_valid_records": valid, "aql_fail": fail,
            "aql_fail_rate": rate, "aql_score": threshold_score(rate*100, profile.aql_warning_pct, profile.aql_critical_pct) if rate is not None else None}


def score_entity(pqc, aql, customer, cases, profile, strategy, *, iv_available=True, rpm_available=True):
    profile.validate()
    facts = {**pqc_facts(pqc, profile), **aql_facts(aql, profile)}
    # Exact duplicates are harmless. Conflicting duplicate rows at one selected
    # customer grain are not additional sales and cannot be averaged.
    cust = customer.drop_duplicates()
    duplicate = bool(cust.duplicated(["supplier_code", "model" if cust.get("customer_grain", pd.Series(dtype=str)).eq("Model").all() else "cc"]).any()) if not cust.empty else False
    totals = customer_totals(cust) if rpm_available and not duplicate else {}
    rpm = totals.get("rpm_now")
    ids = identifiers(cases.get("case_id", pd.Series(dtype=str)))
    iv = int(ids[ids.ne("")].nunique()) if iv_available else None
    rpm_score = threshold_score(rpm, profile.rpm_warning, profile.rpm_critical)
    iv_score = threshold_score(iv, profile.iv_warning, profile.iv_critical)
    client = weighted_bounds(((rpm_score, profile.rpm_weight), (iv_score, profile.iv_weight)))
    supplier = weighted_bounds(((facts["pqc_score"], profile.pqc_weight), (facts["aql_score"], profile.aql_weight)))
    product_score = strategy["score"]
    # Propagate uncertainty through nested weights, rather than discarding a
    # partly measured dimension's known contribution.
    lower = client["lower"]*profile.client_weight/100 + (product_score or 0)*profile.product_weight/100 + supplier["lower"]*profile.supplier_weight/100
    upper = client["upper"]*profile.client_weight/100 + (100 if product_score is None else product_score)*profile.product_weight/100 + supplier["upper"]*profile.supplier_weight/100
    coverage = client["coverage"]*profile.client_weight/100 + (0 if product_score is None else profile.product_weight) + supplier["coverage"]*profile.supplier_weight/100
    facts.update({"rpm": rpm, "returns": totals.get("returned_now"), "sales": totals.get("sold_now"), "iv": iv,
                  "rpm_score": rpm_score, "iv_score": iv_score, "client_score": client["score"],
                  "product_score": product_score, "supplier_score": supplier["score"],
                  "client_contribution": client["lower"]*profile.client_weight/100,
                  "product_contribution": product_score*profile.product_weight/100 if product_score is not None else 0. if profile.product_weight == 0 else None,
                  "supplier_contribution": supplier["lower"]*profile.supplier_weight/100,
                  "risk_score": lower if math.isclose(lower, upper) else None,
                  "risk_lower": lower, "risk_upper": upper, "known_weight": coverage,
                  "strategy_status": strategy["status"], "strategy_reason": strategy["reason"],
                  "strategy_models_matched": strategy["matched_models"], "strategy_models_total": strategy["model_count"],
                  "strategy_source_rows": strategy["source_rows"], "complete": math.isclose(lower, upper)})
    return facts


def build_tu_risk(pqc, aql, voice, iv_cases, scope: DashboardScope, *, grain="Model", department="Hugss",
                  profile=None, registry=(), season="", inspection_only=True):
    """One recomputed score per supplier+grain; no duplicated CC/Model exports."""
    if grain not in GRAINS or department not in DEPARTMENTS:
        raise ValueError("Unsupported TU scope")
    profile = (profile or default_profile(grain)).validate()
    if grain == "Supplier" and profile.product_weight != 0:
        raise ValueError("Supplier grain cannot include product Strategy weight")
    if department != "Hugss" or not scope.includes_supplier("ZX"):
        return pd.DataFrame(), {"department": department, "status": "source_unavailable", "grain": grain}
    p = filter_records(normalize_source(pqc, "pqc"), scope, supplier="ZX", cc_col="cc", model_col="model")
    a = filter_records(normalize_source(aql, "aql"), scope, supplier="ZX", cc_col="cc", model_col="model")
    vgrain = "Model" if grain == "Model" or scope.models else "CC"
    v = voice.loc[voice.get("customer_grain", pd.Series("", index=voice.index)).eq(vgrain)].copy()
    v = filter_records(normalize_source(v, "customer"), scope, supplier="ZX", cc_col="cc", model_col="model", date_col=None)
    iv_available = not iv_cases.empty and {"case_id", "date", "responsibility_stage"}.issubset(iv_cases.columns)
    i = normalize_source(filter_records(iv_cases, scope, supplier="ZX"), "iv")
    before = i.get("responsibility_stage", pd.Series("", index=i.index)).fillna("").astype(str).str.casefold().str.startswith("before")
    i = i.loc[before].copy()
    # Unassigned IDs are never distributed over all Models/CCs.
    key = {"Model": "model", "CC": "cc", "Supplier": "supplier_code"}[grain]
    sources = [p, a] if inspection_only else [p, a, v, i]
    universe = sorted({str(value) for frame in sources for value in frame[key] if value})
    rows = []
    for value in universe:
        groups = [frame.loc[frame[key].eq(value)] for frame in (p, a, v, i)]
        models = sorted({model for frame in groups for model in frame.model if model})
        ccs = sorted({cc for frame in groups for cc in frame.cc if cc})
        cc = value if grain == "CC" else ccs[0] if len(ccs) == 1 else ""
        strategy = strategic_identity(models, cc, registry, season=season)
        if grain == "Supplier":
            strategy = {"status": "not_applicable", "score": None, "reason": "Strategy belongs to products", "matched_models": 0, "model_count": len(models), "source_rows": []}
        scored = score_entity(*groups, profile, strategy, iv_available=iv_available, rpm_available=scope.period != "Custom")
        defect = groups[0].groupby("defect_type")["defect_qty"].sum().sort_values(ascending=False) if "defect_type" in groups[0] and not groups[0].empty else pd.Series(dtype=float)
        rows.append({"entity": value, "grain": grain, "department": department, "supplier_code": "49425", "supplier": "中兴",
                     "cc": cc, "models": " / ".join(models), "top_defect": str(defect.index[0]) if len(defect) else "", **scored})
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["risk_lower", "entity"], ascending=[False, True]).reset_index(drop=True)
    return result, {"version": RISK_POC_VERSION, "department": department, "supplier_code": "49425", "grain": grain,
                    "entities": len(result), "pqc_rows": len(p), "aql_rows": len(a),
                    "pqc_unmapped_rows": int(p[key].eq("").sum()), "aql_unmapped_rows": int(a[key].eq("").sum()),
                    "iv_available": iv_available, "customer_period": "N0 snapshot; no calendar dates",
                    "strategy_source": "Partial follow-up; unmatched = pending", "season": season,
                    "profile": profile.__dict__, "ranking": "known weighted contribution; incomplete bounds do not prove total-risk ordering"}
