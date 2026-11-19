"""Compact source-backed TU Risk POC embedded in the shared dashboard."""
from __future__ import annotations

from pathlib import Path
import html
import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tu_risk_poc import default_profile, build_tu_risk, load_strategy_workbook, number
from quality_chart_ui import apply_quality_chart_style
from cluster_weights import (DEFAULT_RISK_LEVEL_THRESHOLDS, current_risk_level_thresholds,
                             tu_cluster_profile, validate_risk_level_thresholds)
from tu_risk_reference import render_tu_scoring_reference
from tu_cluster_selection import (REVISION_KEY, prepare_cluster_focus,
                                 sync_cluster_focus)

RISK_POC_UI_VERSION = "2026-11-19-v12-axis-label-spacing"
RISK_GROUP_COLORS = {"high": "#e85d68", "medium": "#f0a94a", "low": "#2aa876"}
RISK_GROUP_LABELS = {"high": ("高风险", "High risk"), "medium": ("中风险", "Medium risk"),
                     "low": ("低风险", "Low risk")}

CSS = """
.st-key-tu_three_dimension_risk{background:#fff!important;border:1px solid #dce4f4!important;border-top:5px solid #2854c5!important;border-radius:14px!important;padding:12px 16px!important;gap:8px!important}
.st-key-tu_three_dimension_risk [data-testid="stVerticalBlock"]{gap:10px!important}
.tu-poc-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 6px}
.tu-poc-head h2{font-size:25px!important;margin:0!important;padding:0!important;color:#192e54}
.tu-poc-head span{background:#edf2ff;color:#294dc0;padding:5px 10px;border-radius:8px;font-size:15px;font-weight:700}
.tu-poc-formula{background:#edf2ff;padding:10px 16px;border-radius:10px;font-size:17px;line-height:1.65;color:#1b3575;margin:0}
.tu-poc-status{display:flex;gap:12px;flex-wrap:wrap;padding:6px 0;color:#475569;font-size:16px;line-height:1.5}
.tu-poc-status b{color:#9a3412}
.tu-poc-table-wrap{overflow:auto;border:1px solid #e0e7f3;border-radius:10px}
.tu-poc-table{border-collapse:collapse;width:100%;min-width:860px;font-size:16px;line-height:1.3;table-layout:fixed;margin:0!important}
.tu-poc-table th{background:#f4f6fc;color:#475569;padding:7px 10px;text-align:left;white-space:nowrap}
.tu-poc-table td{border-top:1px solid #e8edf6;padding:5px 10px;vertical-align:middle;overflow-wrap:anywhere}
.tu-poc-cc{margin-left:8px;color:#64748b;white-space:nowrap}
.tu-poc-table td strong{color:#234ebc}.tu-poc-table .pending{color:#9a3412;background:#fff7ed;border-radius:5px;padding:2px 5px;font-size:15px}
.tu-poc-table .confirmed{color:#047857;background:#ecfdf5;padding:2px 5px;border-radius:5px;font-size:15px}
.tu-poc-table details summary{cursor:pointer;color:#284dc0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tu-poc-table details{display:inline-block;vertical-align:middle;max-width:140px;margin-left:8px}
.tu-poc-table details[open]{display:block;max-width:none;margin:4px 0}
.tu-poc-table details[open] summary{white-space:normal}
.tu-poc-table tr:first-child td{background:#f8faff}
.tu-poc-source{font-size:16px;line-height:1.65;color:#475569;background:#f8faff;padding:12px 16px;border-radius:9px}
.tu-poc-chart-note{font-size:16px;line-height:1.55;color:#475569;margin:4px 0}
"""


def risk_distribution_groups(rows, thresholds=DEFAULT_RISK_LEVEL_THRESHOLDS):
    """Assign each plotted Model a level from its existing score lower bound."""
    medium, high = validate_risk_level_thresholds(thresholds)
    view = rows.copy()
    for column in ("supplier_score", "client_score", "risk_lower"):
        view[column] = pd.to_numeric(view.get(column, pd.Series(index=view.index, dtype=float)), errors="coerce")
    if "entity" not in view:
        view["entity"] = pd.Series(index=view.index, dtype=str)
    valid = np.isfinite(view.supplier_score) & np.isfinite(view.client_score) & np.isfinite(view.risk_lower)
    view = view.loc[valid].sort_values("entity", kind="stable").copy()
    view["risk_group"] = np.select(
        [view.risk_lower.ge(high), view.risk_lower.ge(medium)],
        ["high", "medium"],
        default="low",
    )
    return view


def build_risk_distribution_figure(grouped, grain, translate=None, selected_groups=None, focused_cc=""):
    """Use exact scored coordinates; colors/labels never feed back into scoring."""
    t = translate or (lambda zh, en: zh)
    view = grouped if selected_groups is None else grouped.loc[grouped.risk_group.isin(selected_groups)]
    fig = go.Figure()
    for key, names in RISK_GROUP_LABELS.items():
        label = t(*names)
        part = view.loc[view.risk_group.eq(key)].sort_values("risk_lower", ascending=False, kind="stable")
        if part.empty:
            continue
        custom = []
        for _, row in part.iterrows():
            upper = number(row.get("risk_upper"))
            lower = number(row.get("risk_lower"))
            score = f"{lower:.1f}–{upper:.1f}" if lower is not None and upper is not None else "—"
            custom.append([html.escape(str(row.get("entity", ""))), html.escape(str(row.get("cc", ""))),
                html.escape(str(row.get("models", ""))), score, _fmt(row.get("strategy_indicator"), 0),
                _fmt(row.get("returns"), 0), _fmt(row.get("iv"), 0)])
        fig.add_trace(go.Scatter(x=part.supplier_score, y=part.client_score, name=label,
            text=part.entity.astype(str), mode="markers", cliponaxis=False,
            marker=dict(size=18, color=RISK_GROUP_COLORS[key], opacity=.88, line=dict(color="#ffffff", width=1.5)),
            customdata=custom,
            hovertemplate=f"<b>{grain} %{{customdata[0]}}</b><br>CC %{{customdata[1]}}<br>Model %{{customdata[2]}}<br>"
                + t("供应商风险分", "Supplier score") + ": %{x:.1f}<br>" + t("客户端风险分", "Client score") + ": %{y:.1f}<br>"
                + "Return Qty %{customdata[5]} · IV Qty %{customdata[6]}<br>Risk Score %{customdata[3]}<br>"
                + t("风险等级", "Risk level") + f" {label}<br>Strategy %{{customdata[4]}}<extra></extra>"))
    # Place labels around dense points without shifting the measured coordinates.
    occupied = []
    label_rows = view.sort_values("risk_lower", ascending=False, kind="stable")
    plot_width, plot_height = 1000, 370
    anchors = list(zip(
        label_rows.supplier_score * plot_width / 100,
        (100 - label_rows.client_score) * plot_height / 100,
    ))
    positions = [(0,-24),(0,24),(48,0),(-48,0),(58,-25),(-58,-25),(58,25),(-58,25),
                 (0,-48),(0,48),(86,0),(-86,0),(86,-45),(-86,-45),(86,45),(-86,45),
                 (0,-72),(0,72),(116,0),(-116,0)]
    for (_, row), (px, py) in zip(label_rows.iterrows(), anchors):
        label = str(row.entity)
        width = max(45, len(label)*8)
        choices = []
        for dx,dy in positions:
            box = (px+dx-width/2-3,py+dy-11,px+dx+width/2+3,py+dy+11)
            overlaps = sum(box[0]<old[2] and box[2]>old[0] and box[1]<old[3] and box[3]>old[1] for old in occupied)
            covered = sum(box[0]-10<x<box[2]+10 and box[1]-10<y<box[3]+10 for x,y in anchors)
            outside = box[0]<6 or box[2]>plot_width-6 or box[1]<6 or box[3]>plot_height-6
            penalty = overlaps*10000 + covered*1000 + abs(dx) + abs(dy)
            choices.append((outside, penalty, dx, dy, box))
        _, _, dx, dy, box = min(choices, key=lambda choice: choice[:2])
        occupied.append(box)
        fig.add_annotation(x=row.supplier_score,y=row.client_score,xref="x",yref="y",ax=dx,ay=dy,
            text=html.escape(label),showarrow=True,arrowhead=0,arrowwidth=.8,arrowcolor="#a7b1c2",
            standoff=10,font=dict(size=14,color="#344054"),bgcolor="rgba(255,255,255,0.88)",borderpad=2)
    if focused_cc:
        for trace in fig.data:
            trace.selectedpoints = [i for i, point in enumerate(trace.customdata) if point[1] == focused_cc]
            trace.selected = dict(marker=dict(opacity=1))
            trace.unselected = dict(marker=dict(opacity=.3))
    apply_quality_chart_style(fig, height=500, showlegend=True)
    fig.update_layout(margin=dict(l=24, r=36, t=58, b=48),
        legend=dict(orientation="h", x=0, y=1.15, title_text=t("风险等级", "Risk level"), font_size=14,
            itemclick=False, itemdoubleclick=False),
        hoverlabel=dict(bgcolor="#f8faff", bordercolor="#8795e8", font_size=15, align="left"),
        transition=dict(duration=420, easing="cubic-in-out"), clickmode="event+select")
    axis_style = dict(
        range=[0, 100], tickvals=[0, 20, 40, 60, 80, 100], title_font_size=15,
        showline=True, linecolor="#64748b", linewidth=1.25, ticks="outside",
        tickcolor="#64748b", ticklen=4, layer="below traces", zeroline=False,
    )
    fig.update_xaxes(title_text=t("供应商风险分（PQC + AQL）", "Supplier score (PQC + AQL)"),
        side="bottom", title_standoff=12, **axis_style)
    fig.update_yaxes(title_text=t("客户端风险分（Return Qty + IV Qty）", "Client score (Return Qty + IV Qty)"),
        side="left", title_standoff=10, **axis_style)
    fig.add_vline(x=50, line_dash="dash", line_color="#8b96b8", opacity=.45)
    fig.add_hline(y=50, line_dash="dash", line_color="#8b96b8", opacity=.45)
    return fig


def _registry():
    """Automatic private source configuration; never package the workbook publicly.

    Production can connect an access-controlled, already synchronized workbook
    through TU_STRATEGY_WORKBOOK, or approved normalized records through secrets.
    Registry membership uses the binary Strategy policy; connection state is retained in the audit.
    """
    path = os.environ.get("TU_STRATEGY_WORKBOOK", "")
    records = []
    try:
        path = path or st.secrets.get("TU_STRATEGY_WORKBOOK", "")
        normalized = st.secrets.get("TU_STRATEGY_RECORDS_JSON", "")
    except (FileNotFoundError, KeyError):
        normalized = ""
    try:
        if path:
            return _read_strategy_file(path, Path(path).stat().st_mtime_ns), "connected"
        if normalized:
            records = json.loads(normalized)
            if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
                raise ValueError("Invalid Strategy registry")
            for row in records:
                if not isinstance(row.get("models", []), list) or not isinstance(row.get("ccs", []), list) or not isinstance(row.get("strategic"), bool):
                    raise ValueError("Invalid Strategy identity fields")
                if any(not isinstance(value, str) for value in row.get("models", []) + row.get("ccs", [])):
                    raise ValueError("Invalid Strategy identifier")
                if not isinstance(row.get("supplier_code", ""), str) or not isinstance(row.get("season", ""), str):
                    raise ValueError("Invalid Strategy scope")
            return records, "connected"
    except (OSError, ValueError, KeyError, TypeError):
        return [], "invalid"
    return [], "unavailable"


@st.cache_data(show_spinner=False)
def _read_strategy_file(path, modified_ns):
    return load_strategy_workbook(path)


def _fmt(value, precision=1):
    value = number(value)
    return "—" if value is None else f"{value:,.{precision}f}"


def _table(rows, translate):
    t = translate
    e = lambda value: html.escape(str(value))
    body = []
    for rank, row in enumerate(rows.itertuples(index=False), 1):
        status = t("战略", "Strategy") if row.strategy_status == "yes" else t("非战略", "Non-strategy") if row.strategy_status == "no" else t("不适用", "N/A") if row.strategy_status == "not_applicable" else t("待确认", "Pending")
        style = "confirmed" if row.strategy_status in ("yes", "no") else "pending"
        score = _fmt(row.risk_score) if row.complete else f'{_fmt(row.risk_lower)}–{_fmt(row.risk_upper)}'
        models = e(row.models or "—")
        label = f'<strong>{e(row.entity)}</strong>'
        if row.grain == "CC" and row.models:
            preview = row.models.split(" / ")[0]
            extra = len(row.models.split(" / ")) - 1
            label += f'<details><summary>Model · {e(preview)}' + (f' +{extra}' if extra else '') + f'</summary>{models}</details>'
        elif row.grain == "Model":
            label += f'<span class="tu-poc-cc">CC {e(row.cc or "—")}</span>'
        body.append(f'<tr><td>{rank:02d}</td><td>{label}</td><td>{_fmt(row.client_score)}</td>'
                    f'<td><span class="{style}">{status}</span></td><td>{_fmt(row.supplier_score)}</td>'
                    f'<td><strong>{_fmt(row.risk_lower)}</strong></td><td>{score}</td>'
                    f'<td>{_fmt(row.known_weight, 0)}%</td></tr>')
    headers = [t("排序", "Rank"), rows.grain.iloc[0], t("客户端", "Client"), "Strategy", t("供应商", "Supplier"),
               t("已知贡献", "Known points"), t("总分 / 区间", "Score / range"), t("已知权重", "Known weight")]
    widths = [5, 20, 11, 13, 11, 12, 17, 11]
    return ('<div class="tu-poc-table-wrap"><table class="tu-poc-table"><colgroup>'
            + ''.join(f'<col style="width:{width}%">' for width in widths) + '</colgroup><thead><tr>'
            + ''.join(f'<th>{e(label)}</th>' for label in headers) + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>')


def render_tu_risk_poc(pqc, aql, voice, cases, scope, *, translate=None, registry_override=None):
    """Render the Model risk levels and return the baseline CC report facts."""
    t = translate or (lambda zh, en: zh)
    st.markdown('<style>'+CSS+'</style>', unsafe_allow_html=True)
    registry, connection = _registry() if registry_override is None else (registry_override, "connected")
    profile = tu_cluster_profile(st.session_state)
    rows, audit = build_tu_risk(pqc,aql,voice,cases,scope,grain="Model",department="Hugss",
        profile=profile,registry=registry,season="",inspection_only=True)
    audit["strategy_connection"] = connection
    st.session_state["_tu_risk_poc_audit"] = audit
    st.session_state["_tu_risk_poc_rows"] = rows.to_dict("records")
    # The CC report uses its independently scored default profile.
    cc_rows, cc_audit = build_tu_risk(pqc,aql,voice,cases,scope,grain="CC",department="Hugss",
        profile=default_profile("CC"),registry=registry,season="",inspection_only=True)
    st.session_state["_tu_risk_poc_cc_rows"] = cc_rows.to_dict("records")
    st.session_state["_tu_risk_poc_cc_audit"] = cc_audit
    with st.container(key="tu_poc_distribution_panel"):
        st.subheader(t("产品风险分布", "Product Risk Distribution"))
        if rows.empty:
            prepare_cluster_focus(st.session_state, scope, [])
            st.info(t("当前筛选暂无接入的检验产品。现有试点覆盖 Hugss · ZX。", "No connected inspection products in this selection. Current pilot: Hugss · ZX."))
            return cc_rows
        medium, high = current_risk_level_thresholds(st.session_state)
        st.caption(t(f"按 Model 的综合风险分下界定档。低 < {medium:g} · 中 {medium:g} 至低于 {high:g} · 高 ≥ {high:g}。虚线为两轴 50 分参考线。",
                     f"Based on each Model's score lower bound. Low < {medium:g} · Medium {medium:g} to below {high:g} · High ≥ {high:g}. Dashed lines mark the 50-point reference on each axis."))
        plotted = risk_distribution_groups(rows, (medium, high))
        if not plotted.empty:
            options = list(RISK_GROUP_LABELS)
            selected = st.multiselect(t("风险等级", "Risk levels"), options, default=options,
                format_func=lambda value: t(*RISK_GROUP_LABELS[value]), key="tu_poc_risk_levels_Hugss_Model")
            visible_ccs = plotted.loc[plotted.risk_group.isin(selected), "cc"].tolist()
            focused_cc = prepare_cluster_focus(st.session_state, scope, visible_ccs)
            if selected:
                fig = build_risk_distribution_figure(plotted, "Model", t, selected, focused_cc=focused_cc)
                chart_key = f"tu_poc_distribution_{st.session_state.get(REVISION_KEY, 0)}"
                st.plotly_chart(fig, use_container_width=True, key=chart_key, theme=None,
                    on_select=lambda: sync_cluster_focus(st.session_state, chart_key, visible_ccs), selection_mode="points",
                    config={"displayModeBar":True, "scrollZoom":False, "displaylogo":False})
            else:
                st.info(t("请选择至少一个风险等级。", "Select at least one risk level."))
        else:
            prepare_cluster_focus(st.session_state, scope, [])
            st.info(t("当前范围没有同时可计算两轴的记录，保留空图。", "No records with both scores; the plot remains empty."))
        render_tu_scoring_reference(t,profile)
    return cc_rows
