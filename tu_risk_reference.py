"""Shared source-field and full piecewise scoring reference for TU views."""
from __future__ import annotations

import streamlit as st

from tu_risk_poc import default_profile

SOURCE_FIELDS = {
    "PQC": (("疵点个数", "defect_qty"), ("检验数量", "qty_inspected")),
    "AQL": (("检验结果 Result", "result_raw"), ("data_id", "record_id")),
    "Return Quantity": (("N0 Qty returned", "returned_now"),),
    "IV": (("PRODUCT QUANTITY", "iv_qty"), ("FEEDBACK No.", "case_id"),
           ("MODEL CODE", "model_code"), ("Before or after Sales", "responsibility_stage")),
}


def _piecewise(label, variable, warning, critical):
    return rf"""{label} = \begin{{cases}}
50\dfrac{{{variable}}}{{{warning}}}, & 0\le {variable}\le {warning} \\
50+50\dfrac{{{variable}-{warning}}}{{{critical}-{warning}}}, & {warning}<{variable}<{critical} \\
100, & {variable}\ge {critical}
\end{{cases}}"""


def render_tu_scoring_reference(t, profile=None):
    profile = profile or default_profile("Model")
    with st.expander(t("计算公式与原始字段", "Scoring formulas and raw fields"), expanded=False):
        st.caption(t("Raw 为原始列名，箭头后为程序字段。四项分别换成 0-100 分，再按当前权重合成。", "Raw names are original source columns; arrows identify application fields. Convert the four components to 0-100 before applying the current weights."))
        left, right = st.columns(2)
        sections = (
            (left,"PQC",r"\mathrm{PQC}(r)","r",f"{profile.pqc_warning_pct:g}\\%",f"{profile.pqc_critical_pct:g}\\%"),
            (right,"AQL",r"\mathrm{AQL}(q)","q",f"{profile.aql_warning_pct:g}\\%",f"{profile.aql_critical_pct:g}\\%"),
            (left,"Return Quantity",r"T(R)","R",r"\mu",f"{profile.return_critical_multiple:g}\\mu"),
            (right,"IV",r"\mathrm{IV}(I)","I",f"{profile.iv_warning:g}",f"{profile.iv_critical:g}"),
        )
        for column,name,label,variable,warning,critical in sections:
            with column:
                st.markdown(f"**{name}**")
                st.code("\n".join(f"{raw} → {canonical}" for raw,canonical in SOURCE_FIELDS[name]),language=None)
                if name == "PQC":
                    st.latex(rf"r=\dfrac{{\sum\mathrm{{defect\_qty}}+{profile.pqc_prior_defects:g}}}{{\sum\mathrm{{qty\_inspected}}+{profile.pqc_prior_samples:g}}}")
                elif name == "AQL":
                    st.caption(t("按 record_id 去重；未通过的有效首检记录数 / 全部有效首检记录数。重验后 PASS 仍计首检未通过；不按抽检件数作分母。", "Deduplicate record_id. Divide failed first-result records by valid first-result records. A re-check PASS remains a first-result failure; sampled units are not the denominator."))
                elif name == "Return Quantity":
                    st.caption(t(f"只看实际退货件数。50 分 = 同范围同粒度有效对象的平均退货量 μ；100 分 = {profile.return_critical_multiple:g}μ。明确零值参与均值；缺失或冲突值不补零。单选产品不重算参考均值。",f"Use actual returned units. 50 points = mean μ of valid same-scope, same-grain objects; 100 points = {profile.return_critical_multiple:g}μ. Include explicit zero; preserve missing/conflicting inputs. Selecting a product does not recalibrate the peer mean."))
                else:
                    st.caption(t("Before or after Sales 筛选 Before Sales；按 FEEDBACK No. + MODEL CODE 去重后汇总 PRODUCT QUANTITY。", "Filter Before or after Sales to Before Sales; deduplicate FEEDBACK No. + MODEL CODE, then sum PRODUCT QUANTITY."))
                st.latex(_piecewise(label,variable,warning,critical))
        st.markdown(t("**当前权重**", "**Current weights**"))
        st.caption(t(f"客户端 / Strategy / 供应商：{profile.client_weight:g}% / {profile.product_weight:g}% / {profile.supplier_weight:g}%；Return Quantity / IV：{profile.return_weight:g}% / {profile.iv_weight:g}%；PQC / AQL：{profile.pqc_weight:g}% / {profile.aql_weight:g}%。三组均可在权重设置页调整，每组合计 100%。", f"Client / Strategy / supplier: {profile.client_weight:g}% / {profile.product_weight:g}% / {profile.supplier_weight:g}%; Return Quantity / IV: {profile.return_weight:g}% / {profile.iv_weight:g}%; PQC / AQL: {profile.pqc_weight:g}% / {profile.aql_weight:g}%. All three groups are editable in Cluster Weights and must each total 100%."))
        st.caption(t("Strategy 名单字段：Supplier + Strategic Product Model code。按供应商与 Model 精确匹配，命中为 100 分，未命中为 0 分；系统未命中不代表正式业务身份已核实。", "Strategy list fields: Supplier + Strategic Product Model code. Match supplier and Model exactly: listed = 100, unlisted = 0. An unmatched system record does not verify the formal business identity."))
