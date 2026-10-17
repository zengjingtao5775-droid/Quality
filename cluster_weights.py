"""Session policies for cluster views, isolated from dashboard/report scoring."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import math

import numpy as np
import pandas as pd

from tu_risk_poc import default_profile

CLUSTER_WEIGHTS_VERSION = "2026-10-17-v2-40-10-50"
STATE_KEY = "_quality_cluster_weights"
DEFAULTS = {
    "TU": {"client_weight": 40., "product_weight": 10., "supplier_weight": 50.,
           "return_weight": 50., "iv_weight": 50., "pqc_weight": 80., "aql_weight": 20.},
    "BME": {"fsd_fqc_weight": 50., "fsd_rpm_weight": 50.,
            "cmw_rate_weight": 60., "cmw_volume_weight": 40.},
}


def migrate_cluster_defaults(state):
    """Migrate the previous default without overwriting a custom policy."""
    if state.get("_quality_cluster_default_revision") == CLUSTER_WEIGHTS_VERSION:
        return
    previous = {**DEFAULTS["TU"], "client_weight": 30., "supplier_weight": 60.}
    policies = deepcopy(state.get(STATE_KEY, {}))
    if policies.get("TU") == previous:
        policies["TU"] = deepcopy(DEFAULTS["TU"])
        state[STATE_KEY] = policies
    state["_cluster_form_revision_TU"] = state.get("_cluster_form_revision_TU", 0) + 1
    state["_quality_cluster_default_revision"] = CLUSTER_WEIGHTS_VERSION


def validate_weights(community, values):
    if community not in DEFAULTS or set(values) != set(DEFAULTS[community]):
        raise ValueError("Unknown cluster policy")
    values = {key: float(value) for key, value in values.items()}
    groups = (("client_weight", "product_weight", "supplier_weight"),
              ("return_weight", "iv_weight"), ("pqc_weight", "aql_weight")) if community == "TU" else (
              ("fsd_fqc_weight", "fsd_rpm_weight"), ("cmw_rate_weight", "cmw_volume_weight"))
    for group in groups:
        weights = [values[key] for key in group]
        if any(not math.isfinite(value) or value < 0 for value in weights) or not math.isclose(sum(weights), 100.):
            raise ValueError("Each weight group must be non-negative and total 100%")
    return values


def current_weights(state, community):
    saved = state.get(STATE_KEY, {}).get(community, DEFAULTS[community])
    try:
        return validate_weights(community, saved)
    except (ValueError, TypeError, OverflowError):
        return deepcopy(DEFAULTS[community])


def apply_weights(state, community, values):
    # Validate before replacing an applied policy; widget cleanup cannot delete it.
    validated = validate_weights(community, values)
    policies = deepcopy(state.get(STATE_KEY, {}))
    policies[community] = validated
    state[STATE_KEY] = policies


def tu_cluster_profile(state):
    return replace(default_profile("Model"), **current_weights(state, "TU")).validate()


def _weighted_groups(points, scores, weights, *, single="Monitor"):
    """Weight standardized distance, so normalization cannot cancel the weights."""
    scale = points.std(axis=0)
    scale[scale == 0] = 1
    normalized = (points - points.mean(axis=0)) / scale * np.sqrt(weights)
    count = min(3, len(np.unique(normalized, axis=0)))
    order = np.argsort(normalized.sum(axis=1), kind="stable")
    centers = normalized[order[np.linspace(0, len(order)-1, count).round().astype(int)]].copy()
    labels = np.zeros(len(points), dtype=int)
    for _ in range(80):
        distances = ((normalized[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        next_labels = distances.argmin(axis=1)
        next_centers = centers.copy()
        for cluster_id in range(count):
            members = normalized[next_labels == cluster_id]
            next_centers[cluster_id] = members.mean(axis=0) if len(members) else normalized[distances.min(axis=1).argmax()]
        if np.array_equal(labels, next_labels) and np.allclose(centers, next_centers):
            labels = next_labels
            break
        labels, centers = next_labels, next_centers
    ranked = pd.DataFrame({"group": labels, "score": scores}).groupby("group").score.mean().sort_values(kind="stable").index.tolist()
    names = {1: [single], 2: ["Monitor", "Priority improvement"],
             3: ["Monitor", "Attention", "Priority improvement"]}[len(ranked)]
    mapping = dict(zip(ranked, names))
    return [mapping[label] for label in labels]


def fsd_cluster_view(baseline, weights):
    """Return a separate presentation frame; never mutate Pareto/report facts."""
    weights = validate_weights("BME", weights)
    view = baseline.copy(deep=True)
    if view.empty or weights["fsd_fqc_weight"] == 50.:
        return view
    valid = np.isfinite(view.rpm) & np.isfinite(view.defect_rate)
    matched = view.loc[valid]
    if matched.empty:
        return view
    def minmax(series):
        span = series.max() - series.min()
        return pd.Series(.5, index=series.index) if not span else (series-series.min())/span
    fqc = minmax(matched.defect_rate)
    rpm = minmax(np.log10(matched.rpm.clip(lower=1)))
    scores = (fqc*weights["fsd_fqc_weight"] + rpm*weights["fsd_rpm_weight"]).round(1)
    view.loc[valid, "priority_score"] = scores
    view.loc[valid, "cluster_label"] = _weighted_groups(
        np.column_stack([fqc, rpm]), scores.to_numpy(),
        [weights["fsd_fqc_weight"]/50, weights["fsd_rpm_weight"]/50], single="Priority improvement")
    return view


def cmw_cluster_view(baseline, weights):
    weights = validate_weights("BME", weights)
    view = baseline.copy(deep=True)
    if view.empty or weights["cmw_rate_weight"] == 60.:
        return view
    from bme_quality import _relative_percentile
    for _, rows in view.groupby("quality_gate", sort=True):
        has_rate = rows.defect_rate.notna()
        rate = _relative_percentile(rows.defect_rate)
        volume = _relative_percentile(rows.defect_qty)
        rate.loc[rows.defect_rate.le(0)] = 0
        volume.loc[rows.defect_qty.le(0)] = 0
        scores = (rate*weights["cmw_rate_weight"]/100 + volume*weights["cmw_volume_weight"]/100).where(has_rate, volume)
        view.loc[rows.index, "risk_score"] = scores.round(1)
        # Missing denominators retain volume-only scores and their existing groups.
        # A rate weight cannot create a missing measurement.
        if has_rate.all():
            view.loc[rows.index, "cluster_label"] = _weighted_groups(
                rows[["severity_axis", "exposure_axis"]].to_numpy(dtype=float), scores.to_numpy(),
                [weights["cmw_rate_weight"]/60, weights["cmw_volume_weight"]/40])
        view.loc[rows.index[has_rate], "score_basis"] = f'Rate percentile {weights["cmw_rate_weight"]:g}% + defect-volume percentile {weights["cmw_volume_weight"]:g}%'
    return view.sort_values(["risk_score", "defect_qty", "issue_records"], ascending=False).reset_index(drop=True)
