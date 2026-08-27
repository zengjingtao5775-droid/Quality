from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


BME_QUALITY_LOGIC_VERSION = "2026-08-27-v13"


EVENT_COLUMNS = [
    "community",
    "supplier",
    "supplier_code",
    "stage",
    "date",
    "event_timestamp",
    "order_po",
    "trace_number",
    "model_item_code",
    "item_name",
    "material_supplier",
    "family",
    "process",
    "issue_driver",
    "inspected_qty",
    "defect_qty",
    "defect_rate",
    "result",
    "spec_text",
    "spec_low",
    "spec_high",
    "measured_value",
    "unit",
    "severity",
    "status",
    "status_available",
    "workflow_end_date",
    "data_quality_flag",
    "comments",
    "metric_scope",
    "source_file",
    "source_sheet",
    "source_row",
    "is_alert",
    "alert_reason",
]


def _empty_events() -> pd.DataFrame:
    return pd.DataFrame(columns=EVENT_COLUMNS)


def _read_excel(path: Path, **kwargs) -> pd.DataFrame:
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    return pd.read_excel(path, engine=engine, **kwargs)


def _clean_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [
        re.sub(r"\s+", "", str(value)).replace("（", "(").replace("）", ")")
        for value in frame.columns
    ]
    return frame


def _col(frame: pd.DataFrame, *names: str, default: object = "") -> pd.Series:
    normalized = {
        re.sub(r"\s+", "", str(column)).replace("（", "(").replace("）", ")"): column
        for column in frame.columns
    }
    for name in names:
        key = re.sub(r"\s+", "", name).replace("（", "(").replace("）", ")")
        if key in normalized:
            return frame[normalized[key]]
        for normalized_name, column in normalized.items():
            if normalized_name.startswith(key + ".") or key in normalized_name:
                return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def _number(series: pd.Series, default: float | None = 0.0) -> pd.Series:
    result = pd.to_numeric(series, errors="coerce")
    return result if default is None else result.fillna(default)


def _date(series: pd.Series) -> pd.Series:
    values = series.copy()
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.to_datetime(values, errors="coerce", format="mixed", dayfirst=True)
    serial_mask = numeric.between(20000, 80000, inclusive="both")
    result.loc[serial_mask] = pd.to_datetime(
        numeric.loc[serial_mask], unit="D", origin="1899-12-30", errors="coerce"
    )
    roc = values.fillna("").astype(str).str.extract(r"(?<!\d)(?P<year>\d{2,3})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日")
    roc_mask = roc["year"].notna()
    if roc_mask.any():
        roc_dates = pd.to_datetime(
            (pd.to_numeric(roc.loc[roc_mask, "year"]) + 1911).astype(int).astype(str)
            + "-" + roc.loc[roc_mask, "month"].str.zfill(2)
            + "-" + roc.loc[roc_mask, "day"].str.zfill(2),
            errors="coerce",
        )
        result.loc[roc_mask] = roc_dates
    return result


def _iso_week_date(year: pd.Series, week: pd.Series) -> pd.Series:
    year_number = pd.to_numeric(year, errors="coerce")
    week_number = pd.to_numeric(week.astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    labels = year_number.astype("Int64").astype(str) + "-W" + week_number.astype("Int64").astype(str).str.zfill(2) + "-1"
    return pd.to_datetime(labels, format="%G-W%V-%u", errors="coerce")


def _text(series: pd.Series, default: str = "") -> pd.Series:
    result = series.fillna("").astype(str).str.strip()
    return result.replace({"nan": "", "None": ""}).where(result.ne(""), default)


def _identifier(series: pd.Series, default: str = "") -> pd.Series:
    """Keep source identifiers readable when Excel coerces them to floats."""
    return _text(series, default).str.replace(r"(?<=\d)\.0$", "", regex=True)


def _negative(series: pd.Series) -> pd.Series:
    text = _text(series).str.upper()
    return text.str.fullmatch(r"NO", na=False) | text.str.contains(
        r"NOK|FAIL|FAILED|NG|REJECT|BLOCK|不合格|不通过|拒收|退回|报废|超差",
        regex=True,
        na=False,
    )


def _positive(series: pd.Series) -> pd.Series:
    text = _text(series).str.upper()
    return text.str.fullmatch(r"OK|PASS|PASSED|合格|通过|已通过|良品", na=False)


def _parse_range(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    lows = pd.Series(np.nan, index=series.index, dtype=float)
    highs = pd.Series(np.nan, index=series.index, dtype=float)
    for index, value in series.fillna("").astype(str).items():
        text = value.strip().replace("～", "~").replace("—", "-").replace("–", "-")
        text = re.sub(r"(?<=\d)-(?=\d)", "~", text)
        numbers = [float(number) for number in re.findall(r"-?\d+(?:\.\d+)?", text)]
        if len(numbers) >= 2:
            lows.at[index], highs.at[index] = min(numbers[:2]), max(numbers[:2])
        elif len(numbers) == 1 and any(token in text for token in [">", "≥"]):
            lows.at[index] = numbers[0]
        elif len(numbers) == 1 and any(token in text for token in ["<", "≤"]):
            highs.at[index] = numbers[0]
    return lows, highs


def _status(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    raw = _text(series)
    upper = raw.str.upper()
    closed = upper.str.contains(r"CLOSED|COMPLETE|DONE|已通过|已完成|结案|关闭|合格", regex=True)
    progress = upper.str.contains(r"PROCESS|PENDING|确认|处理中|返工|等待|申请", regex=True)
    open_mask = upper.str.contains(r"OPEN|未结案|未关闭|待处理|退回", regex=True)
    mapped = pd.Series("Status unavailable", index=series.index, dtype=object)
    mapped.loc[progress] = "In progress"
    mapped.loc[open_mask] = "Open"
    mapped.loc[closed] = "Closed"
    return mapped, raw.ne("")


def _frame(**columns: object) -> pd.DataFrame:
    frame = pd.DataFrame(columns)
    for column in EVENT_COLUMNS:
        if column not in frame:
            frame[column] = np.nan
    frame = frame[EVENT_COLUMNS]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["event_timestamp"] = pd.to_datetime(frame["event_timestamp"], errors="coerce")
    frame["workflow_end_date"] = pd.to_datetime(frame["workflow_end_date"], errors="coerce")
    for column in ["inspected_qty", "defect_qty", "defect_rate", "spec_low", "spec_high", "measured_value"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["is_alert"] = frame["is_alert"].fillna(False).astype(bool)
    frame["status_available"] = frame["status_available"].fillna(False).astype(bool)
    return frame


def _normalize_po(series: pd.Series) -> pd.Series:
    return (
        _text(series)
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\s+", "", regex=True)
        .str.upper()
    )


def spc_run_rule_flags(values: pd.Series, center: float, ucl: float, lcl: float) -> pd.DataFrame:
    """Return auditable Western-Electric-style signals used by the BME page."""
    values = pd.to_numeric(values, errors="coerce").reset_index(drop=True)
    result = pd.DataFrame(index=values.index)
    result["beyond_3sigma"] = values.gt(ucl) | values.lt(lcl)
    side = np.sign(values - center).fillna(0).astype(int)
    result["eight_one_side"] = False
    result["six_trend"] = False
    for end in range(7, len(values)):
        window = side.iloc[end - 7:end + 1]
        if (window.eq(1).all() or window.eq(-1).all()):
            # Mark the point that completes the rule, rather than painting the
            # whole window as eight separate special-cause events.
            result.loc[end, "eight_one_side"] = True
    for end in range(5, len(values)):
        window = values.iloc[end - 5:end + 1]
        delta = window.diff().dropna()
        if delta.gt(0).all() or delta.lt(0).all():
            result.loc[end, "six_trend"] = True
    result["signal"] = result.any(axis=1)
    return result


def build_imr_chart_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    """Build an I-MR chart without turning data-entry suspects into SPC signals."""
    chart = frame.copy().sort_values(["event_timestamp", "date", "source_row"], na_position="last")
    chart["value"] = pd.to_numeric(chart["measured_value"], errors="coerce")
    chart = chart[chart["value"].notna()].reset_index(drop=True)
    chart["is_data_quality_suspect"] = chart.get(
        "data_quality_flag", pd.Series("", index=chart.index)
    ).fillna("").astype(str).ne("")
    estimate = chart[~chart["is_data_quality_suspect"]].copy()
    if len(estimate) < 2:
        return chart, {}
    center = float(estimate["value"].mean())
    mrbar = float(estimate["value"].diff().abs().dropna().mean())
    ucl, lcl = center + 2.66 * mrbar, center - 2.66 * mrbar
    chart["moving_range"] = np.nan
    chart.loc[estimate.index, "moving_range"] = estimate["value"].diff().abs().to_numpy()
    for column in ["beyond_3sigma", "eight_one_side", "six_trend", "signal"]:
        chart[column] = False
    estimate_flags = spc_run_rule_flags(estimate["value"], center, ucl, lcl)
    chart.loc[estimate.index, estimate_flags.columns] = estimate_flags.to_numpy()
    limits = {"center": center, "ucl": ucl, "lcl": lcl, "mrbar": mrbar, "mr_ucl": 3.267 * mrbar}
    stable = not bool(estimate_flags["signal"].any()) and not bool(
        chart.loc[estimate.index, "moving_range"].gt(limits["mr_ucl"]).any()
    )
    limits["stable"] = stable
    low = pd.to_numeric(estimate.get("spec_low"), errors="coerce").dropna()
    high = pd.to_numeric(estimate.get("spec_high"), errors="coerce").dropna()
    if stable and len(estimate) >= 25 and estimate["value"].nunique() >= 5 and not low.empty and not high.empty:
        std = float(estimate["value"].std(ddof=1))
        if std > 0:
            limits["ppk"] = min((float(high.median()) - center) / (3 * std), (center - float(low.median())) / (3 * std))
    return chart, limits


def build_p_chart_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    chart = frame.copy().sort_values("date")
    chart["n"] = pd.to_numeric(chart["inspected_qty"], errors="coerce")
    chart["nc"] = pd.to_numeric(chart["defect_qty"], errors="coerce")
    chart = chart[chart["n"].gt(0) & chart["nc"].ge(0)].reset_index(drop=True)
    if chart.empty:
        return chart, {}
    pbar = float(chart["nc"].sum() / chart["n"].sum())
    sigma = np.sqrt(pbar * (1 - pbar) / chart["n"])
    chart["rate"] = chart["nc"] / chart["n"]
    chart["ucl"] = np.minimum(1.0, pbar + 3 * sigma)
    chart["lcl"] = np.maximum(0.0, pbar - 3 * sigma)
    chart = pd.concat([chart, spc_run_rule_flags(chart["rate"], pbar, chart["ucl"], chart["lcl"])], axis=1)
    return chart, {"center": pbar, "stable": not bool(chart["signal"].any())}


def build_xbar_r_chart_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    """Build an Xbar-R chart for complete consecutive subgroups of five."""
    values = frame.copy().sort_values(["date", "order_po", "source_row"], na_position="last")
    values["value"] = pd.to_numeric(values["measured_value"], errors="coerce")
    values = values[values["value"].notna()].copy()
    values["within_batch"] = values.groupby(["source_sheet", "order_po"], dropna=False).cumcount()
    values["subgroup"] = values["source_sheet"].astype(str) + " · " + values["order_po"].astype(str) + " · " + (values["within_batch"] // 5 + 1).astype(str)
    grouped = values.groupby("subgroup", sort=False).agg(date=("date", "min"), mean=("value", "mean"), range=("value", lambda x: x.max() - x.min()), n=("value", "size")).reset_index()
    chart = grouped[grouped["n"].eq(5)].reset_index(drop=True)
    if chart.empty:
        return chart, {"incomplete_groups": float((~grouped["n"].eq(5)).sum())}
    center, rbar = float(chart["mean"].mean()), float(chart["range"].mean())
    limits = {
        "center": center, "ucl": center + 0.577 * rbar, "lcl": center - 0.577 * rbar,
        "rbar": rbar, "r_ucl": 2.114 * rbar, "r_lcl": 0.0,
        "incomplete_groups": float((~grouped["n"].eq(5)).sum()),
    }
    chart = pd.concat([chart, spc_run_rule_flags(chart["mean"], center, limits["ucl"], limits["lcl"])], axis=1)
    chart["range_signal"] = chart["range"].gt(limits["r_ucl"]) | chart["range"].lt(limits["r_lcl"])
    stable = not bool(chart["signal"].any()) and not bool(chart["range_signal"].any())
    limits["stable"] = stable
    if stable and len(values) >= 25:
        std = float(values["value"].std(ddof=1))
        if std > 0:
            limits["ppl"] = (center - 200.0) / (3 * std)
    return chart, limits


def summarize_spc_process_risk(method: str, frame: pd.DataFrame) -> dict[str, object]:
    """Summarize one SPC sequence without mixing process signals with specifications."""
    summary: dict[str, object] = {
        "measurement_count": 0,
        "spc_observation_count": 0,
        "signal_count": 0,
        "signal_rate": 0.0,
        "specification_breaches": 0,
        "specification_rate": 0.0,
        "has_specification": False,
        "limits_available": False,
        "stable": None,
        "capability": None,
        "attention_rate": 0.0,
    }
    if frame.empty:
        return summary

    if method.startswith("imr"):
        chart, limits = build_imr_chart_data(frame)
        valid_chart = chart[
            ~chart.get(
                "is_data_quality_suspect", pd.Series(False, index=chart.index)
            ).fillna(False)
        ].copy()
        mr_signal = valid_chart.get(
            "moving_range", pd.Series(np.nan, index=valid_chart.index)
        ).gt(float(limits.get("mr_ucl", np.inf)))
        signal = valid_chart.get(
            "signal", pd.Series(False, index=valid_chart.index)
        ).fillna(False) | mr_signal
        measured = pd.to_numeric(
            valid_chart.get("value", pd.Series(np.nan, index=valid_chart.index)),
            errors="coerce",
        )
        low = pd.to_numeric(
            valid_chart.get("spec_low", pd.Series(np.nan, index=valid_chart.index)),
            errors="coerce",
        )
        high = pd.to_numeric(
            valid_chart.get("spec_high", pd.Series(np.nan, index=valid_chart.index)),
            errors="coerce",
        )
    elif method == "pchart":
        chart, limits = build_p_chart_data(frame)
        valid_chart = chart.copy()
        signal = valid_chart.get(
            "signal", pd.Series(False, index=valid_chart.index)
        ).fillna(False)
        measured = pd.Series(dtype=float)
        low = pd.Series(dtype=float)
        high = pd.Series(dtype=float)
    else:
        chart, limits = build_xbar_r_chart_data(frame)
        valid_chart = chart.copy()
        signal = valid_chart.get(
            "signal", pd.Series(False, index=valid_chart.index)
        ).fillna(False) | valid_chart.get(
            "range_signal", pd.Series(False, index=valid_chart.index)
        ).fillna(False)
        measured = pd.to_numeric(
            frame.get("measured_value", pd.Series(np.nan, index=frame.index)),
            errors="coerce",
        )
        low = pd.to_numeric(
            frame.get("spec_low", pd.Series(np.nan, index=frame.index)),
            errors="coerce",
        )
        high = pd.to_numeric(
            frame.get("spec_high", pd.Series(np.nan, index=frame.index)),
            errors="coerce",
        )

    measurement_count = int(measured.notna().sum())
    spc_observation_count = int(len(valid_chart))
    signal_count = int(signal.sum())
    has_specification = bool(low.notna().any() or high.notna().any())
    outside_specification = (
        (low.notna() & measured.lt(low))
        | (high.notna() & measured.gt(high))
    ) if measurement_count else pd.Series(dtype=bool)
    specification_breaches = int(outside_specification.sum())
    signal_rate = signal_count / spc_observation_count if spc_observation_count else 0.0
    specification_rate = specification_breaches / measurement_count if measurement_count else 0.0
    capability = limits.get("ppk", limits.get("ppl"))

    summary.update({
        "measurement_count": measurement_count,
        "spc_observation_count": spc_observation_count,
        "signal_count": signal_count,
        "signal_rate": float(signal_rate),
        "specification_breaches": specification_breaches,
        "specification_rate": float(specification_rate),
        "has_specification": has_specification,
        "limits_available": "stable" in limits,
        "stable": limits.get("stable"),
        "capability": float(capability) if capability is not None else None,
        "attention_rate": float(max(signal_rate, specification_rate)),
    })
    return summary


def build_spc_model_component_risk(
    frame: pd.DataFrame,
    summaries: dict[str, dict[str, object]] | None = None,
) -> pd.DataFrame:
    """Map CMW torque risk by model and exact source component name.

    Cross-model recurrence is observational: a component is marked recurring
    only when the current data contains a risky homogeneous sequence for the
    same exact source component name in more than one model. It is not a
    prediction that the issue will occur in another model.
    """
    columns = [
        "full_label", "model_code", "model_name", "model_display",
        "component", "spec_low", "spec_high", "unit", "risk_key",
        "risk_rank", "attention_rate", "measurement_count", "signal_count",
        "signal_rate", "specification_breaches", "specification_rate",
        "capability", "affected_model_count", "affected_models",
        "other_models", "recurs_across_models",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    group_columns = [
        "model_item_code", "item_name", "process", "spec_low", "spec_high", "unit"
    ]
    for keys, group in frame.groupby(group_columns, dropna=False):
        if len(group) < 5:
            continue
        model_code = str(keys[0]).strip() if pd.notna(keys[0]) else ""
        model_name = str(keys[1]).strip() if pd.notna(keys[1]) else ""
        model_display = model_name or model_code or "Unrecorded model"
        component = str(keys[2]).strip() if pd.notna(keys[2]) else "Unrecorded component"
        full_label = (
            f"CMW · I-MR · {model_display} · {component} · "
            f"{keys[3]}–{keys[4]} {keys[5]}"
        )
        summary = (
            summaries[full_label]
            if summaries is not None and full_label in summaries
            else summarize_spc_process_risk("imr", group)
        )
        specification_breaches = int(summary["specification_breaches"])
        signal_count = int(summary["signal_count"])
        if specification_breaches > 0:
            risk_key = "specification"
            risk_rank = 0
        elif signal_count > 0 or summary["stable"] is False:
            risk_key = "spc"
            risk_rank = 1
        else:
            continue
        rows.append({
            "full_label": full_label,
            "model_code": model_code,
            "model_name": model_name,
            "model_display": model_display,
            "component": component,
            "spec_low": keys[3],
            "spec_high": keys[4],
            "unit": keys[5],
            "risk_key": risk_key,
            "risk_rank": risk_rank,
            "attention_rate": float(summary["attention_rate"]),
            "measurement_count": int(summary["measurement_count"]),
            "signal_count": signal_count,
            "signal_rate": float(summary["signal_rate"]),
            "specification_breaches": specification_breaches,
            "specification_rate": float(summary["specification_rate"]),
            "capability": summary["capability"],
        })

    if not rows:
        return pd.DataFrame(columns=columns)
    risk = pd.DataFrame(rows)
    risk = risk.sort_values(
        ["risk_rank", "attention_rate", "model_display", "component"],
        ascending=[True, False, True, True],
    ).reset_index(drop=True)

    component_models: dict[str, list[tuple[str, str]]] = {}
    for component, component_rows in risk.groupby("component", sort=False):
        model_rows = (
            component_rows.sort_values(
                ["risk_rank", "attention_rate"], ascending=[True, False]
            )[["model_code", "model_display"]]
            .drop_duplicates("model_code")
        )
        component_models[str(component)] = [
            (str(row.model_code), str(row.model_display))
            for row in model_rows.itertuples(index=False)
        ]

    affected_counts: list[int] = []
    affected_labels: list[str] = []
    other_labels: list[str] = []
    for row in risk.itertuples(index=False):
        models = component_models[str(row.component)]
        affected_counts.append(len(models))
        affected_labels.append("、".join(label for _, label in models))
        others = [label for code, label in models if code != str(row.model_code)]
        other_labels.append("、".join(others))
    risk["affected_model_count"] = affected_counts
    risk["affected_models"] = affected_labels
    risk["other_models"] = other_labels
    risk["recurs_across_models"] = risk["affected_model_count"].gt(1)
    return risk[columns]


def _finalize_event_flags(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    measured = pd.to_numeric(frame["measured_value"], errors="coerce")
    low = pd.to_numeric(frame["spec_low"], errors="coerce")
    high = pd.to_numeric(frame["spec_high"], errors="coerce")
    outside = (low.notna() & measured.lt(low)) | (high.notna() & measured.gt(high))
    explicit_failure = _negative(frame["result"])
    defects = pd.to_numeric(frame["defect_qty"], errors="coerce").fillna(0).gt(0)
    frame["is_alert"] = frame["is_alert"].fillna(False) | outside | explicit_failure | defects
    frame["alert_reason"] = _text(frame["alert_reason"])
    frame.loc[outside & frame["alert_reason"].eq(""), "alert_reason"] = "Measured value outside source specification"
    frame.loc[explicit_failure & frame["alert_reason"].eq(""), "alert_reason"] = "Source result is nonconforming"
    frame.loc[defects & frame["alert_reason"].eq(""), "alert_reason"] = "Source records nonconformity"
    return frame


def _load_fsd(root: Path) -> list[pd.DataFrame]:
    path = root / "BME Database" / "FSD" / "FSD P2 data input.xlsx"
    if not path.exists():
        return []
    frames: list[pd.DataFrame] = []

    iqc = _clean_columns(_read_excel(path, sheet_name="IQC"))
    if not iqc.empty:
        checked = ["外观不良", "尺寸不良", "牙纹不良", "混装/漏装", "功性能"]
        issue = iqc.apply(
            lambda row: " / ".join(name for name in checked if str(row.get(name, "")).strip() in {"☑", "√", "1", "True"})
            or str(row.get("异常原因", "")).strip(),
            axis=1,
        )
        status, status_available = _status(_col(iqc, "处理状态", "结案日期"))
        frames.append(_frame(
            community="BME", supplier="FSD", supplier_code="FSD", stage="IQC",
            date=_date(_col(iqc, "日期")), order_po=_text(_col(iqc, "采购单号")),
            model_item_code=_text(_col(iqc, "料号")), item_name=_text(_col(iqc, "物料名称")),
            family=_text(_col(iqc, "车种")), process="Incoming material",
            issue_driver=issue, inspected_qty=_number(_col(iqc, "数量"), None),
            defect_qty=_number(_col(iqc, "不良笔数"), None), defect_rate=np.nan,
            result=_text(_col(iqc, "判定")), spec_text=_text(_col(iqc, "物料规格")),
            spec_low=np.nan, spec_high=np.nan, measured_value=np.nan, unit="",
            severity="Medium", status=status, status_available=status_available,
            metric_scope="Exception log; pass rate unavailable", source_file=str(path.relative_to(root)),
            source_sheet="IQC", source_row=iqc.index + 2, is_alert=True,
            alert_reason=_text(pd.Series(issue, index=iqc.index), "Incoming nonconformity record"),
        ))

    pqc = _clean_columns(_read_excel(path, sheet_name="PQC"))
    if not pqc.empty:
        spec = _col(pqc, "范围")
        low, high = _parse_range(spec)
        measured = _number(_col(pqc, "首件值"), None)
        outside = (low.notna() & measured.lt(low)) | (high.notna() & measured.gt(high))
        result = _text(_col(pqc, "检验结果"))
        frames.append(_frame(
            community="BME", supplier="FSD", supplier_code="FSD", stage="PQC",
            date=_date(_col(pqc, "检验日期")), order_po="",
            model_item_code=_text(_col(pqc, "规格")), item_name=_text(_col(pqc, "产品名称")),
            family="", process=_text(_col(pqc, "检验项目")), issue_driver=_text(_col(pqc, "检验内容")),
            inspected_qty=1, defect_qty=(outside | _negative(result)).astype(int), defect_rate=np.nan,
            result=result, spec_text=_text(spec), spec_low=low, spec_high=high,
            measured_value=measured, unit=_text(_col(pqc, "检验工具")), severity="High",
            status="Status unavailable", status_available=False, metric_scope="First-piece measurement",
            source_file=str(path.relative_to(root)), source_sheet="PQC", source_row=pqc.index + 2,
            is_alert=outside | _negative(result), alert_reason="",
        ))

    for sheet_name, stage, header in [("AQL inspecation", "AQL", 2), ("DKL inspection", "DKL", 3)]:
        raw = _clean_columns(_read_excel(path, sheet_name=sheet_name, header=header))
        if stage == "DKL":
            raw = raw[_text(_col(raw, "PartsSupplier")).str.upper().eq("FSD")].copy()
        if raw.empty:
            continue
        inspected = _number(_col(raw, "InspectedQty检验数量", "Nbrofframeforkcontroled"), None)
        nc = _number(_col(raw, "NCQty不良数量", "NCQty"), None)
        result = _text(
            _col(raw, "FinalDecisionofSupplier决定")
            if stage == "AQL"
            else _col(raw, "FinalDecisionofPL")
        )
        control_start = 15 if stage == "AQL" else 16
        control_end = 36 if stage == "AQL" else 46
        control_columns = list(raw.columns[control_start:control_end])
        issue = raw[control_columns].apply(
            lambda row: " / ".join(str(column).split("\n")[0] for column, value in row.items() if str(value).upper().strip() == "NOK"),
            axis=1,
        ) if control_columns else pd.Series("", index=raw.index)
        has_alert = nc.fillna(0).gt(0) | _negative(result) | issue.ne("")
        frames.append(_frame(
            community="BME", supplier="FSD", supplier_code="FSD", stage=stage,
            date=_iso_week_date(_col(raw, "Year年", "Year"), _col(raw, "Week周", "Week")),
            order_po=_text(_col(raw, "P.O.forFrameorBike订单号")),
            model_item_code=_text(_col(raw, "ItemforFrameforkonly")),
            item_name=_text(_col(raw, "Name(formularlinkwithDATABASE)车种名", "Modelname")),
            family=_text(_col(raw, "Family")), process=_text(_col(raw, "Range范围", "FrameFork")),
            issue_driver=_text(issue, "No recorded NOK control"), inspected_qty=inspected,
            defect_qty=nc, defect_rate=np.where(inspected.fillna(0).gt(0), nc / inspected, np.nan),
            result=result, spec_text="", spec_low=np.nan, spec_high=np.nan, measured_value=np.nan,
            unit="pcs", severity=np.where(has_alert, "High", "Low"), status="Status unavailable",
            status_available=False, metric_scope="Inspection record",
            source_file=str(path.relative_to(root)), source_sheet=sheet_name, source_row=raw.index + header + 2,
            is_alert=has_alert, alert_reason=np.where(has_alert, "NC quantity or NOK control", ""),
        ))

    lab = _clean_columns(_read_excel(path, sheet_name="lab test"))
    if not lab.empty:
        result = _text(_col(lab, "Decision"))
        frames.append(_frame(
            community="BME", supplier="FSD", supplier_code=_text(_col(lab, "SupplierCode"), "FSD"), stage="LAB",
            date=_date(_col(lab, "ReleasedDate", "LoggedDate")), order_po=_text(_col(lab, "PurchaseOrderNumber")),
            model_item_code=_text(_col(lab, "ProductCode")), item_name=_text(_col(lab, "ProductDesignation")),
            family=_text(_col(lab, "Specification")), process=_text(_col(lab, "TestCode")),
            issue_driver=_text(_col(lab, "TestDescription")), inspected_qty=1,
            defect_qty=_negative(result).astype(int), defect_rate=np.nan, result=result,
            spec_text=_text(_col(lab, "CharLimits")), spec_low=np.nan, spec_high=np.nan,
            measured_value=_number(_col(lab, "FinalCycles"), None), unit=_text(_col(lab, "Units")),
            severity=np.where(_negative(result), "Critical", "Low"),
            status=np.where(_text(_col(lab, "ReleasedStatus")).ne(""), "Closed", "Status unavailable"),
            status_available=_text(_col(lab, "ReleasedStatus")).ne(""), metric_scope="Explicit lab decision only",
            source_file=str(path.relative_to(root)), source_sheet="lab test", source_row=lab.index + 2,
            is_alert=_negative(result), alert_reason=np.where(_negative(result), "Mandatory lab test failed", ""),
        ))
    return frames


def _load_cmw(root: Path) -> list[pd.DataFrame]:
    base = root / "BME Database" / "CMW（迪奇）"
    frames: list[pd.DataFrame] = []
    fqc_path = base / "AQL inspecation" / "FQC Daily Report_2026 (1).xlsm"
    if fqc_path.exists():
        for sheet in ["Common line", "High-end line"]:
            raw = _clean_columns(_read_excel(fqc_path, sheet_name=sheet, header=1))
            date = _date(_col(raw, "日期"))
            raw = raw[date.notna()].copy()
            date = date.loc[raw.index]
            result = _text(_col(raw, "检验结果"))
            inspected = _number(_col(raw, "检验批量", "抽样数量"), None)
            defects = _number(_col(raw, "总不良数量", "拒收数量"), 0)
            frames.append(_frame(
                community="BME", supplier="CMW", supplier_code="CMW", stage="AQL",
                date=date, order_po=_text(_col(raw, "工单")), model_item_code=_identifier(_col(raw, "整车料号")),
                item_name=_text(_col(raw, "整车描述", "整车分类")), family=_text(_col(raw, "整车家族")),
                process=_text(_col(raw, "不良的部位"), sheet), issue_driver=_text(_col(raw, "不良描述", "不良原因"), "Inspection result"),
                inspected_qty=inspected, defect_qty=defects,
                defect_rate=np.where(inspected.fillna(0).gt(0), defects / inspected, np.nan), result=result,
                spec_text="", spec_low=np.nan, spec_high=np.nan, measured_value=np.nan, unit="pcs",
                severity=_text(_col(raw, "不良等级"), "Low"),
                status=np.where(_text(_col(raw, "不良重新检验结果")).str.upper().eq("OK"), "Closed", "Status unavailable"),
                status_available=_text(_col(raw, "不良重新检验结果")).ne(""), metric_scope="FQC/AQL record",
                source_file=str(fqc_path.relative_to(root)), source_sheet=sheet, source_row=raw.index + 3,
                is_alert=_negative(result) | defects.gt(0), alert_reason="",
            ))

    iqc_path = base / "IQC" / "IQC Daily Report-2026.xlsx"
    if iqc_path.exists():
        raw = _clean_columns(_read_excel(iqc_path, header=1))
        # The workbook contains thousands of preformatted blank template rows.
        # Keep only rows that carry an actual IQC business identifier or value.
        business_row = pd.concat(
            [
                _col(raw, "FinishedDate检验完成日期", "ReceivingDate收货日期"),
                _col(raw, "P/O工单号", "P/O"),
                _col(raw, "Itemcode料号", "Itemcode"),
                _col(raw, "component零件名称", "component"),
                _col(raw, "QTY数量", "数量"),
            ],
            axis=1,
        ).notna().any(axis=1)
        raw = raw[business_row].copy()
        result = _text(_col(raw, "InspectionResult检验结果", "检验结果"))
        inspected = _number(_col(raw, "QTY数量", "数量"), None)
        defects = _number(_col(raw, "ReturnQTY退货数量", "退货数量"), 0)
        frames.append(_frame(
            community="BME", supplier="CMW", supplier_code="CMW", stage="IQC",
            date=_date(_col(raw, "FinishedDate检验完成日期", "ReceivingDate收货日期")),
            order_po=_text(_col(raw, "P/O工单号", "P/O")), model_item_code=_identifier(_col(raw, "Itemcode料号", "Itemcode")),
            item_name=_text(_col(raw, "component零件名称", "component")), family="", process="Incoming material",
            material_supplier=_text(_col(raw, "Supplier供应商", "Supplier"), "Unrecorded"),
            issue_driver=_text(_col(raw, "NoncomfromingDescription不良描述", "不良描述"), "Inspection result"),
            inspected_qty=inspected, defect_qty=defects,
            defect_rate=np.where(inspected.fillna(0).gt(0), defects / inspected, np.nan), result=result,
            spec_text="", spec_low=np.nan, spec_high=np.nan, measured_value=np.nan, unit="pcs",
            severity=np.where(_negative(result), "High", "Low"), status="Status unavailable", status_available=False,
            metric_scope="Complete IQC log", source_file=str(iqc_path.relative_to(root)), source_sheet="Sheet1",
            source_row=raw.index + 3, is_alert=_negative(result) | defects.gt(0), alert_reason="",
        ))

    process_path = base / "PQC" / "Process Control Record_2026.xlsm"
    if process_path.exists():
        raw = _clean_columns(_read_excel(process_path, sheet_name="Defect Follow-up", header=1))
        defects = _number(_col(raw, "Q'ty数量", "数量"), 0)
        frames.append(_frame(
            community="BME", supplier="CMW", supplier_code="CMW", stage="PQC",
            date=_date(_col(raw, "Date日期")), order_po="", model_item_code=_text(_col(raw, "Model车型")),
            item_name=_text(_col(raw, "Model车型")), family="", process=_text(_col(raw, "W.S工位")),
            issue_driver=_text(_col(raw, "NonconformanceDescription问题描述")), inspected_qty=np.nan,
            defect_qty=defects, defect_rate=np.nan, result=np.where(defects.gt(0), "NG", ""),
            spec_text="", spec_low=np.nan, spec_high=np.nan, measured_value=np.nan, unit="pcs",
            severity="High", status="Status unavailable", status_available=False, metric_scope="Defect log; denominator unavailable",
            source_file=str(process_path.relative_to(root)), source_sheet="Defect Follow-up", source_row=raw.index + 3,
            is_alert=defects.gt(0), alert_reason="Process nonconformity",
        ))

    torque_path = base / "machine data" / "PQC生产扭力记录表.xlsx"
    if torque_path.exists():
        raw = _clean_columns(_read_excel(torque_path, sheet_name="数据结果"))
        for name in ["工单", "扭力车型描述", "车型model", "生产日期", "日期", "当前流程状态", "质量确认结果"]:
            if name in raw:
                raw[name] = raw[name].ffill()
        component = _text(raw.iloc[:, 11] if raw.shape[1] > 11 else _col(raw, "整车料件明细"))
        result = _text(raw.iloc[:, 15] if raw.shape[1] > 15 else _col(raw, "结果"))
        detail = component.ne("") & ~component.str.contains("整车料件项目") & result.ne("")
        raw, component, result = raw[detail].copy(), component[detail], result[detail]
        spec = _text(raw.iloc[:, 12] if raw.shape[1] > 12 else _col(raw, "扭力标准"))
        low, high = _parse_range(spec)
        measured = _number(raw.iloc[:, 13] if raw.shape[1] > 13 else _col(raw, "读数"), None)
        status, status_available = _status(_col(raw, "当前流程状态", "质量确认结果"))
        frames.append(_frame(
            community="BME", supplier="CMW", supplier_code="CMW", stage="MACHINE",
            date=_date(_col(raw, "生产日期")), event_timestamp=_date(_col(raw, "日期")), order_po=_text(_col(raw, "工单")),
            trace_number=_text(_col(raw, "整车追溯号")),
            model_item_code=_text(_col(raw, "车型model")), item_name=_text(_col(raw, "扭力车型描述")),
            family="", process=component, issue_driver=component, inspected_qty=1,
            defect_qty=_negative(result).astype(int), defect_rate=np.nan, result=result,
            spec_text=spec, spec_low=low, spec_high=high, measured_value=measured,
            unit=_text(raw.iloc[:, 14] if raw.shape[1] > 14 else _col(raw, "单位")), severity="High", status=status, status_available=status_available,
            metric_scope="Torque checkpoint", source_file=str(torque_path.relative_to(root)), source_sheet="数据结果",
            source_row=raw.index + 2, is_alert=_negative(result), alert_reason="",
            data_quality_flag=np.where(high.notna() & measured.gt(high * 5), "Suspect value > 5x USL", ""),
            comments=_text(_col(raw, "备注")),
        ))

    rework_path = base / "Rework" / "返工作业申请书.xlsx"
    if rework_path.exists():
        raw = _clean_columns(_read_excel(rework_path, sheet_name="数据结果"))
        status, status_available = _status(_col(raw, "当前流程状态", "判定结论"))
        qty = _number(_col(raw, "数量").astype(str).str.extract(r"([\d.]+)")[0], 0)
        frames.append(_frame(
            community="BME", supplier="CMW", supplier_code="CMW", stage="REWORK",
            date=_date(_col(raw, "申请时间")), event_timestamp=_date(_col(raw, "申请时间.1", "申请时间")),
            workflow_end_date=_date(_col(raw, "更新时间", "完成时间")), order_po=_text(_col(raw, "编号")),
            model_item_code=_text(_col(raw, "型号")), item_name=_text(_col(raw, "零件名")), family="",
            process=_text(_col(raw, "返工作业场所"), "Rework"), issue_driver=_text(_col(raw, "不合格内容", "返工作业原因")),
            inspected_qty=qty, defect_qty=qty, defect_rate=np.nan, result=_text(_col(raw, "判定结论")),
            spec_text=_text(_col(raw, "期望返工时间")), spec_low=np.nan, spec_high=np.nan, measured_value=np.nan,
            unit="pcs", severity=np.where(status.eq("Closed"), "Low", "High"), status=status,
            status_available=status_available, metric_scope="Rework application", source_file=str(rework_path.relative_to(root)),
            source_sheet="数据结果", source_row=raw.index + 2, is_alert=~status.eq("Closed"),
            alert_reason=np.where(status.eq("Closed"), "", "Rework not confirmed closed"),
        ))
    return frames


def _load_tektro(root: Path) -> list[pd.DataFrame]:
    base = root / "BME Database" / "TEKTRO"
    frames: list[pd.DataFrame] = []
    iqc_path = base / "IQC" / "876.1自由彎管IQC紀錄.xlsx"
    if iqc_path.exists():
        with pd.ExcelFile(iqc_path, engine="openpyxl") as workbook:
            sheet_names = [name for name in workbook.sheet_names if name != "OtherInfo"]
        for sheet in sheet_names:
            raw = _clean_columns(_read_excel(iqc_path, sheet_name=sheet, header=12))
            checks = [column for column in raw.columns if column not in {"序號", "批號"}]
            result = raw[checks].astype(str).apply(lambda row: "NOK" if row.str.upper().str.contains("NOK|NG|FAIL").any() else "OK", axis=1)
            frames.append(_frame(
                community="BME", supplier="TEKTRO", supplier_code="TEKTRO", stage="IQC", date=pd.NaT,
                order_po=_text(_col(raw, "批号", "批號")), model_item_code=sheet, item_name=sheet, family="",
                process="Incoming component", issue_driver=np.where(result.eq("NOK"), "IQC checkpoint failed", ""),
                inspected_qty=1, defect_qty=result.eq("NOK").astype(int), defect_rate=np.nan, result=result,
                spec_text="", spec_low=np.nan, spec_high=np.nan, measured_value=np.nan, unit="",
                severity=np.where(result.eq("NOK"), "High", "Low"), status="Status unavailable", status_available=False,
                metric_scope="IQC checkpoint", source_file=str(iqc_path.relative_to(root)), source_sheet=sheet,
                source_row=raw.index + 14, is_alert=result.eq("NOK"), alert_reason="",
            ))

    pqc_path = base / "PQC" / "244570-1.xls"
    if pqc_path.exists():
        raw = _clean_columns(_read_excel(pqc_path))
        measured = _number(_col(raw, "數據04", "数据04"), None)
        frames.append(_frame(
            community="BME", supplier="TEKTRO", supplier_code="TEKTRO", stage="PQC",
            date=_date(_col(raw, "Date")), event_timestamp=_date(_col(raw, "Date")), order_po=_text(_col(raw, "訂單單號", "订单单号")),
            model_item_code=_text(_col(raw, "型號", "型号")), item_name=_text(_col(raw, "型號", "型号")),
            family=_text(_col(raw, "油管長度", "油管长度")),
            process="Continuous parameter", issue_driver="数据04", inspected_qty=1, defect_qty=0,
            defect_rate=np.nan, result="", spec_text="Specification unavailable", spec_low=np.nan, spec_high=np.nan,
            measured_value=measured, unit="", severity="Medium", status="Status unavailable", status_available=False,
            metric_scope="Stability only; specification unavailable", source_file=str(pqc_path.relative_to(root)),
            source_sheet="20260122", source_row=raw.index + 2, is_alert=False, alert_reason="",
        ))

    lab_path = base / "LAB test" / "2026-1~4月Q13RS拔脫力數據.xlsx"
    if lab_path.exists():
        with pd.ExcelFile(lab_path, engine="openpyxl") as workbook:
            sheet_names = list(workbook.sheet_names)
        for sheet in sheet_names:
            raw = _clean_columns(_read_excel(lab_path, sheet_name=sheet))
            measured = _number(_col(raw, "最大力量kgf(標準200kgf)"), None)
            fail = measured.notna() & measured.lt(200)
            frames.append(_frame(
                community="BME", supplier="TEKTRO", supplier_code="TEKTRO", stage="LAB",
                date=_date(_col(raw, "試驗日期:")), order_po=_text(_col(raw, "試驗批號:")),
                model_item_code=_text(_col(raw, "試驗批號:")), item_name="Q13RS pull-out force", family="",
                process=_text(_col(raw, "試驗型態:"), "Pull-out test"), issue_driver="Pull-out force below 200 kgf",
                inspected_qty=1, defect_qty=fail.astype(int), defect_rate=np.nan,
                result=np.where(fail, "FAIL", np.where(measured.notna(), "PASS", "")), spec_text=">= 200 kgf",
                spec_low=200.0, spec_high=np.nan, measured_value=measured, unit="kgf",
                severity=np.where(fail, "Critical", "Low"), status="Closed", status_available=True,
                metric_scope="Explicit 200 kgf source standard", source_file=str(lab_path.relative_to(root)),
                source_sheet=sheet, source_row=raw.index + 2, is_alert=fail,
                alert_reason=np.where(fail, "Mandatory pull-out force below 200 kgf", ""),
            ))
    return frames


def load_bme_quality_events(root: Path) -> pd.DataFrame:
    frames = _load_fsd(root) + _load_cmw(root) + _load_tektro(root)
    if not frames:
        return _empty_events()
    events = pd.concat(frames, ignore_index=True)
    events = _finalize_event_flags(events)
    events["supplier"] = _text(events["supplier"])
    events["stage"] = _text(events["stage"])
    events["source_row"] = pd.to_numeric(events["source_row"], errors="coerce").astype("Int64")
    return events.sort_values(["date", "supplier", "stage"], ascending=[False, True, True], na_position="last").reset_index(drop=True)


def _compact_product_text(value: object) -> str:
    """Normalize a source product alias without inventing a new identifier."""
    if value is None or (not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)):
        return ""
    return re.sub(r"[^A-Z0-9\u4e00-\u9fff]", "", str(value).upper())


def _first_model_token(value: object) -> str:
    """Return the first usable model-family token from a source description."""
    if value is None or (not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)):
        return ""
    tokens = re.findall(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", str(value).upper())
    excluded = {"RAW", "FRAME", "FORK", "FRK", "BIKE", "MM", "CN", "ST", "OLD"}
    for token in tokens:
        compact = _compact_product_text(token)
        if (
            len(compact) >= 4
            and compact not in excluded
            and re.search(r"[A-Z]", compact)
            and re.search(r"\d", compact)
        ):
            return compact
    return ""


def build_bme_product_master(events: pd.DataFrame) -> pd.DataFrame:
    """Create an auditable product master for IQC, PQC and FQC analysis.

    The source files do not share one universal product code. This function
    therefore uses only source-native identifiers and explicit supplier rules:
    FSD IQC item codes, FSD PQC/FQC family-model aliases, CMW FQC whole-bike
    item codes, and TEKTRO source model codes. CMW PQC rows only contain a
    model name, while CMW and FSD IQC rows only contain incoming-component
    codes, so none is assigned to a whole-bike style without an auditable
    one-to-one relationship.
    """
    if events.empty:
        return events.assign(
            quality_gate=pd.Series(dtype="object"),
            product_group=pd.Series(dtype="object"),
            product_key=pd.Series(dtype="object"),
            product_label=pd.Series(dtype="object"),
            product_link_method=pd.Series(dtype="object"),
        )
    source = events[events["stage"].isin(["IQC", "PQC", "AQL", "DKL"])].copy()
    if source.empty:
        return source.assign(
            quality_gate=pd.Series(dtype="object"),
            product_group=pd.Series(dtype="object"),
            product_key=pd.Series(dtype="object"),
            product_label=pd.Series(dtype="object"),
            product_link_method=pd.Series(dtype="object"),
        )
    source["quality_gate"] = source["stage"].replace({"AQL": "FQC", "DKL": "FQC"})

    fsd_alias_labels: dict[str, str] = {}
    fsd_rows = source[source["supplier"].eq("FSD")]
    for value in fsd_rows.loc[fsd_rows["stage"].eq("IQC"), "family"]:
        alias = _compact_product_text(value)
        if len(alias) >= 4 and re.search(r"[A-Z]", alias) and re.search(r"\d", alias):
            fsd_alias_labels.setdefault(alias, str(value).strip())
    for value in fsd_rows.loc[fsd_rows["stage"].eq("PQC"), "model_item_code"]:
        alias = _first_model_token(value)
        if alias:
            fsd_alias_labels.setdefault(alias, alias)

    fsd_aliases = sorted(fsd_alias_labels, key=len, reverse=True)
    product_groups = {"FSD": "车架 / 前叉", "CMW": "CMW 整车料号", "TEKTRO": "刹车系统"}

    def resolve_product(row: pd.Series) -> tuple[str, str, str]:
        supplier = str(row.get("supplier", "") or "").strip()
        code = _compact_product_text(row.get("model_item_code", ""))
        name = _compact_product_text(row.get("item_name", ""))
        family = _compact_product_text(row.get("family", ""))
        haystack = code + name + family
        group = product_groups.get(supplier, supplier or "未记录产品类型")
        if supplier == "CMW" and str(row.get("stage", "")) == "IQC":
            # CMW IQC only identifies the incoming component. Without a BOM
            # relationship, labelling it as a finished-bike style would create
            # a false product link in the management view.
            group = "来料零部件"
        if supplier == "FSD" and str(row.get("stage", "")) == "IQC" and code:
            source_code = str(row.get("model_item_code", "")).strip()
            return (
                f"FSD|IQC_ITEM|{code}",
                f"料号 {source_code}",
                "FSD IQC source item code; no BOM link to bike model",
            )
        if supplier == "FSD":
            matched = next((alias for alias in fsd_aliases if alias in haystack), "")
            if matched:
                identifier = fsd_alias_labels[matched] or matched
                return f"FSD|{matched}", f"{group} · {identifier}", "FSD family / model alias"
        elif supplier == "CMW" and str(row.get("stage", "")) in {"AQL", "DKL"} and code:
            source_code = str(row.get("model_item_code", "")).strip()
            description = str(row.get("item_name", "") or "").strip()
            label = f"整车料号 {source_code}"
            if description:
                label += f" · {description}"
            return f"CMW|{code}", label, "CMW FQC whole-bike item code"
        elif supplier == "CMW" and str(row.get("stage", "")) == "PQC":
            identifier = str(row.get("model_item_code", "") or row.get("item_name", "") or "未记录车型").strip()
            fallback = code or name or "UNMAPPED"
            return (
                f"CMW_MODEL|{fallback}",
                f"PQC 车型（未对应整车料号） · {identifier}",
                "CMW PQC model; no exact whole-bike item-code link",
            )

        fallback = code or name or family or "UNMAPPED"
        raw_identifier = ""
        for value in [row.get("model_item_code", ""), row.get("item_name", ""), row.get("family", "")]:
            if value is not None and not pd.isna(value) and str(value).strip():
                raw_identifier = str(value).strip()
                break
        identifier = raw_identifier or "未记录产品"
        method = "Source item / model code"
        if supplier == "CMW" and str(row.get("stage", "")) == "IQC":
            method = "CMW component code; no BOM link to bike model"
        return f"{supplier}|{fallback}", f"{group} · {identifier}", method

    resolved = source.apply(resolve_product, axis=1, result_type="expand")
    resolved.columns = ["product_key", "product_label", "product_link_method"]
    source[["product_key", "product_label", "product_link_method"]] = resolved
    source["product_group"] = source["supplier"].map(product_groups).fillna(source["supplier"])
    source.loc[
        source["supplier"].eq("CMW") & source["stage"].eq("IQC"),
        "product_group",
    ] = "来料零部件"
    source.loc[
        source["supplier"].eq("CMW") & source["stage"].eq("PQC"),
        "product_group",
    ] = "PQC 车型（未对应整车料号）"
    source.loc[
        source["supplier"].eq("FSD") & source["stage"].eq("IQC"),
        "product_group",
    ] = "IQC 来料料号"
    return source.reset_index(drop=True)


def _relative_percentile(values: pd.Series) -> pd.Series:
    """Return a 0-100 peer percentile without making a single item 100."""
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.notna()
    result = pd.Series(np.nan, index=values.index, dtype="float64")
    count = int(valid.sum())
    if count == 1:
        result.loc[valid] = 50.0
    elif count > 1:
        ranks = numeric.loc[valid].rank(method="average")
        result.loc[valid] = (ranks - 1) / (count - 1) * 100
    return result


def build_bme_relative_risk_scores(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build supplier and product priority scores from auditable BME gates.

    Scores are relative rankings inside the currently selected data, not defect
    probabilities or acceptance decisions. Product baselines are separated by
    supplier, source product family and quality gate so unlike grains are never
    compared directly. Missing gates are reported as coverage and are not scored
    as zero. Rate receives 60% and defect volume 40% when a valid denominator is
    available; otherwise the gate score uses volume only.
    """
    master = build_bme_product_master(events)
    product_columns = [
        "supplier", "product_key", "product_label", "product_group",
        "risk_score", "affected_gates", "available_gates", "defect_qty",
        "inspected_qty", "latest_date", "baseline",
    ]
    supplier_columns = [
        "supplier", "risk_score", "available_gates", "defect_qty",
        "inspected_qty", "product_count", "baseline",
    ]
    if master.empty:
        return pd.DataFrame(columns=product_columns), pd.DataFrame(columns=supplier_columns)

    master = master.copy()
    master["inspected_qty"] = pd.to_numeric(master.get("inspected_qty"), errors="coerce")
    master["defect_qty"] = pd.to_numeric(master.get("defect_qty"), errors="coerce").fillna(0)
    alerts = master.get("is_alert", pd.Series(False, index=master.index)).fillna(False)
    master["risk_defect_qty"] = master["defect_qty"].where(alerts, 0.0)

    # A measured-only process is valid for SPC, but it is not automatically an
    # auditable conforming quality gate. Keep a supplier/gate in relative-risk
    # scoring only when the source contains an explicit judgement or a recorded
    # issue. This prevents missing specifications or blank pass/fail fields from
    # being converted into a misleading zero-risk score.
    result_values = master.get("result", pd.Series("", index=master.index)).fillna("").astype(str).str.strip()
    explicit_judgement = result_values.ne("") & ~result_values.str.fullmatch(
        r"Not recorded|Unrecorded|未记录|None|nan", case=False, na=False
    )
    master["risk_gate_evidence"] = explicit_judgement | alerts | master["defect_qty"].gt(0)
    auditable_gate = master.groupby(["supplier", "quality_gate"], dropna=False)[
        "risk_gate_evidence"
    ].transform("any")
    master = master[auditable_gate].copy()
    if master.empty:
        return pd.DataFrame(columns=product_columns), pd.DataFrame(columns=supplier_columns)

    gate = master.groupby(
        ["supplier", "product_key", "product_label", "product_group", "quality_gate"],
        as_index=False,
    ).agg(
        defect_qty=("risk_defect_qty", "sum"),
        inspected_qty=("inspected_qty", lambda values: values.sum(min_count=1)),
        record_count=("source_row", "size"),
        latest_date=("date", "max"),
    )
    gate["defect_rate"] = gate["defect_qty"].div(gate["inspected_qty"].replace(0, np.nan))
    peer = ["supplier", "product_group", "quality_gate"]
    gate["volume_percentile"] = gate.groupby(peer, dropna=False)["defect_qty"].transform(_relative_percentile)
    gate["rate_percentile"] = gate.groupby(peer, dropna=False)["defect_rate"].transform(_relative_percentile)
    gate["gate_score"] = np.where(
        gate["rate_percentile"].notna(),
        gate["rate_percentile"] * 0.60 + gate["volume_percentile"] * 0.40,
        gate["volume_percentile"],
    )

    products = gate.groupby(
        ["supplier", "product_key", "product_label", "product_group"], as_index=False
    ).agg(
        risk_score=("gate_score", "mean"),
        affected_gates=("defect_qty", lambda values: int((values > 0).sum())),
        available_gates=("quality_gate", "nunique"),
        defect_qty=("defect_qty", "sum"),
        inspected_qty=("inspected_qty", lambda values: values.sum(min_count=1)),
        latest_date=("latest_date", "max"),
    )
    products = products[products["defect_qty"].gt(0)].copy()
    products["risk_score"] = products["risk_score"].round(1)
    products["baseline"] = "Supplier + product family + quality gate peer percentile"
    products = products.sort_values(["risk_score", "defect_qty"], ascending=False).reset_index(drop=True)

    supplier_gate = master.groupby(["supplier", "quality_gate"], as_index=False).agg(
        defect_qty=("risk_defect_qty", "sum"),
        inspected_qty=("inspected_qty", lambda values: values.sum(min_count=1)),
    )
    supplier_gate["defect_rate"] = supplier_gate["defect_qty"].div(
        supplier_gate["inspected_qty"].replace(0, np.nan)
    )
    supplier_gate["volume_percentile"] = supplier_gate.groupby("quality_gate")["defect_qty"].transform(_relative_percentile)
    supplier_gate["rate_percentile"] = supplier_gate.groupby("quality_gate")["defect_rate"].transform(_relative_percentile)
    supplier_gate["gate_score"] = np.where(
        supplier_gate["rate_percentile"].notna(),
        supplier_gate["rate_percentile"] * 0.60 + supplier_gate["volume_percentile"] * 0.40,
        supplier_gate["volume_percentile"],
    )
    supplier_scores = supplier_gate.groupby("supplier", as_index=False).agg(
        risk_score=("gate_score", "mean"),
        available_gates=("quality_gate", "nunique"),
        defect_qty=("defect_qty", "sum"),
        inspected_qty=("inspected_qty", lambda values: values.sum(min_count=1)),
    )
    product_counts = products.groupby("supplier")["product_key"].nunique().rename("product_count")
    supplier_scores = supplier_scores.merge(product_counts, on="supplier", how="left")
    supplier_scores["product_count"] = supplier_scores["product_count"].fillna(0).astype(int)
    supplier_scores["risk_score"] = supplier_scores["risk_score"].round(1)
    supplier_scores["baseline"] = "Quality-gate peer percentile across suppliers"
    supplier_scores = supplier_scores.sort_values(["risk_score", "defect_qty"], ascending=False).reset_index(drop=True)
    return products[product_columns], supplier_scores[supplier_columns]


def build_bme_relative_risk_scores_for_selection(
    period_events: pd.DataFrame,
    selected_suppliers: list[str] | tuple[str, ...] | set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score against the full period peer pool, then filter the displayed rows.

    Supplier selection is a viewing control. It must not change the peer
    baseline or make the same supplier's score move simply because another
    supplier is hidden from the page.
    """
    products, suppliers = build_bme_relative_risk_scores(period_events)
    selected = {str(value) for value in selected_suppliers}
    if not selected:
        return products.iloc[0:0].copy(), suppliers.iloc[0:0].copy()
    return (
        products[products["supplier"].isin(selected)].copy(),
        suppliers[suppliers["supplier"].isin(selected)].copy(),
    )


def build_bme_priority_product_clusters(events: pd.DataFrame) -> pd.DataFrame:
    """Cluster BME products that already have auditable issue evidence.

    The relative-risk axis comes from ``build_bme_relative_risk_scores`` and
    therefore keeps supplier, product-family and quality-gate peer baselines
    separate. The exposure axis is the issue-volume percentile inside the same
    supplier/product-family peer group. K-means is applied only after those
    axes have been normalized to 0-100, so the chart can group unlike source
    grains without pretending they are one lifecycle product.
    """
    columns = [
        "supplier", "product_key", "product_label", "product_group",
        "cluster_label", "risk_score", "exposure_axis", "defect_qty",
        "inspected_qty", "affected_gates", "available_gates", "latest_date",
        "confidence", "baseline",
    ]
    products, _ = build_bme_relative_risk_scores(events)
    if products.empty:
        return pd.DataFrame(columns=columns)

    clustered = products.copy()
    peer = ["supplier", "product_group"]
    clustered["exposure_axis"] = clustered.groupby(peer, dropna=False)[
        "defect_qty"
    ].transform(_relative_percentile)
    clustered["exposure_axis"] = clustered["exposure_axis"].fillna(50.0)

    points = clustered[["exposure_axis", "risk_score"]].fillna(0).to_numpy(dtype=float)
    raw_labels = _deterministic_kmeans_labels(points, cluster_count=3)
    cluster_priority = (
        pd.DataFrame(
            {
                "cluster_id": raw_labels,
                "risk_score": clustered["risk_score"].to_numpy(dtype=float),
            }
        )
        .groupby("cluster_id")["risk_score"]
        .mean()
        .sort_values()
    )
    ordered = cluster_priority.index.astype(int).tolist()
    label_sets = {
        1: ["Priority improvement"],
        2: ["Attention", "Priority improvement"],
        3: ["Monitor", "Attention", "Priority improvement"],
    }
    names = label_sets[len(ordered)]
    name_map = {cluster_id: names[position] for position, cluster_id in enumerate(ordered)}
    clustered["cluster_label"] = [name_map[int(value)] for value in raw_labels]

    inspected = pd.to_numeric(clustered["inspected_qty"], errors="coerce")
    clustered["confidence"] = np.select(
        [inspected.ge(30), inspected.gt(0)],
        ["High", "Medium"],
        default="Low",
    )
    clustered["exposure_axis"] = clustered["exposure_axis"].round(1)
    return clustered[columns].sort_values(
        ["risk_score", "defect_qty"], ascending=False
    ).reset_index(drop=True)


def _deterministic_kmeans_labels(
    points: np.ndarray, cluster_count: int = 3, max_iter: int = 80
) -> np.ndarray:
    """Cluster two-dimensional risk signals without a random seed dependency."""
    if len(points) == 0:
        return np.array([], dtype=int)
    unique_points = np.unique(points, axis=0)
    cluster_count = max(1, min(cluster_count, len(unique_points)))
    scale = points.std(axis=0)
    scale[scale == 0] = 1
    normalized = (points - points.mean(axis=0)) / scale
    order = np.argsort(normalized.sum(axis=1))
    seed_positions = np.linspace(0, len(order) - 1, cluster_count).round().astype(int)
    centroids = normalized[order[seed_positions]].copy()
    labels = np.zeros(len(points), dtype=int)
    for _ in range(max_iter):
        distances = ((normalized[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        next_labels = distances.argmin(axis=1)
        next_centroids = centroids.copy()
        for cluster_id in range(cluster_count):
            members = normalized[next_labels == cluster_id]
            if len(members):
                next_centroids[cluster_id] = members.mean(axis=0)
            else:
                farthest = distances.min(axis=1).argmax()
                next_centroids[cluster_id] = normalized[farthest]
        if np.array_equal(labels, next_labels) and np.allclose(centroids, next_centroids):
            labels = next_labels
            break
        labels = next_labels
        centroids = next_centroids
    return labels


def build_cmw_product_clusters(events: pd.DataFrame) -> pd.DataFrame:
    """Cluster CMW IQC, PQC and FQC quality objects within each source gate.

    CMW IQC component codes, PQC model names and FQC whole-bike item codes do
    not share an auditable master-data relationship. They are therefore never
    merged into one lifecycle product. Each gate is normalized and clustered
    independently, then displayed together as comparable investigation
    priorities. A valid rate uses 60% rate percentile and 40% defect-volume
    percentile. PQC has no denominator, so its score uses defect-volume
    percentile only; issue-record intensity is used only as the second
    clustering axis.
    """
    columns = [
        "quality_gate", "product_key", "product_label", "product_group",
        "cluster_label", "risk_score", "severity_axis", "exposure_axis",
        "defect_qty", "inspected_qty", "defect_rate", "issue_records",
        "record_count", "latest_date", "confidence", "score_basis",
    ]
    master = build_bme_product_master(events)
    master = master[
        master["supplier"].eq("CMW")
        & master["quality_gate"].isin(["IQC", "PQC", "FQC"])
    ].copy()
    if master.empty:
        return pd.DataFrame(columns=columns)

    master["inspected_qty"] = pd.to_numeric(master.get("inspected_qty"), errors="coerce")
    master["defect_qty"] = pd.to_numeric(master.get("defect_qty"), errors="coerce").fillna(0)
    alerts = master.get("is_alert", pd.Series(False, index=master.index)).fillna(False)
    master["risk_defect_qty"] = master["defect_qty"].where(alerts, 0.0)
    master["risk_issue_record"] = alerts.astype(int)
    grouped = master.groupby(
        ["quality_gate", "product_key", "product_label", "product_group"],
        as_index=False,
    ).agg(
        defect_qty=("risk_defect_qty", "sum"),
        inspected_qty=("inspected_qty", lambda values: values.sum(min_count=1)),
        issue_records=("risk_issue_record", "sum"),
        record_count=("source_row", "size"),
        latest_date=("date", "max"),
    )
    grouped["defect_rate"] = grouped["defect_qty"].div(
        grouped["inspected_qty"].replace(0, np.nan)
    )

    grouped["volume_percentile"] = grouped.groupby("quality_gate")["defect_qty"].transform(_relative_percentile)
    grouped["rate_percentile"] = grouped.groupby("quality_gate")["defect_rate"].transform(_relative_percentile)
    grouped["issue_percentile"] = grouped.groupby("quality_gate")["issue_records"].transform(_relative_percentile)
    grouped.loc[grouped["defect_qty"].le(0), "volume_percentile"] = 0.0
    grouped.loc[
        grouped["defect_rate"].notna() & grouped["defect_rate"].le(0),
        "rate_percentile",
    ] = 0.0
    grouped.loc[grouped["issue_records"].le(0), "issue_percentile"] = 0.0

    has_rate = grouped["rate_percentile"].notna()
    grouped["risk_score"] = np.where(
        has_rate,
        grouped["rate_percentile"] * 0.60 + grouped["volume_percentile"] * 0.40,
        grouped["volume_percentile"],
    )
    grouped["severity_axis"] = np.where(
        has_rate, grouped["rate_percentile"], grouped["volume_percentile"]
    )
    grouped["exposure_axis"] = np.where(
        has_rate, grouped["volume_percentile"], grouped["issue_percentile"]
    )
    grouped["score_basis"] = np.where(
        has_rate,
        "Rate percentile 60% + defect-volume percentile 40%",
        "Defect-volume percentile only; denominator unavailable",
    )
    grouped["confidence"] = np.select(
        [
            has_rate & grouped["inspected_qty"].ge(30) & grouped["record_count"].ge(3),
            has_rate,
        ],
        ["High", "Medium"],
        default="Low",
    )

    cluster_labels = pd.Series(index=grouped.index, dtype="object")
    label_sets = {
        1: ["Monitor"],
        2: ["Monitor", "Priority improvement"],
        3: ["Monitor", "Attention", "Priority improvement"],
    }
    for _, gate_rows in grouped.groupby("quality_gate", sort=True):
        points = gate_rows[["severity_axis", "exposure_axis"]].fillna(0).to_numpy(dtype=float)
        raw_labels = _deterministic_kmeans_labels(points, cluster_count=3)
        cluster_priority = (
            pd.DataFrame({"cluster_id": raw_labels, "risk_score": gate_rows["risk_score"].to_numpy()})
            .groupby("cluster_id")["risk_score"]
            .mean()
            .sort_values()
        )
        ordered = cluster_priority.index.astype(int).tolist()
        names = label_sets[len(ordered)]
        name_map = {cluster_id: names[position] for position, cluster_id in enumerate(ordered)}
        cluster_labels.loc[gate_rows.index] = [name_map[int(value)] for value in raw_labels]
    grouped["cluster_label"] = cluster_labels
    grouped["risk_score"] = grouped["risk_score"].round(1)
    grouped["severity_axis"] = grouped["severity_axis"].round(1)
    grouped["exposure_axis"] = grouped["exposure_axis"].round(1)
    return grouped[columns].sort_values(
        ["risk_score", "defect_qty", "issue_records"], ascending=False
    ).reset_index(drop=True)


def bme_source_fingerprint(root: Path) -> tuple[tuple[str, int, int], ...]:
    base = root / "BME Database"
    records: list[tuple[str, int, int]] = []
    if not base.exists():
        return tuple()
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm", ".xls"} and not path.name.startswith("~$"):
            stat = path.stat()
            records.append((str(path.relative_to(root)), int(stat.st_size), int(stat.st_mtime_ns)))
    return tuple(records)


def load_bme_customer_quality(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load factory-to-component-supplier NC declarations and FSD PO quantities."""
    nc_path = root / "BME Database" / "Customer" / "non_conforms_export_22062026.xlsx"
    order_path = root / "BME Database" / "FSD" / "FSD P2 data input.xlsx"
    if not nc_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    raw = _clean_columns(_read_excel(nc_path))
    supplier_raw = _text(_col(raw, "Componentsupplier"))
    supplier = np.select(
        [supplier_raw.str.contains("FUJI", case=False), supplier_raw.str.contains("TEKTRO", case=False)],
        ["FSD", "TEKTRO"], default="Other",
    )
    nc = pd.DataFrame({
        "supplier": supplier,
        "date": _iso_week_date(_col(raw, "Year"), _col(raw, "Week")),
        "year": pd.to_numeric(_col(raw, "Year"), errors="coerce"),
        "week": pd.to_numeric(_col(raw, "Week"), errors="coerce"),
        "item_code": _text(_col(raw, "Nonconformitemcode")),
        "model": _text(_col(raw, "ModelCodeName")),
        "nc_qty": _number(_col(raw, "NonconformQuantities"), 0),
        "defect_code": _text(_col(raw, "DefectCode"), "Unrecorded"),
        "po": _normalize_po(_col(raw, "ComponentPO")),
        "decision": _text(_col(raw, "ProdcomDecision")),
        "comments": _text(_col(raw, "Comments")),
        "nqc": _number(_col(raw, "Nqc"), 0),
        "source_row": raw.index + 2,
    })
    nc = nc[nc["supplier"].isin(["FSD", "TEKTRO"])].reset_index(drop=True)
    if not order_path.exists():
        return nc, pd.DataFrame()
    order_raw = _clean_columns(_read_excel(order_path, sheet_name="Order_Frame(260625)"))
    orders = pd.DataFrame({
        "po": _normalize_po(_col(order_raw, "Ordernumber")),
        "ehd": _date(_col(order_raw, "EHD")),
        "ordered_qty": _number(_col(order_raw, "OrderedQty"), None),
        "model": _text(_col(order_raw, "Model")),
        "item_code": _text(_col(order_raw, "ItemCode")),
        "subcontractor": _text(_col(order_raw, "SubContractor", "Subcontractor", "SubContractorName")),
    })
    fsd_name = orders["subcontractor"].str.contains(r"TIANJIN\s*FUJI|FUJI[- ]?TA", case=False, regex=True, na=False)
    orders = orders[orders["po"].ne("") & fsd_name].copy()
    # A PO may legitimately contain several FSD model/item lines. Aggregate
    # their quantities instead of retaining an arbitrary final line.
    orders = orders.groupby("po", as_index=False).agg(
        ehd=("ehd", "max"),
        ordered_qty=("ordered_qty", "sum"),
        model=("model", lambda values: " / ".join(dict.fromkeys(value for value in values if value))),
        item_code=("item_code", lambda values: " / ".join(dict.fromkeys(value for value in values if value))),
        subcontractor=("subcontractor", "first"),
    )
    return nc, orders


def build_bme_issue_pareto(
    events: pd.DataFrame,
    customer_nc: pd.DataFrame,
    limit: int = 15,
) -> tuple[pd.DataFrame, int]:
    """Combine clearly labeled process defects and component-supplier NC codes.

    Process issues and component-supplier NCs remain separate rows so quantities from
    different quality stages are never silently merged under one label.
    """
    columns = ["supplier", "source_scope", "issue_driver", "defect_qty", "alert_records"]
    process = pd.DataFrame(columns=columns)
    missing_issue_alerts = 0
    if not events.empty:
        alerts = events[events.get("is_alert", pd.Series(False, index=events.index)).fillna(False)].copy()
        raw_issue = alerts.get("issue_driver", pd.Series("", index=alerts.index)).fillna("").astype(str).str.strip()
        generic_issue = raw_issue.str.fullmatch(
            r"|No recorded NOK control|Inspection result|Not recorded|未记录",
            case=False,
            na=True,
        )
        missing_issue_alerts = int(generic_issue.sum())
        process_source = alerts.loc[~generic_issue].copy()
        # A slash can be part of one source description (for example
        # "Frame/fork" or a combined inspection result). Splitting it and
        # copying the full source quantity to every term inflates the Pareto.
        process_source["issue_driver"] = (
            process_source["issue_driver"].fillna("").astype(str).str.strip()
            .str.replace(r"\s*\n+\s*", " / ", regex=True)
        )
        process_source = process_source[
            process_source["issue_driver"].ne("")
            & process_source["issue_driver"].str.contains(r"[A-Za-z\u4e00-\u9fff]", regex=True, na=False)
            & pd.to_numeric(process_source.get("defect_qty", 0), errors="coerce").fillna(0).gt(0)
        ]
        if not process_source.empty:
            process = (
                process_source.groupby(["supplier", "issue_driver"], as_index=False)
                .agg(defect_qty=("defect_qty", "sum"), alert_records=("issue_driver", "size"))
            )
            process["source_scope"] = "Process"
            process = process[columns]

    customer = pd.DataFrame(columns=columns)
    if not customer_nc.empty:
        customer_source = customer_nc.copy()
        customer_source["defect_code"] = customer_source.get(
            "defect_code", pd.Series("", index=customer_source.index)
        ).fillna("").astype(str).str.strip()
        customer_source["nc_qty"] = pd.to_numeric(
            customer_source.get("nc_qty", 0), errors="coerce"
        ).fillna(0)
        customer_source = customer_source[
            customer_source["defect_code"].ne("")
            & ~customer_source["defect_code"].str.fullmatch(r"Unrecorded|Not recorded|未记录", case=False, na=False)
            & customer_source["nc_qty"].gt(0)
        ]
        if not customer_source.empty:
            customer = (
                customer_source.groupby(["supplier", "defect_code"], as_index=False)
                .agg(defect_qty=("nc_qty", "sum"), alert_records=("defect_code", "size"))
                .rename(columns={"defect_code": "issue_driver"})
            )
            customer["issue_driver"] = "Defect Code " + customer["issue_driver"]
            customer["source_scope"] = "Component"
            customer = customer[columns]

    result = pd.concat([process, customer], ignore_index=True)
    if result.empty:
        return pd.DataFrame(columns=columns), missing_issue_alerts
    result = result.sort_values(["defect_qty", "alert_records"], ascending=False)
    if limit > 0:
        result = result.head(limit)
    return result.sort_values("defect_qty").reset_index(drop=True), missing_issue_alerts


def calculate_fsd_customer_ppm(
    nc: pd.DataFrame, orders: pd.DataFrame, start_date: object, end_date: object
) -> dict[str, float]:
    """Calculate FSD customer PPM with each PO counted once in the denominator."""
    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    selected = nc[
        nc["supplier"].eq("FSD")
        & pd.to_datetime(nc["date"], errors="coerce").between(start, end)
    ].copy()
    if selected.empty:
        return {"nc_qty": 0.0, "ordered_qty": 0.0, "coverage": np.nan, "ppm": np.nan}
    linked = selected.merge(orders[["po", "ordered_qty"]], on="po", how="left")
    total_nc = float(selected["nc_qty"].sum())
    matched_nc = float(linked.loc[linked["ordered_qty"].notna(), "nc_qty"].sum())
    coverage = matched_nc / total_nc if total_nc > 0 else np.nan
    period_pos = set(orders.loc[pd.to_datetime(orders["ehd"], errors="coerce").between(start, end), "po"])
    denominator_pos = period_pos | set(selected.loc[selected["po"].ne(""), "po"])
    denominator = float(orders.loc[orders["po"].isin(denominator_pos), "ordered_qty"].fillna(0).sum())
    ppm = total_nc / denominator * 1_000_000 if denominator > 0 and coverage >= 0.90 else np.nan
    return {"nc_qty": total_nc, "ordered_qty": denominator, "coverage": coverage, "ppm": ppm}


def bme_events_to_alerts(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    alerts = events[events["is_alert"]].copy()
    stage_map = {
        "IQC": "IQC", "PQC": "PQC", "AQL": "AQL", "DKL": "DKL",
        "MACHINE": "MACHINE", "LAB": "LAB", "REWORK": "REWORK",
    }
    risk = _text(alerts["severity"], "Medium").str.title()
    risk = risk.where(risk.isin(["Critical", "High", "Medium", "Low"]), "Medium")
    result = pd.DataFrame({
        "alert_type": alerts["stage"].map(stage_map).fillna("PQC"),
        "inspection_type": alerts["stage"],
        "inspection_date": alerts["date"],
        "community": "BME",
        "supplier_dpp": alerts["supplier"],
        "supplier_code": alerts["supplier_code"],
        "material_supplier": np.where(alerts["stage"].eq("IQC"), alerts["supplier"], ""),
        "order_po": alerts["order_po"],
        "model_item_code": alerts["model_item_code"],
        "item_name": alerts["item_name"],
        "issue_driver": alerts["issue_driver"].where(alerts["issue_driver"].ne(""), alerts["alert_reason"]),
        "process": alerts["process"],
        "inspected_qty": alerts["inspected_qty"],
        "defect_qty": alerts["defect_qty"],
        "defect_rate": alerts["defect_rate"],
        "risk_level": risk,
        "status": alerts["status"],
        "spec_text": alerts["spec_text"],
        "source": alerts["source_file"] + " / " + alerts["source_sheet"],
    })
    result["risk_rank"] = result["risk_level"].map({"Critical": 4, "High": 3, "Medium": 2, "Low": 1}).fillna(0)
    return result.reset_index(drop=True)
