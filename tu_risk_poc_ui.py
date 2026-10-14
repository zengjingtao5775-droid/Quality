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
                         build_tu_risk, load_strategy_workbook, number)

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
"""


def _registry():
    """Automatic private source configuration; never package the workbook publicly.

    Production can connect an access-controlled, already synchronized workbook
    through TU_STRATEGY_WORKBOOK, or approved normalized records through secrets.
    A missing/invalid source is visible and yields pending identities.
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
    defaults = RiskProfile(**saved_profiles[profile_key]) if profile_key in saved_profiles else default_profile(grain)
    prefix = f"tu_poc_{department.lower()}_{grain.lower()}"
    with st.expander(t("试算参数 · 三维权重及换分阈值", "Trial parameters · weights and score thresholds"), expanded=False):
        st.markdown(t("这些是 POC 建议值，尚未校准；当前会话内各部门、各粒度独立保存，可下载配置。只调整评分政策，原始记录自动读取。", "These are uncalibrated POC proposals. Departments and grains have separate session settings; export the policy to retain it. Source records load automatically."))
        a, b, c = st.columns(3)
        client = a.number_input(t("W1 · 客户端 %", "W1 · Client %"), 0., 100., float(defaults.client_weight), step=5., key=prefix+"_w1")
        product = b.number_input(t("W2 · 产品 %", "W2 · Product %"), 0., 100., float(defaults.product_weight), step=5., disabled=grain=="Supplier", key=prefix+"_w2")
        supplier = 100-client-product
        c.metric(t("W3 · 供应商 %", "W3 · Supplier %"), f"{supplier:g}%")
        a, b = st.columns(2)
        rpm = a.number_input(t("客户端内部 · RPM %", "Within client · RPM %"), 0., 100., float(defaults.rpm_weight), step=5., key=prefix+"_rpm_weight")
        pqc = b.number_input(t("供应商内部 · PQC %", "Within supplier · PQC %"), 0., 100., float(defaults.pqc_weight), step=5., key=prefix+"_pqc_weight")
        st.markdown(t(f"IV = {100-rpm:g}%；AQL = {100-pqc:g}%。客户端与供应商的内部权重各自合计 100%。", f"IV = {100-rpm:g}%; AQL = {100-pqc:g}%. Each internal weight group totals 100%."))
        inputs = {}
        a, b, c, d = st.columns(4)
        for col, name, warning, critical, suffix in (
            (a, "PQC DPU", defaults.pqc_warning_pct, defaults.pqc_critical_pct, "%"),
            (b, t("AQL 首验未通过率", "AQL first-result fail rate"), defaults.aql_warning_pct, defaults.aql_critical_pct, "%"),
            (c, "RPM", defaults.rpm_warning, defaults.rpm_critical, ""),
            (d, "IV", defaults.iv_warning, defaults.iv_critical, t("件", "cases"))):
            idx = ("pqc", "aql", "rpm", "iv")[(a,b,c,d).index(col)]
            with col:
                st.markdown(f"**{name}**")
                inputs[idx+"_warning"] = st.number_input(t(f"50 分 · {suffix}", f"50 points · {suffix}"), min_value=.01, value=float(warning), key=prefix+"_"+idx+"_warning")
                inputs[idx+"_critical"] = st.number_input(t(f"100 分 · {suffix}", f"100 points · {suffix}"), min_value=.02, value=float(critical), key=prefix+"_"+idx+"_critical")
        a,b = st.columns(2)
        prior_d = a.number_input(t("PQC 平滑先验疵点", "PQC prior defect points"), min_value=0., value=float(defaults.pqc_prior_defects), key=prefix+"_prior_d")
        prior_n = b.number_input(t("PQC 平滑先验样本", "PQC prior sample size"), min_value=0., value=float(defaults.pqc_prior_samples), key=prefix+"_prior_n")
        profile = replace(defaults, client_weight=client, product_weight=product, supplier_weight=supplier,
                          rpm_weight=rpm, iv_weight=100-rpm, pqc_weight=pqc, aql_weight=100-pqc,
                          pqc_warning_pct=inputs["pqc_warning"], pqc_critical_pct=inputs["pqc_critical"],
                          aql_warning_pct=inputs["aql_warning"], aql_critical_pct=inputs["aql_critical"],
                          rpm_warning=inputs["rpm_warning"], rpm_critical=inputs["rpm_critical"],
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
        st.markdown('<div class="tu-poc-head"><h2>'+html.escape(t("TU · 三维 Risk Score POC", "TU · Three-Dimension Risk POC"))+'</h2><span>'+html.escape(t("试算 · 未校准", "Trial · Uncalibrated"))+'</span></div>', unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns([1,1,1.5,1])
        department = c1.selectbox(t("部门", "Department"), DEPARTMENTS, key="tu_poc_department")
        grain = c2.selectbox(t("计算粒度", "Risk grain"), GRAINS, key="tu_poc_grain")
        population = c3.selectbox(t("产品范围", "Population"), ["inspected", "all"], format_func=lambda x: t("有检验记录", "With inspections") if x=="inspected" else t("全部可用产品", "All available products"), key="tu_poc_population")
        registry, connection = _registry() if registry_override is None else (registry_override, "connected")
        seasons = sorted({record.get("season", "") for record in registry} - {""})
        season = c4.selectbox(t("Strategy 季节", "Strategy season"), [""]+seasons, format_func=lambda x:x or t("待指定", "Unspecified"), key="tu_poc_season")
        profile = _profile_controls(department, grain, t)
        if profile is None:
            st.session_state["_tu_risk_poc_audit"]={"status":"invalid_policy"}
            return pd.DataFrame()
        st.markdown('<div class="tu-poc-formula">'+html.escape(t(
            f"Risk = 客户端（RPM + IV）× {profile.client_weight:g}% + 产品（Strategy）× {profile.product_weight:g}% + 供应商（PQC + AQL）× {profile.supplier_weight:g}%",
            f"Risk = Client (RPM + IV) × {profile.client_weight:g}% + Product (Strategy) × {profile.product_weight:g}% + Supplier (PQC + AQL) × {profile.supplier_weight:g}%"))+'</div>',unsafe_allow_html=True)
        rows, audit = build_tu_risk(pqc,aql,voice,cases,scope,grain=grain,department=department,profile=profile,registry=registry,season=season,inspection_only=population=="inspected")
        audit["strategy_connection"]=connection
        st.session_state["_tu_risk_poc_audit"]=audit
        st.session_state["_tu_risk_poc_rows"]=rows.to_dict("records")
        if rows.empty:
            st.session_state["_tu_risk_poc_cc_audit"] = {**audit, "grain": "CC"}
            st.info(t("当前部门/筛选暂无接入的检验产品。现有试点覆盖 Hugss · ZX；Knit 和 Woven 保留部门位置，待接入自动数据源。", "No inspection products are connected for this department/selection. Current pilot: Hugss · ZX. Knit and Woven await automatic sources."))
            return pd.DataFrame()
        complete = int(rows.complete.sum())
        status = t(f"{len(rows)} 个{grain} · 展示前 {min(10,len(rows))} 个 · 完整总分 {complete} 个", f"{len(rows)} {grain}s · Top {min(10,len(rows))} shown · {complete} complete scores")
        missing = t("Strategy 跟进表未接入", "Strategy follow-up not connected") if connection=="unavailable" else t("Strategy 来源需修复", "Strategy source requires repair") if connection=="invalid" else t("Strategy 未匹配仍待确认", "Unmatched Strategy identities remain pending")
        st.markdown('<div class="tu-poc-status"><span>'+html.escape(status)+'</span><b>'+html.escape(missing)+'</b><span>'+html.escape(t("暂按已知贡献排列，缺失项不当作零；区间重叠时不能断言谁的总风险更高。", "Ordered by known contributions; missing is not zero. Overlapping bounds do not establish total-risk order."))+'</span></div>',unsafe_allow_html=True)
        st.markdown(_table(rows.head(10),t),unsafe_allow_html=True)
        with st.expander(t("计算明细 · 分子、分母及每项贡献", "Calculation detail · denominators and contributions"),expanded=False):
            entity=st.selectbox(t("查看产品 / 供应商", "Inspect product / supplier"),rows.entity.tolist(),key=f"tu_poc_{grain.lower()}_example")
            example=rows.loc[rows.entity.eq(entity)].iloc[0]
            pdpu = _fmt(example.pqc_dpu*100,3) if number(example.pqc_dpu) is not None else "—"
            aqlrate = _fmt(example.aql_fail_rate*100,2) if number(example.aql_fail_rate) is not None else "—"
            explanation = [
                t(f"PQC：{_fmt(example.pqc_defects,0)} 疵点 ÷ {_fmt(example.pqc_inspected,0)} 检验 = {pdpu}%。平滑后（D + {profile.pqc_prior_defects:g}）÷（N + {profile.pqc_prior_samples:g}），换分后 {_fmt(example.pqc_score)} 分。", f"PQC: {_fmt(example.pqc_defects,0)} defects / {_fmt(example.pqc_inspected,0)} inspections = {pdpu}%. Smooth (D + {profile.pqc_prior_defects:g}) / (N + {profile.pqc_prior_samples:g}); score {_fmt(example.pqc_score)}."),
                t(f"AQL：{example.aql_fail} 条首验未通过 ÷ {example.aql_valid_records} 条有效记录 = {aqlrate}%；共 {example.aql_records} 条记录，换分后 {_fmt(example.aql_score)} 分。重验后 PASS 仍视为首验未通过。", f"AQL: {example.aql_fail} first-result failures / {example.aql_valid_records} valid of {example.aql_records} records = {aqlrate}%; score {_fmt(example.aql_score)}. PASS after recheck is a first-result failure."),
                t(f"RPM：{_fmt(example.returns,0)} 退货 ÷ {_fmt(example.sales,0)} 销量 × 1,000,000 = {_fmt(example.rpm)}；换分后 {_fmt(example.rpm_score)} 分。IV：{_fmt(example.iv,0)} 个 Before Sales 唯一案例，换分后 {_fmt(example.iv_score)} 分。", f"RPM: {_fmt(example.returns,0)} returns / {_fmt(example.sales,0)} sales × 1,000,000 = {_fmt(example.rpm)}; score {_fmt(example.rpm_score)}. IV: {_fmt(example.iv,0)} unique Before Sales cases; score {_fmt(example.iv_score)}."),
                t(f"客户端 = RPM 分 × {profile.rpm_weight:g}% + IV 分 × {profile.iv_weight:g}% = {_fmt(example.client_score)}；供应商 = PQC 分 × {profile.pqc_weight:g}% + AQL 分 × {profile.aql_weight:g}% = {_fmt(example.supplier_score)}。", f"Client = RPM score × {profile.rpm_weight:g}% + IV score × {profile.iv_weight:g}% = {_fmt(example.client_score)}; Supplier = PQC score × {profile.pqc_weight:g}% + AQL score × {profile.aql_weight:g}% = {_fmt(example.supplier_score)}."),
                t(f"已知贡献：客户端 {_fmt(example.client_contribution)} + 供应商 {_fmt(example.supplier_contribution)}" + (f" + 产品 {_fmt(example.product_contribution)}" if number(example.product_contribution) is not None else "；产品待确认，未计入已知贡献") + f" → {_fmt(example.risk_lower)}。完整总分 {_fmt(example.risk_score)}；可能区间 {_fmt(example.risk_lower)}–{_fmt(example.risk_upper)}。", f"Known contribution: Client {_fmt(example.client_contribution)} + Supplier {_fmt(example.supplier_contribution)}" + (f" + Product {_fmt(example.product_contribution)}" if number(example.product_contribution) is not None else "; Product pending, not included in known contributions") + f" → {_fmt(example.risk_lower)}. Complete score {_fmt(example.risk_score)}; bounds {_fmt(example.risk_lower)}–{_fmt(example.risk_upper)}."),
            ]
            st.markdown('<div class="tu-poc-source">'+'<br><br>'.join(html.escape(line) for line in explanation)+'</div>',unsafe_allow_html=True)
            st.markdown(t("换分规则：不超过 50 分阈值，得分 = 50 × 数值 ÷ 阈值；两阈值之间，得分 = 50 + 50 ×（数值 − 50 分阈值）÷（100 分阈值 − 50 分阈值）；超过上限记 100 分。Strategy 确认是战略款记 100、明确非战略记 0、未匹配记待确认。", "Scoring: up to the warning threshold, score = 50 × value / warning; between thresholds, score = 50 + 50 × (value − warning) / (critical − warning); cap at 100. Strategy: confirmed Yes = 100, explicit No = 0, unmatched = pending."))
            st.markdown(t("分数用于复核优先级，不是不良概率。PQC 是每件检验的疵点数，不等于不合格件率；AQL 是记录层面的首验未通过率。客户 N0 源无日期，自定义日期不用于 RPM；Strategy 季节须明确匹配。审厂、CP、工人及手工矩阵不参与本次打分。", "Scores prioritize review, not defect probability. PQC is defects per inspected unit; AQL is first-result failure per inspection record. N0 customer snapshots are undated, so custom calendar ranges cannot supply RPM. Strategy season requires an explicit match. Audit, CP, workers and manual matrix scores are excluded."))
            st.download_button(t("下载当前计算明细", "Download current calculations"),rows.to_csv(index=False).encode("utf-8-sig"),file_name=f"tu-risk-poc-{grain.lower()}.csv",mime="text/csv",key="tu_poc_download_rows")
        with st.expander(t("风险分布 · 供应商检验表现 × 客户端反馈", "Risk distribution · supplier inspections vs client feedback"),expanded=False):
            plotted=rows.loc[rows.supplier_score.notna() & rows.client_score.notna()]
            if not plotted.empty:
                fig=go.Figure()
                for status,label,color in [("pending",t("Strategy 待确认", "Strategy pending"),"#64748b"),("candidate",t("Strategy 候选", "Strategy candidate"),"#d97706"),("yes",t("战略款", "Strategy Yes"),"#2854c5"),("no",t("非战略款", "Strategy No"),"#15803d"),("not_applicable",t("供应商粒度", "Supplier grain"),"#2854c5")]:
                    part=plotted.loc[plotted.strategy_status.eq(status)]
                    if part.empty:continue
                    fig.add_trace(go.Scatter(x=part.supplier_score,y=part.client_score,text=part.entity,name=label,mode="markers",marker={"size":12,"color":color},customdata=part[["risk_lower","risk_upper"]].values,hovertemplate="%{text}<br>Supplier: %{x:.1f}<br>Client: %{y:.1f}<br>Risk: %{customdata[0]:.1f}–%{customdata[1]:.1f}<extra></extra>"))
                fig.update_layout(height=330,margin=dict(l=20,r=20,t=10,b=15),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(size=16))
                fig.update_xaxes(title=t("供应商风险分（PQC + AQL）", "Supplier score (PQC + AQL)"),range=[-2,102],gridcolor="#e3e8f2")
                fig.update_yaxes(title=t("客户端风险分（RPM + IV）", "Client score (RPM + IV)"),range=[-2,102],gridcolor="#e3e8f2")
                st.plotly_chart(fig,use_container_width=True,key="tu_poc_distribution",config={"displayModeBar":False})
                st.markdown(t("颜色只表示已确认的产品身份；分布图不额外增加聚类权重，聚类不会改变 Risk Score。", "Color indicates product identity only. The distribution adds no cluster weight; clustering does not change Risk Score."))
            else: st.info(t("当前范围没有同时可计算两轴的记录，保留空图。", "No records with both scores; the plot remains empty."))
        # CC Pareto/report always recompute at CC grain; Model scores are never
        # summed or averaged into a CC score. Independent profile is retained.
        saved_cc = st.session_state.get("_tu_risk_poc_profiles", {}).get(f"{department}:CC")
        cc_profile=profile if grain=="CC" else RiskProfile(**saved_cc) if saved_cc else default_profile("CC")
        try:
            cc_rows,cc_audit=build_tu_risk(pqc,aql,voice,cases,scope,grain="CC",department=department,profile=cc_profile,registry=registry,season=season,inspection_only=population=="inspected")
        except ValueError:
            st.warning(t("CC 评分配置无效，CC 帕累托及报告暂留空；切换 CC 粒度修正参数。", "CC policy is invalid. CC Pareto/report remain empty; switch to CC to repair the policy."))
            return pd.DataFrame()
        st.session_state["_tu_risk_poc_cc_rows"]=cc_rows.to_dict("records")
        st.session_state["_tu_risk_poc_cc_audit"]=cc_audit
        return cc_rows
