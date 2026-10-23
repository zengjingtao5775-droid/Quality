"""Single-CC drill-down for TU quality gates; global scores stay independent."""
from __future__ import annotations

from dataclasses import replace
import re

import pandas as pd

from dashboard_scope import filter_records, identifiers


FOCUS_KEY = "_tu_quality_focus_cc"
SCOPE_KEY = "_tu_quality_focus_scope"
REVISION_KEY = "_tu_quality_focus_revision"


def _cc(value):
    text = re.sub(r"\.0$", "", str(value or "").strip())
    return text if re.fullmatch(r"\d{6}", text) else ""


def clear_cluster_focus(state):
    state[FOCUS_KEY] = ""
    # Chart selection state is read-only. A new widget identity clears it.
    state[REVISION_KEY] = int(state.get(REVISION_KEY, 0)) + 1


def prepare_cluster_focus(state, scope, visible_ccs):
    """Expire a selection when the base scope or visible products change."""
    identity = scope.facts()
    allowed = {_cc(value) for value in visible_ccs} - {""}
    if state.get(SCOPE_KEY) != identity:
        clear_cluster_focus(state)
        state[SCOPE_KEY] = identity
    elif state.get(FOCUS_KEY) and state[FOCUS_KEY] not in allowed:
        clear_cluster_focus(state)
    return str(state.get(FOCUS_KEY, ""))


def sync_cluster_focus(state, chart_key, visible_ccs):
    """Use the exact CC carried by the selected point, never its plot index."""
    event = state.get(chart_key, {})
    selection = event.get("selection", {}) if isinstance(event, dict) else {}
    points = selection.get("points", []) if isinstance(selection, dict) else []
    if not points:
        state[FOCUS_KEY] = ""
        return
    custom = points[-1].get("customdata", [])
    if not isinstance(custom, (list, tuple)) or len(custom) < 2:
        return
    selected_cc = _cc(custom[1])
    allowed = {_cc(value) for value in visible_ccs} - {""}
    if selected_cc and selected_cc in allowed:
        state[FOCUS_KEY] = selected_cc


def select_quality_gate_sources(incoming, process, final, scope, focused_cc=""):
    """Filter each gate before aggregation; missing links never mean zero NC."""
    chosen = _cc(focused_cc)
    gate_scope = replace(scope, ccs=(chosen,)) if chosen else scope
    selected, unavailable = {}, {}
    for stage, frame in (("IQC", incoming), ("PQC", process), ("FQC", final)):
        cc_col = "product_code" if "product_code" in frame else "cc"
        model_col = "model_code" if "model_code" in frame else "model"
        codes = identifiers(frame.get(cc_col, pd.Series("", index=frame.index)))
        models = identifiers(frame.get(model_col, pd.Series("", index=frame.index)))
        # An empty already-filtered frame still retains its source schema.
        missing_cc_link = bool(gate_scope.ccs) and (cc_col not in frame or (len(frame) > 0 and not codes.ne("").any()))
        missing_model_link = bool(gate_scope.models) and (model_col not in frame or (len(frame) > 0 and not models.ne("").any()))
        if missing_cc_link or missing_model_link:
            unavailable[stage] = "CC" if missing_cc_link else "Model"
            selected[stage] = frame.iloc[:0].copy()
        else:
            selected[stage] = filter_records(frame, gate_scope, supplier="ZX", cc_col=cc_col, model_col=model_col)
    return gate_scope, selected, unavailable
