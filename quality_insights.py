"""Source-grounded evidence and narratives shared by TU and BME.

Numbers are calculated here, rather than by the language model. Suggestions
are deliberately separate from observations and from recorded actions.
"""
import math
import re
import json

import pandas as pd

INSIGHTS_VERSION = "2026-10-07-v7-verified-ai"


def numeric(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def gate_totals(frame):
    """Use the same complete-denominator rule as the gate charts."""
    if frame.empty:
        return {"quantity": None, "denominator": None, "rate": None, "rows": 0}
    quantity = pd.to_numeric(frame.defect_qty, errors="coerce").sum(min_count=1)
    denominator = pd.to_numeric(frame.po_qty, errors="coerce")
    complete = bool(denominator.gt(0).all()) and pd.notna(quantity)
    total = denominator.sum(min_count=1)
    return {"quantity": numeric(quantity), "denominator": numeric(total) if complete else None,
            "rate": numeric(quantity / total) if complete else None, "rows": len(frame)}


def supplier_summary(community, supplier, product_type, gates, customer=None, iv=None, language="中文"):
    """One supplier row; never add percentages, mixed quantities or snapshots."""
    customer = customer or {}
    zh = language == "中文"
    row = {"Community": community, "供应商" if zh else "Supplier": supplier, "FG / CPT": product_type}
    row["RPM"] = f"{customer['rpm_now']:,.0f}" if numeric(customer.get("rpm_now")) is not None else "—"
    row["NQC (€)"] = f"{customer['nqc_now']:,.2f}" if numeric(customer.get("nqc_now")) is not None else "—"
    row["IV (案例)" if zh else "IV (cases)"] = f"{iv:,}" if iv is not None else "—"
    details = []
    for stage in ("IQC", "PQC", "FQC"):
        totals = gate_totals(gates.loc[gates.stage.eq(stage)])
        if totals["rate"] is not None:
            value = f"{totals['rate']:.2%}"
        elif totals["quantity"] is not None:
            unit = ("条" if zh else "records") if stage == "IQC" or (supplier == "CMW" and stage == "PQC") else ("疵点" if zh else "defects")
            value = f"{totals['quantity']:,.0f} {unit}"
        else:
            value = "—"
        row[stage] = value
        details.append({"community": community, "supplier": supplier, "stage": stage, **totals})
    return row, details


def _month(value):
    text = str(value)
    return text[:7] if re.match(r"\d{4}-\d{2}", text) else text


def chart_evidence(traces, y_format="", context=None):
    context = dict(context or {})
    kind = context.get("kind")
    lines = [t for t in traces if t.get("mode") in ("lines", "lines+markers") and t.get("type") == "scatter"]
    bars = [t for t in traces if t.get("type") == "bar"]
    if kind == "trend" or (not kind and len(lines) == 1 and not bars):
        trace = lines[0] if lines else {}
        pairs = [(str(x), numeric(y)) for x, y in zip(trace.get("x", []), trace.get("y", [])) if numeric(y) is not None]
        if not pairs:
            return {**context, "kind": "empty"}
        peak = max(pairs, key=lambda p: p[1])
        latest = pairs[-1]
        previous = pairs[-2] if len(pairs) > 1 else None
        evidence = {**context, "kind": "trend", "is_rate": "%" in y_format, "months": len(pairs),
                    "first": pairs[0], "latest": latest, "previous": previous, "peak": peak,
                    "change": latest[1] - previous[1] if previous else None,
                    "relative_change": (latest[1] / previous[1] - 1) if previous and previous[1] > 0 else None}
        monthly = context.get("monthly", [])
        if monthly:
            evidence["latest_volume"] = monthly[-1]
            evidence["previous_volume"] = monthly[-2] if len(monthly) > 1 else None
        cutoff = pd.to_datetime(context.get("cutoff"), errors="coerce")
        if pd.notna(cutoff) and _month(latest[0]) == str(cutoff)[:7]:
            evidence["partial_latest"] = cutoff.day < cutoff.days_in_month
        return evidence
    if kind == "pareto" or (not kind and bars and lines):
        bar = bars[0] if bars else {}
        names = context.get("names") or bar.get("labels") or bar.get("x", [])
        pairs = [(str(name), numeric(value)) for name, value in zip(names, bar.get("y", [])) if numeric(value) is not None]
        total = numeric(context.get("total"))
        if total is None and lines and lines[0].get("y"):
            endpoint = numeric(lines[0]["y"][-1])
            total = sum(p[1] for p in pairs) / endpoint if endpoint and endpoint > 0 else None
        return {**context, "kind": "pareto", "ranked": pairs[:5], "shown_total": sum(p[1] for p in pairs),
                "total": total, "shown_share": sum(p[1] for p in pairs) / total if total and total > 0 else None,
                "top_share": pairs[0][1] / total if pairs and total and total > 0 else None}
    if kind == "spc" or any(t.get("type") == "heatmap" for t in traces):
        return {**context, "kind": "spc"}
    if any(t.get("mode") == "markers" or t.get("mode") == "markers+text" for t in traces):
        points = []
        for trace in traces:
            for i, (x, y) in enumerate(zip(trace.get("x", []), trace.get("y", []))):
                if numeric(x) is None or numeric(y) is None:
                    continue
                labels = trace.get("text", [])
                label = labels[i] if isinstance(labels, list) and i < len(labels) else ""
                points.append({"label": str(label), "x": numeric(x), "y": numeric(y), "group": trace.get("name", "")})
        return {**context, "kind": "cluster", "objects": len(points),
                "high_x": max(points, key=lambda p: p["x"]) if points else None,
                "high_y": max(points, key=lambda p: p["y"]) if points else None}
    return {**context, "kind": kind or "other"}


def chart_signal(facts, language="中文"):
    """Color only measured signals; never infer improvement from sparse data."""
    zh = language == "中文"
    evidence = facts.get("evidence") or {}
    kind = evidence.get("kind")
    def signal(tone, chinese, english):
        return {"tone": tone, "label": chinese if zh else english}
    if facts.get("empty") or kind == "empty":
        return signal("neutral", "暂无数据", "Data unavailable")
    if kind == "trend":
        if evidence.get("partial_latest"):
            return signal("warning", "末月未完整 · 待对齐", "Partial month · align periods")
        delta = numeric(evidence.get("change"))
        if delta is None:
            return signal("neutral", "缺少可比上期", "No comparable prior period")
        if delta > 0:
            return signal("danger", "近期回升 · 优先复核", "Recent increase · review first")
        if delta < 0:
            current = evidence.get("latest_volume") or {}
            previous = evidence.get("previous_volume") or {}
            denominator = numeric(current.get("denominator"))
            previous_denominator = numeric(previous.get("denominator"))
            # Rates need both denominators. If coverage shrank, a lower rate
            # is a review signal rather than evidence of improvement.
            if evidence.get("is_rate") and (denominator is None or previous_denominator is None
                    or denominator <= 0 or previous_denominator <= 0 or denominator < previous_denominator):
                return signal("warning", "数值回落 · 覆盖待核实", "Lower value · verify coverage")
            if evidence.get("exception_only") or not evidence.get("is_rate"):
                return signal("warning", "记录减少 · 效果待核实", "Fewer issues · verify effectiveness")
            return signal("good", "问题率回落 · 继续验证", "Lower issue rate · verify improvement")
        return signal("neutral", "近期持平", "Unchanged recently")
    if kind == "pareto" and evidence.get("ranked"):
        return signal("danger", "首位问题 · 优先复核", "Leading issue · review first")
    if kind == "cluster":
        return signal("warning", "相对优先级 · 需追溯", "Relative priority · trace sources")
    if kind == "spc":
        return signal("warning", "过程信号 · 核对规格", "Process signal · check specifications")
    return signal("neutral", "按当前范围复核", "Review the current selection")


def inspection_signal(passed, total, language="中文"):
    """Distinguish recorded PASS/FAIL counts from corrective-action closure."""
    passed, total = numeric(passed), numeric(total)
    zh = language == "中文"
    if passed is None or total is None or total <= 0 or passed < 0 or passed > total:
        return {"tone": "neutral", "label": "结果待补齐" if zh else "Results unavailable", "not_passed": None}
    remaining = total - passed
    return {"tone": "danger" if remaining else "good",
            "label": (f"{remaining:,.0f} 条未通过" if remaining else "全部有效记录 PASS") if zh else
                     (f"{remaining:,.0f} non-PASS records" if remaining else "All valid records PASS"),
            "not_passed": remaining}


def build_chart_insight(facts, language="中文"):
    """Three compact, distinct layers: evidence, interpretation, next check."""
    zh = language == "中文"
    e = facts.get("evidence") or chart_evidence(facts.get("traces", []), facts.get("y_format", ""), facts.get("context"))
    kind = e.get("kind")
    if facts.get("empty") or kind == "empty":
        if "spc" in str(facts.get("id", "")).lower():
            return {"finding": "该供应商/工艺点尚无可用的连续过程测量记录。" if zh else "No continuous process measurements are available for this supplier/checkpoint.",
                    "interpretation": "无法建立控制限或评价稳定性，也不能把缺失记录解释为过程无异常。" if zh else "Control limits and stability cannot be assessed; missing records do not mean a process has no signals.",
                    "action": "补齐时点、供应商、工艺点、连续测量值、规格上下限及批次/量具信息，再按同一工艺点分析。" if zh else "Supply timestamps, supplier, checkpoint, consecutive measurements, specification limits and batch/gauge details, then analyze the same checkpoint."}
        reason = facts.get("summary") or ("当前筛选没有可用数据。" if zh else "No data is available for this selection.")
        return {"finding": reason,
                "interpretation": "缺失数据不能解释为零问题或稳定过程。" if zh else "Missing data does not mean zero defects or a stable process.",
                "action": "补齐该环节的日期、对象编码、检验数和问题数后再判断；先核对筛选是否排除了业务范围。" if zh else "Check the selection and supply dated object codes, inspection volumes and issue counts before assessing performance."}
    if kind == "trend":
        rate = e.get("is_rate", False)
        fmt = (lambda v: f"{v:.2%}") if rate else (lambda v: f"{v:,.2f}".rstrip("0").rstrip("."))
        latest, peak, first = e["latest"], e["peak"], e["first"]
        previous = e.get("previous")
        change = e.get("change")
        delta = f"{change * 100:+.2f} " + ("个百分点" if zh else "pp") if rate and change is not None else f"{change:+,.0f}" if change is not None else ""
        finding = f"最新 {_month(latest[0])} 为 {fmt(latest[1])}" if zh else f"Latest {_month(latest[0])}: {fmt(latest[1])}"
        if previous:
            finding += f"，较 {_month(previous[0])} {delta}" if zh else f", {delta} vs {_month(previous[0])}"
        finding += f"；峰值 {_month(peak[0])} 为 {fmt(peak[1])}。" if zh else f"; peak {_month(peak[0])}: {fmt(peak[1])}."
        rebound = previous and latest[1] < first[1] and latest[1] > previous[1]
        if rebound:
            interpretation = "首末下降，但最新一期反弹，不能判断为持续改善。" if zh else "Below the first period but rising recently; sustained improvement is not established."
        elif previous and latest[1] > previous[1]:
            interpretation = "近期问题信号回升，优先复核最新一期与峰值期的差异。" if zh else "The recent issue signal increased; compare the latest period with the peak period first."
        elif previous and latest[1] < previous[1]:
            interpretation = "最新一期回落；需确认检验覆盖或记录量未下降，再判断改善。" if zh else "The latest period declined; confirm inspection coverage or reporting did not shrink before attributing improvement."
        else:
            interpretation = "仅当前观测值不能证明长期稳定。" if zh else "Current observations alone do not establish long-term stability."
        volume = e.get("latest_volume") or {}
        numerator, denominator = numeric(volume.get("numerator")), numeric(volume.get("denominator"))
        if rate and denominator and numerator is not None:
            interpretation += f" 最新分子/分母 {numerator:,.0f}/{denominator:,.0f}。" if zh else f" Latest numerator/denominator: {numerator:,.0f}/{denominator:,.0f}."
        if e.get("exception_only"):
            interpretation += " 该源只有异常记录，不能据此推算总体不良率。" if zh else "This exception-only log cannot estimate the full population defect rate."
        if e.get("partial_latest"):
            interpretation += " 末月未完整，不能与完整月份直接比较。" if zh else "The latest month is partial and is not directly comparable with full months."
        action = f"复核 {_month(latest[0])} 与 {_month(peak[0])} 的主要问题、批次和处置记录；用相同分母及追溯范围验证措施效果。" if zh else f"Review leading issues, batches and disposition records in {_month(latest[0])} and {_month(peak[0])}; verify action effectiveness with comparable coverage and denominators."
        if e.get("exception_only"):
            action = f"复核 {_month(latest[0])} 的问题、来料批次及处置记录；补齐含合格批次的全部来料检验记录，再评价总体合格率。" if zh else f"Review {_month(latest[0])} issues, incoming batches and disposition records; obtain the complete incoming inspection log, including passing batches, before calculating an overall pass rate."
        elif e.get("partial_latest"):
            action = f"先将 {_month(latest[0])} 与上期相同天数、相同检验范围对齐，再复核主要问题及批次；保留完整月结果作后续验证。" if zh else f"Align {_month(latest[0])} with the same elapsed days and inspection scope in the previous period before reviewing defects/batches; retain full-month results for follow-up verification."
        return {"finding": finding, "interpretation": interpretation, "action": action}
    if kind == "pareto" and e.get("ranked"):
        first = e["ranked"][0]
        score = e.get("measure") == "risk_score"
        unit = ("风险分" if zh else "risk points") if score else e.get("unit", "个" if zh else "issues")
        share = f"{e['top_share']:.1%}" if e.get("top_share") is not None else "—"
        covered = f"{e['shown_share']:.1%}" if e.get("shown_share") is not None else "—"
        first_value = f"{first[1]:,.1f}" if score else f"{first[1]:,.0f}"
        finding = f"首位「{first[0]}」{first_value} {unit}，占全部范围 {share}；当前展示覆盖 {covered}。" if zh else f"Leading: {first[0]} ({first_value} {unit}), {share} of the full selection; shown coverage {covered}."
        interpretation = "风险分仅用于调查排序，占比是风险分份额，不是产品不良概率。" if zh and score else "Scores rank investigation priorities; shares are score contributions, not defect probabilities." if score else "累计线以当前范围全部问题为分母，未展示类别仍占据剩余份额。" if zh else "Cumulative shares use the full selected population, including categories outside the displayed subset."
        if not score and e.get("shown_share") is not None and e["shown_share"] < .8:
            interpretation += " 问题较分散，不能只处理首位类别。" if zh else "Issues are spread across categories; addressing the leader alone will leave substantial exposure."
        action = f"先按「{first[0]}」核对对应 CC/Model、批次和原始记录，再与客户退货或 IV 交叉验证；不能直接据此断定根因。" if zh else f"Start with {first[0]}: trace affected codes/models, batches and source records; cross-check returns or IV before assigning a cause."
        if e.get("traceability_missing"):
            action = f"先按「{first[0]}」复核材料、来料批次、供方及处置结果；当前没有 CC/Model 链路，需补齐追溯后再关联成品风险。" if zh else f"Review {first[0]} by material, incoming batch, vendor and disposition; obtain the missing CC/Model traceability before linking it to finished-product risk."
        if e.get("composite_descriptions"):
            interpretation += " 原始组合描述不能拆分为各单项疵点数量。" if zh else "Composite source descriptions cannot be split into quantities for individual defects."
        if e.get("category_type") == "product_family":
            action = f"先复核「{first[0]}」产品族的拒收批次及同期生产量，再补充具体疵点名称，避免把产品族当作缺陷根因。" if zh else f"Review rejected batches and production volume for {first[0]}, then capture specific defect names; a product family is not a defect cause."
        return {"finding": finding, "interpretation": interpretation, "action": action}
    if kind == "cluster":
        hi_x, hi_y = e.get("high_x"), e.get("high_y")
        finding = facts.get("summary") or (f"当前展示 {e.get('objects', 0)} 个对象。" if zh else f"The selection shows {e.get('objects', 0)} objects.")
        if hi_x and hi_y:
            finding += f" 横轴最高：{hi_x['label'] or hi_x['group']}；纵轴最高：{hi_y['label'] or hi_y['group']}。" if zh else f" Highest x: {hi_x['label'] or hi_x['group']}; highest y: {hi_y['label'] or hi_y['group']}."
        return {"finding": finding,
                "interpretation": "横纵轴同时偏高的对象优先复核；不同轴的最高对象不一定相同。分数或聚类位置不能直接证明共同根因。" if zh else "Prioritize objects elevated on both axes; axis leaders can differ. Cluster positions or scores do not establish a common cause.",
                "action": "逐对象核对检验量、退货/销量及编码映射；区分样本不足、生产问题和客户端信号，再选择对应批次复盘。" if zh else "Check each object's inspection volume, returns/sales and exact code mapping; distinguish sparse sampling from factory and customer signals before investigating its batches."}
    if kind == "spc":
        return {"finding": facts.get("summary") or ("过程图使用独立的供应商及工艺点筛选。" if zh else "Process charts use independent supplier and checkpoint filters."),
                "interpretation": "规格超限与控制图异常是两类信号；没有有效规格或足够观测时，不判断能力或稳定性。" if zh else "Specification breaches and control-chart signals are distinct; capability or stability requires valid specifications and adequate observations.",
                "action": "先复核异常时点的批次、设备设定和量具记录，再按同一工艺点连续复测；不得仅凭信号认定根因或拒收。" if zh else "Review batches, settings and gauge records at signal times, then repeat measurements at the same checkpoint; a signal alone does not establish cause or rejection."}
    return {"finding": facts.get("summary") or ("图表反映当前筛选内的记录结构。" if zh else "The chart shows records within the current selection."),
            "interpretation": "先确认样本、单位及追溯范围一致，数量变化不能直接解释为质量变化。" if zh else "Check consistent samples, units and traceability; count changes alone do not establish quality changes.",
            "action": "复核主要对象的原始检验记录与处置状态，并补齐可比的检验分母。" if zh else "Review source inspections and disposition status for leading objects and obtain comparable inspection denominators."}


def validate_ai_response(response, chart_ids, allowed_ccs, source_facts=None):
    """Require three recommendations and substantive per-chart layers."""
    if not isinstance(response, dict):
        raise ValueError("Expected AI JSON object")
    actions = response.get("actions")
    if not isinstance(actions, list) or len(actions) != 3:
        raise ValueError("Exactly three report actions required")
    allowed = set(str(cc) for cc in allowed_ccs)
    number_pattern = r"\d+(?:[.,]\d+)*%?"
    factual_numbers = set(re.findall(number_pattern, json.dumps(source_facts or {}, ensure_ascii=False)))

    def check_numbers(text):
        qualitative = text
        for cc in sorted(allowed, key=len, reverse=True):
            qualitative = qualitative.replace(cc, "")
        new_numbers = set(re.findall(number_pattern, qualitative)) - factual_numbers
        if new_numbers:
            raise ValueError("AI introduced unsupported numbers: " + ", ".join(sorted(new_numbers)))
    normalized = []
    for action in actions:
        text = str(action.get("action", "")).strip() if isinstance(action, dict) else ""
        codes = action.get("priority_ccs", []) if isinstance(action, dict) else []
        if not text or not isinstance(codes, list) or any(str(cc) not in allowed for cc in codes):
            raise ValueError("Invalid report action scope")
        # Narrative contains no new numeric claim; data tables own all values.
        check_numbers(text)
        normalized.append({"action": text[:600], "priority_ccs": codes})
    charts = response.get("charts", [])
    if not isinstance(charts, list) or len(charts) != len(chart_ids):
        raise ValueError("One insight per chart required")
    by_id = {}
    for chart in charts:
        if not isinstance(chart, dict) or chart.get("id") in by_id:
            raise ValueError("Duplicate or invalid chart")
        if any(not isinstance(chart.get(k), str) or len(chart[k].strip()) < 12 for k in ("interpretation", "action")):
            raise ValueError("Chart insight lacks interpretation/action")
        check_numbers(chart["interpretation"] + " " + chart["action"])
        by_id[chart["id"]] = {k: chart[k].strip()[:900] for k in ("interpretation", "action")}
    if set(by_id) != set(chart_ids):
        raise ValueError("Chart scope mismatch")
    return {"actions": normalized, "charts": by_id}


def validate_with_repair(content, chart_ids, allowed_ccs, source_facts, repair):
    """Permit one provider correction, while retaining all factual checks."""
    try:
        return validate_ai_response(json.loads(content), chart_ids, allowed_ccs, source_facts)
    except (ValueError, TypeError) as error:
        corrected = repair(content, str(error))
        # No further retry and no partially validated response reaches the UI.
        return validate_ai_response(json.loads(corrected), chart_ids, allowed_ccs, source_facts)
