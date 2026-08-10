from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


EVENT_COLUMNS = [
    "community",
    "supplier",
    "supplier_code",
    "stage",
    "date",
    "order_po",
    "model_item_code",
    "item_name",
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


def _negative(series: pd.Series) -> pd.Series:
    text = _text(series).str.upper()
    return text.str.contains(
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
    for column in ["inspected_qty", "defect_qty", "defect_rate", "spec_low", "spec_high", "measured_value"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["is_alert"] = frame["is_alert"].fillna(False).astype(bool)
    frame["status_available"] = frame["status_available"].fillna(False).astype(bool)
    return frame


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
        if raw.empty:
            continue
        inspected = _number(_col(raw, "InspectedQty检验数量", "Nbrofframeforkcontroled"), None)
        nc = _number(_col(raw, "NCQty不良数量", "NCQty"), None)
        result = _text(_col(raw, "FinalDecisionofSupplier决定"))
        control_start = 15 if stage == "AQL" else 16
        control_columns = list(raw.columns[control_start:40])
        issue = raw[control_columns].apply(
            lambda row: " / ".join(str(column).split("\n")[0] for column, value in row.items() if str(value).upper().strip() == "NOK"),
            axis=1,
        ) if control_columns else pd.Series("", index=raw.index)
        has_alert = nc.fillna(0).gt(0) | _negative(result) | issue.ne("")
        frames.append(_frame(
            community="BME", supplier="FSD", supplier_code="FSD", stage=stage,
            date=_iso_week_date(_col(raw, "Year年"), _col(raw, "Week周")),
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
                date=date, order_po=_text(_col(raw, "工单")), model_item_code=_text(_col(raw, "整车料号")),
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
        result = _text(_col(raw, "InspectionResult检验结果", "检验结果"))
        inspected = _number(_col(raw, "QTY数量", "数量"), None)
        defects = _number(_col(raw, "ReturnQTY退货数量", "退货数量"), 0)
        frames.append(_frame(
            community="BME", supplier="CMW", supplier_code="CMW", stage="IQC",
            date=_date(_col(raw, "FinishedDate检验完成日期", "ReceivingDate收货日期")),
            order_po=_text(_col(raw, "P/O工单号", "P/O")), model_item_code=_text(_col(raw, "Itemcode料号", "Itemcode")),
            item_name=_text(_col(raw, "component零件名称", "component")), family="", process="Incoming material",
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
            date=_date(_col(raw, "生产日期", "日期")), order_po=_text(_col(raw, "工单")),
            model_item_code=_text(_col(raw, "车型model")), item_name=_text(_col(raw, "扭力车型描述")),
            family="", process=component, issue_driver=component, inspected_qty=1,
            defect_qty=_negative(result).astype(int), defect_rate=np.nan, result=result,
            spec_text=spec, spec_low=low, spec_high=high, measured_value=measured,
            unit=_text(raw.iloc[:, 14] if raw.shape[1] > 14 else _col(raw, "单位")), severity="High", status=status, status_available=status_available,
            metric_scope="Torque checkpoint", source_file=str(torque_path.relative_to(root)), source_sheet="数据结果",
            source_row=raw.index + 2, is_alert=_negative(result), alert_reason="",
        ))

    rework_path = base / "Rework" / "返工作业申请书.xlsx"
    if rework_path.exists():
        raw = _clean_columns(_read_excel(rework_path, sheet_name="数据结果"))
        status, status_available = _status(_col(raw, "当前流程状态", "判定结论"))
        qty = _number(_col(raw, "数量").astype(str).str.extract(r"([\d.]+)")[0], 0)
        frames.append(_frame(
            community="BME", supplier="CMW", supplier_code="CMW", stage="REWORK",
            date=_date(_col(raw, "申请时间")), order_po=_text(_col(raw, "编号")),
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
        measured = _number(_col(raw, "数据04"), None)
        frames.append(_frame(
            community="BME", supplier="TEKTRO", supplier_code="TEKTRO", stage="PQC",
            date=_date(_col(raw, "Date")), order_po=_text(_col(raw, "訂單單號", "订单单号")),
            model_item_code=_text(_col(raw, "型號", "型号")), item_name=_text(_col(raw, "型號", "型号")), family="",
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
