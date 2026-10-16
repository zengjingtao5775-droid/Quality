"""Compact source-backed TU Risk POC embedded in the shared dashboard."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import html
import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tu_risk_poc import (RISK_POC_VERSION, DEPARTMENTS, GRAINS, RiskProfile, default_profile,
                         build_tu_risk, load_strategy_workbook, number, profile_from_saved)
from quality_chart_ui import apply_quality_chart_style

RISK_POC_UI_VERSION = "2026-10-16-v4-compact-binary-strategy"
RISK_GROUP_COLORS = {"high": "#e85d68", "medium": "#f0a94a", "low": "#2aa876", "single": "#2854c5"}

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


def risk_distribution_groups(rows):
    """Restore the former three-group view without changing any source score."""
    view = rows.copy()
    for column in ("supplier_score", "client_score", "risk_lower"):
        view[column] = pd.to_numeric(view.get(column, pd.Series(index=view.index, dtype=float)), errors="coerce")
    if "entity" not in view:
        view["entity"] = pd.Series(index=view.index, dtype=str)
    valid = np.isfinite(view.supplier_score) & np.isfinite(view.client_score) & np.isfinite(view.risk_lower)
    view = view.loc[valid].sort_values("entity", kind="stable").copy()
    if view.empty:
        view["risk_group"] = pd.Series(dtype=str)
        return view
    points = view[["supplier_score", "client_score"]].to_numpy(dtype=float)
    count = min(3, len(np.unique(points, axis=0)))
    if count == 1:
        view["risk_group"] = "single"
        return view
    # Same standardized, deterministic K-means used by the previous chart.
    scale = points.std(axis=0)
    scale[scale == 0] = 1
    normalized = (points - points.mean(axis=0)) / scale
    order = np.argsort(normalized.sum(axis=1), kind="stable")
    seeds = np.linspace(0, len(order) - 1, count).round().astype(int)
    centers = normalized[order[seeds]].copy()
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
    view["_distribution_group"] = labels
    rank = view.groupby("_distribution_group").risk_lower.mean().sort_values(kind="stable").index.tolist()
    names = {rank[0]: "low", rank[-1]: "high"} if len(rank) > 1 else {rank[0]: "single"}
    names.update({cluster_id: "medium" for cluster_id in rank[1:-1]})
    view["risk_group"] = view._distribution_group.map(names)
    return view.drop(columns="_distribution_group")


def build_risk_distribution_figure(grouped, grain, translate=None, selected_groups=None):
    """Use exact scored coordinates; colors/labels never feed back into scoring."""
    t = translate or (lambda zh, en: zh)
    view = grouped if selected_groups is None else grouped.loc[grouped.risk_group.isin(selected_groups)]
    labels = {"high": t("高风险组", "High-risk group"), "medium": t("中风险组", "Medium-risk group"),
              "low": t("低风险组", "Low-risk group"), "single": t("当前分组", "Current group")}
    fig = go.Figure()
    for key in ("high", "medium", "low", "single"):
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
        fig.add_trace(go.Scatter(x=part.supplier_score, y=part.client_score, name=labels[key],
            text=part.entity.astype(str), mode="markers", cliponaxis=False,
            marker=dict(size=18, color=RISK_GROUP_COLORS[key], opacity=.88, line=dict(color="#ffffff", width=1.5)),
            customdata=custom,
            hovertemplate=f"<b>{grain} %{{customdata[0]}}</b><br>CC %{{customdata[1]}}<br>Model %{{customdata[2]}}<br>"
                + t("供应商风险分", "Supplier score") + ": %{x:.1f}<br>" + t("客户端风险分", "Client score") + ": %{y:.1f}<br>"
                + "Return Qty %{customdata[5]} · IV Qty %{customdata[6]}<br>Risk Score %{customdata[3]}<br>Strategy %{customdata[4]}<extra></extra>"))
    # Place labels around dense points without shifting the measured coordinates.
    occupied = []
    anchors = [(float(row.supplier_score)+4)/108*1000 for _, row in view.iterrows()]
    anchor_y = [(108-float(row.client_score))/113*370 for _, row in view.iterrows()]
    positions = [(0,-24),(0,24),(48,0),(-48,0),(58,-25),(-58,-25),(58,25),(-58,25),
                 (0,-48),(0,48),(86,0),(-86,0),(86,-45),(-86,-45),(86,45),(-86,45),
                 (0,-72),(0,72),(116,0),(-116,0)]
    for _, row in view.sort_values("risk_lower",ascending=False,kind="stable").iterrows():
        label = str(row.entity)
        px, py = (float(row.supplier_score)+4)/108*1000, (108-float(row.client_score))/113*370
        width = max(45, len(label)*8)
        choices = []
        for dx,dy in positions:
            box = (px+dx-width/2-3,py+dy-11,px+dx+width/2+3,py+dy+11)
            overlaps = sum(box[0]<old[2] and box[2]>old[0] and box[1]<old[3] and box[3]>old[1] for old in occupied)
            covered = sum(box[0]-10<x<box[2]+10 and box[1]-10<y<box[3]+10 for x,y in zip(anchors,anchor_y))
            outside = box[0]<-20 or box[2]>1020 or box[1]<-12 or box[3]>382
            choices.append((overlaps*10000+covered*1000+int(outside)*10000+abs(dx)+abs(dy),dx,dy,box))
        _,dx,dy,box = min(choices,key=lambda choice:choice[0])
        occupied.append(box)
        fig.add_annotation(x=row.supplier_score,y=row.client_score,xref="x",yref="y",ax=dx,ay=dy,
            text=html.escape(label),showarrow=True,arrowhead=0,arrowwidth=.8,arrowcolor="#a7b1c2",
            standoff=10,font=dict(size=14,color="#344054"),bgcolor="rgba(255,255,255,0.88)",borderpad=2)
    apply_quality_chart_style(fig, height=500, showlegend=True)
    fig.update_layout(margin=dict(l=24, r=36, t=58, b=48),
        legend=dict(orientation="h", x=0, y=1.15, title_text=t("相对风险分组", "Relative risk groups"), font_size=14,
            itemclick=False, itemdoubleclick=False),
        hoverlabel=dict(bgcolor="#f8faff", bordercolor="#8795e8", font_size=15, align="left"),
        transition=dict(duration=420, easing="cubic-in-out"))
    fig.update_xaxes(title_text=t("供应商风险分（PQC + AQL）", "Supplier score (PQC + AQL)"),
        range=[-4, 104], tickvals=[0, 20, 40, 60, 80, 100], title_font_size=15, title_standoff=12)
    fig.update_yaxes(title_text=t("客户端风险分（Return Qty + IV Qty）", "Client score (Return Qty + IV Qty)"),
        range=[-5, 108], tickvals=[0, 20, 40, 60, 80, 100], title_font_size=15, title_standoff=10)
    fig.add_vline(x=50, line_dash="dash", line_color="#8b96b8", opacity=.45)
    fig.add_hline(y=55, line_dash="dash", line_color="#8b96b8", opacity=.45)
    fig.add_annotation(xref="paper", yref="paper", x=.98, y=.98,
        text=t("右上：检验表现与客户反馈双高", "Upper right: elevated inspections and client signals"),
        showarrow=False, font=dict(size=14, color="#dc2626"), bgcolor="rgba(255,255,255,0.85)")
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


def _profile_controls(department, grain, t):
    saved_profiles = st.session_state.setdefault("_tu_risk_poc_profiles", {})
    profile_key = f"{department}:{grain}"
    defaults = profile_from_saved(saved_profiles.get(profile_key), grain)
    prefix = f"tu_poc_{department.lower()}_{grain.lower()}"
    with st.expander(t("权重设置与评分阈值", "Risk weights and score thresholds"), expanded=False):
        st.markdown(t("这些是 POC 建议值，尚未校准；当前会话内各部门、各粒度独立保存，可下载配置。只调整评分政策，原始记录自动读取。", "These are uncalibrated POC proposals. Departments and grains have separate session settings; export the policy to retain it. Source records load automatically."))
        st.markdown(t("Strategy：是 = 1，否 = 0；产品风险分 = Strategy × 100。", "Strategy: Yes = 1, No = 0; product score = Strategy × 100."))
        a, b, c = st.columns(3)
        client = a.number_input(t("W1 · 客户端 %", "W1 · Client %"), 0., 100., float(defaults.client_weight), step=5., key=prefix+"_w1")
        product = b.number_input(t("W2 · 产品 %", "W2 · Product %"), 0., 100., float(defaults.product_weight), step=5., disabled=grain=="Supplier", key=prefix+"_w2")
        supplier = 100-client-product
        c.metric(t("W3 · 供应商 %", "W3 · Supplier %"), f"{supplier:g}%")
        a, b = st.columns(2)
        returned = a.number_input(t("客户端内部 · Return Qty %", "Within client · Return Qty %"), 0., 100., float(defaults.return_weight), step=5., key=prefix+"_return_weight")
        pqc = b.number_input(t("供应商内部 · PQC %", "Within supplier · PQC %"), 0., 100., float(defaults.pqc_weight), step=5., key=prefix+"_pqc_weight")
        st.markdown(t(f"IV Qty = {100-returned:g}%；AQL = {100-pqc:g}%。客户端与供应商的内部权重各自合计 100%。", f"IV Qty = {100-returned:g}%; AQL = {100-pqc:g}%. Each internal weight group totals 100%."))
        inputs = {}
        a, b, c, d = st.columns(4)
        for col, idx, name, warning, critical, suffix in (
            (a, "pqc", "PQC DPU", defaults.pqc_warning_pct, defaults.pqc_critical_pct, "%"),
            (b, "aql", t("AQL 首验未通过率", "AQL first-result fail rate"), defaults.aql_warning_pct, defaults.aql_critical_pct, "%"),
            (d, "iv", "IV Qty", defaults.iv_warning, defaults.iv_critical, t("件", "units"))):
            with col:
                st.markdown(f"**{name}**")
                inputs[idx+"_warning"] = st.number_input(t(f"50 分 · {suffix}", f"50 points · {suffix}"), min_value=.01, value=float(warning), key=prefix+"_"+idx+"_warning")
                inputs[idx+"_critical"] = st.number_input(t(f"100 分 · {suffix}", f"100 points · {suffix}"), min_value=.02, value=float(critical), key=prefix+"_"+idx+"_critical")
        with c:
            st.markdown("**Return Qty**")
            st.markdown(t("50 分 = 同范围产品退货数量的平均值，自动计算。", "50 points = the automatically calculated peer mean return quantity."))
            return_multiple = st.number_input(t("100 分 · 平均值的倍数", "100 points · multiple of mean"), min_value=1.01, value=float(defaults.return_critical_multiple), step=.25, key=prefix+"_return_multiple")
        a,b = st.columns(2)
        prior_d = a.number_input(t("PQC 平滑先验疵点", "PQC prior defect points"), min_value=0., value=float(defaults.pqc_prior_defects), key=prefix+"_prior_d")
        prior_n = b.number_input(t("PQC 平滑先验样本", "PQC prior sample size"), min_value=0., value=float(defaults.pqc_prior_samples), key=prefix+"_prior_n")
        profile = replace(defaults, client_weight=client, product_weight=product, supplier_weight=supplier,
                          return_weight=returned, iv_weight=100-returned, pqc_weight=pqc, aql_weight=100-pqc,
                          pqc_warning_pct=inputs["pqc_warning"], pqc_critical_pct=inputs["pqc_critical"],
                          aql_warning_pct=inputs["aql_warning"], aql_critical_pct=inputs["aql_critical"],
                          return_critical_multiple=return_multiple,
                          iv_warning=inputs["iv_warning"], iv_critical=inputs["iv_critical"],
                          pqc_prior_defects=prior_d, pqc_prior_samples=prior_n)
        # Streamlit cleans hidden widget state after a grain/department switch.
        # Keep the policy separately so independent profiles actually persist.
        saved_profiles[profile_key] = profile.__dict__
        try:
            profile.validate()
        except ValueError:
            st.error(t("权重不能为负且须合计 100%；100 分阈值必须大于 50 分阈值。请调整试算参数。", "Weights must be non-negative and total 100%; critical thresholds must exceed warning thresholds."))
            return None
        st.download_button(t("下载当前评分配置", "Download scoring policy"), json.dumps({"version":RISK_POC_VERSION,"department":department,"grain":grain,"profile":profile.__dict__},ensure_ascii=False,indent=2),
                           file_name=f"tu-risk-{department.lower()}-{grain.lower()}.json", mime="application/json", key=prefix+"_download_policy")
    return profile


def render_tu_risk_poc(pqc, aql, voice, cases, scope, *, translate=None, registry_override=None):
    """Return scored CC facts for the shared Pareto/report; current view has its own grain."""
    t = translate or (lambda zh, en: zh)
    st.session_state["_tu_risk_poc_rows"] = []
    st.session_state["_tu_risk_poc_cc_rows"] = []
    st.session_state["_tu_risk_poc_cc_audit"] = {}
    st.markdown('<style>'+CSS+'</style>', unsafe_allow_html=True)
    with st.container(border=True, key="tu_three_dimension_risk"):
        st.markdown('<div class="tu-poc-head"><h2>'+html.escape(t("Risk Score 设置", "Risk Score Settings"))+'</h2><span>'+html.escape(t("试算 · 未校准", "Trial · Uncalibrated"))+'</span></div>', unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns([1,1,1.5,1])
        department = c1.selectbox(t("部门", "Department"), DEPARTMENTS, key="tu_poc_department")
        grain = c2.selectbox(t("计算粒度", "Risk grain"), GRAINS, key="tu_poc_grain")
        population = c3.selectbox(t("产品范围", "Population"), ["inspected", "all"], format_func=lambda x: t("有检验记录", "With inspections") if x=="inspected" else t("全部可用产品", "All available products"), key="tu_poc_population")
        registry, connection = _registry() if registry_override is None else (registry_override, "connected")
        seasons = sorted({record.get("season", "") for record in registry} - {""})
        season = c4.selectbox(t("Strategy 季节", "Strategy season"), [""]+seasons, format_func=lambda x:x or t("全部季节", "All seasons"), key="tu_poc_season")
        profile = _profile_controls(department, grain, t)
        if profile is None:
            st.session_state["_tu_risk_poc_audit"]={"status":"invalid_policy"}
            return pd.DataFrame()
        rows, audit = build_tu_risk(pqc,aql,voice,cases,scope,grain=grain,department=department,profile=profile,registry=registry,season=season,inspection_only=population=="inspected")
        audit["strategy_connection"]=connection
        st.session_state["_tu_risk_poc_audit"]=audit
        st.session_state["_tu_risk_poc_rows"]=rows.to_dict("records")
        if rows.empty:
            st.session_state["_tu_risk_poc_cc_audit"] = {**audit, "grain": "CC"}
            st.info(t("当前部门/筛选暂无接入的检验产品。现有试点覆盖 Hugss · ZX；Knit 和 Woven 保留部门位置，待接入自动数据源。", "No inspection products are connected for this department/selection. Current pilot: Hugss · ZX. Knit and Woven await automatic sources."))
            return pd.DataFrame()
        with st.container(key="tu_poc_distribution_panel"):
            st.subheader(t("高风险产品聚类分析", "High-Risk Product Cluster Analysis"))
            plotted = risk_distribution_groups(rows)
            if not plotted.empty:
                options = [key for key in ("high", "medium", "low", "single") if key in set(plotted.risk_group)]
                group_names = {"high": t("高风险组", "High-risk group"), "medium": t("中风险组", "Medium-risk group"),
                    "low": t("低风险组", "Low-risk group"), "single": t("当前分组", "Current group")}
                selected = st.multiselect(t("聚类筛选（可多选）", "Cluster filter (multi-select)"), options,
                    default=options, format_func=lambda value: group_names[value], key=f"tu_poc_groups_{department}_{grain}")
                if selected:
                    fig = build_risk_distribution_figure(plotted, grain, t, selected)
                    st.plotly_chart(fig, use_container_width=True, key="tu_poc_distribution",
                        config={"displayModeBar":True, "scrollZoom":False, "displaylogo":False})
                else:
                    st.info(t("请选择至少一个风险分组。", "Select at least one risk group."))
            else:
                st.info(t("当前范围没有同时可计算两轴的记录，保留空图。", "No records with both scores; the plot remains empty."))
        # CC Pareto/report always recompute at CC grain; Model scores are never
        # summed or averaged into a CC score. Independent profile is retained.
        saved_cc = st.session_state.get("_tu_risk_poc_profiles", {}).get(f"{department}:CC")
        cc_profile=profile if grain=="CC" else profile_from_saved(saved_cc, "CC")
        try:
            cc_rows,cc_audit=build_tu_risk(pqc,aql,voice,cases,scope,grain="CC",department=department,profile=cc_profile,registry=registry,season=season,inspection_only=population=="inspected")
        except ValueError:
            st.warning(t("CC 评分配置无效，CC 帕累托及报告暂留空；切换 CC 粒度修正参数。", "CC policy is invalid. CC Pareto/report remain empty; switch to CC to repair the policy."))
            return pd.DataFrame()
        st.session_state["_tu_risk_poc_cc_rows"]=cc_rows.to_dict("records")
        st.session_state["_tu_risk_poc_cc_audit"]=cc_audit
        return cc_rows
