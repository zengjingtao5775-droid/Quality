"""Independent TU/BME cluster settings and the shared sidebar navigation."""
from __future__ import annotations

import streamlit as st

from cluster_weights import DEFAULTS, apply_weights, current_weights, migrate_cluster_defaults, tu_cluster_profile
from tu_risk_reference import render_tu_scoring_reference


CLUSTER_SETTINGS_UI_VERSION = "2026-10-19-v5-pdf-policy-fields"


def render_quality_navigation(t):
    migrate_cluster_defaults(st.session_state)
    page = "cluster-settings" if st.query_params.get("view") == "cluster-settings" else "dashboard"
    def navigate(target):
        if target == "dashboard":
            st.query_params.pop("view", None)
        else:
            st.query_params["view"] = target
    with st.sidebar, st.container(key="quality_navigation"):
        st.markdown('<div class="quality-nav-brand-block"><div class="quality-nav-kicker">DECATHLON</div>'
                    '<div class="quality-nav-brand">NEA QUALITY</div>'
                    '<div class="quality-nav-subtitle">'+t("质量分析工作台", "Quality workspace")+'</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="quality-nav-section">'+t("工作空间", "WORKSPACE")+'</div>', unsafe_allow_html=True)
        with st.container(key="quality_nav_links"):
            for target, label, icon in (
                ("dashboard", t("质量看板", "Dashboard"), ":material/dashboard:"),
                ("cluster-settings", t("聚类权重设置", "Cluster Weights"), ":material/tune:"),
            ):
                st.button(label, icon=icon, key=f"quality_nav_{target}",
                          type="primary" if page == target else "secondary",
                          use_container_width=True, on_click=navigate, args=(target,),
                          help=t("当前页面", "Current page") if page == target else None)
    return page


def render_cluster_settings(t):
    st.header(t("聚类权重设置", "Cluster Weights"))
    st.caption(t("TU 与 BME 分别设置，仅用于聚类分析。KPI、CC 风险帕累托、疵点帕累托、SPC 与报告沿用原有计算口径。", "Separate TU and BME policies for cluster analysis only. KPI, CC risk Pareto, defect Pareto, SPC and reports retain their existing calculations."))
    st.info(t("保存后在当前会话生效，返回质量看板即可查看。新会话恢复默认值。", "Save to apply in this session, then return to the dashboard. A new session restores defaults."))
    tu, bme = st.tabs(["TU · Textile Unit", "BME · Bike Mobility"])
    for community, tab in (("TU", tu), ("BME", bme)):
        with tab, st.container(key=f"quality_cluster_settings_{community.lower()}"):
            current = current_weights(st.session_state, community)
            revision_key = f"_cluster_form_revision_{community}"
            revision = st.session_state.get(revision_key, 0)
            def control(col, key, label):
                return col.number_input(label, min_value=0., max_value=100., value=current[key], step=1., key=f"cluster_{community}_{revision}_{key}")
            with st.form(f"cluster_weights_{community}_{revision}", border=True):
                values = {}
                if community == "TU":
                    st.subheader(t("TU 聚类风险分", "TU cluster risk score"))
                    st.caption(t("Model 粒度 · Hugss · 有检验记录产品 · 全部 Strategy 季节，跟随主看板全局筛选。", "Model grain · Hugss · inspected products · all Strategy seasons, within the global dashboard selection."))
                    st.caption(t("与 2026-10-19 PDF 一致：Return Quantity 只用退货件数，平均量 μ 对应 50 分，1.8μ 对应 100 分。默认权重 40/10/50、50/50、80/20。", "Aligned with the 2026-10-19 PDF: Return Quantity uses returned units; mean μ = 50 points and 1.8μ = 100 points. Default weights: 40/10/50, 50/50, 80/20."))
                    a,b,c = st.columns(3)
                    for col, key, label in ((a,"client_weight",t("客户端 %", "Client %")), (b,"product_weight",t("产品 · Strategy %", "Product · Strategy %")), (c,"supplier_weight",t("供应商 %", "Supplier %"))):
                        values[key] = control(col, key, label)
                    st.markdown(t("**客户端内部权重**", "**Within client**"))
                    a,b = st.columns(2)
                    values["return_weight"] = control(a, "return_weight", "Return Qty %")
                    values["iv_weight"] = control(b, "iv_weight", "IV Qty %")
                    st.markdown(t("**供应商内部权重**", "**Within supplier**"))
                    a,b = st.columns(2)
                    values["pqc_weight"] = control(a, "pqc_weight", "PQC %")
                    values["aql_weight"] = control(b, "aql_weight", "AQL %")
                else:
                    st.subheader(t("FSD 聚类", "FSD clusters"))
                    st.caption(t("FQC 不良率与成品 Model RPM 的相对权重。", "Relative weights for FQC defect rate and finished-model RPM."))
                    a,b = st.columns(2)
                    values["fsd_fqc_weight"] = control(a, "fsd_fqc_weight", t("FQC 不良率 %", "FQC defect rate %"))
                    values["fsd_rpm_weight"] = control(b, "fsd_rpm_weight", "RPM %")
                    st.subheader(t("CMW 聚类", "CMW clusters"))
                    st.caption(t("有可靠分母的 IQC/FQC 使用下列权重；缺少分母的 PQC 保留仅按问题数量评分。", "IQC/FQC with valid denominators use these weights; PQC without a denominator retains volume-only scoring."))
                    a,b = st.columns(2)
                    values["cmw_rate_weight"] = control(a, "cmw_rate_weight", t("不良率 %", "Defect rate %"))
                    values["cmw_volume_weight"] = control(b, "cmw_volume_weight", t("问题数量 %", "Defect volume %"))
                st.caption(t("每组权重合计须为 100%。当前为试算参数，尚未校准。", "Each weight group must total 100%. These are uncalibrated trial parameters."))
                a,b = st.columns(2)
                save = a.form_submit_button(t("保存并应用", "Save and Apply"), type="primary", use_container_width=True)
                reset = b.form_submit_button(t("恢复默认", "Restore Defaults"), use_container_width=True)
            if reset:
                apply_weights(st.session_state, community, DEFAULTS[community])
                st.session_state[revision_key] = revision+1
                st.session_state[f"_cluster_saved_{community}"] = True
                st.rerun()
            if save:
                try:
                    apply_weights(st.session_state, community, values)
                    st.session_state[f"_cluster_saved_{community}"] = True
                except (ValueError, TypeError):
                    st.error(t("每组权重须合计 100%，请调整后保存。已应用的配置保持不变。", "Each group must total 100%. Adjust and save again; the applied policy is unchanged."))
            if st.session_state.pop(f"_cluster_saved_{community}", False):
                st.success(t(f"{community} 聚类权重已应用。", f"{community} cluster weights applied."))
            if community == "TU":
                render_tu_scoring_reference(t,tu_cluster_profile(st.session_state))
