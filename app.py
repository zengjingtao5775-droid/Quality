from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Iterable

VENDOR_DIR = Path(__file__).resolve().parent / ".vendor"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ==========================================
# 0. Page configuration and language
# ==========================================
if "lang" not in st.session_state:
    st.session_state.lang = "中文"


def t(cn_text: str, en_text: str) -> str:
    return cn_text if st.session_state.lang == "中文" else en_text


st.set_page_config(
    page_title="迪卡侬NEA质量看板",
    page_icon="Q",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        display: block;
        background: transparent;
        height: 2.8rem;
        pointer-events: auto;
    }
    div[data-testid="stDeployButton"],
    div[data-testid="stAppDeployButton"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"] {display: none;}
    div[data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
        pointer-events: auto !important;
        width: auto !important;
        height: auto !important;
    }
    div[data-testid="collapsedControl"],
    button[data-testid="stExpandSidebarButton"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        z-index: 999999 !important;
        width: 46px !important;
        min-width: 46px !important;
        height: 46px !important;
        min-height: 46px !important;
        align-items: center !important;
        justify-content: center !important;
        background: #ffffff !important;
        border: 1px solid #d9e2e7 !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14) !important;
    }
    button[data-testid="stExpandSidebarButton"] span,
    button[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
        display: flex !important;
        visibility: visible !important;
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        font-size: 28px !important;
        line-height: 28px !important;
        color: #172033 !important;
    }
    button[data-testid="stExpandSidebarButton"]::after {
        content: "筛选";
        position: absolute;
        left: 54px;
        top: 8px;
        background: #ffffff;
        border: 1px solid #d9e2e7;
        border-radius: 8px;
        padding: 5px 9px;
        color: #172033;
        font-size: 0.82rem;
        font-weight: 780;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.10);
        white-space: nowrap;
    }
    .stApp {
        background:
            radial-gradient(circle at 18% 10%, rgba(229, 48, 55, 0.08), transparent 28%),
            radial-gradient(circle at 82% 12%, rgba(0, 148, 122, 0.12), transparent 32%),
            linear-gradient(180deg, #f8fafc 0%, #eef5f7 100%);
    }
    .block-container {padding-top: 1.0rem; padding-bottom: 2.5rem; max-width: 1420px;}
    section[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(241, 248, 249, 0.96) 100%);
        border-right: 1px solid rgba(203, 213, 225, 0.95);
        box-shadow: 12px 0 34px rgba(15, 23, 42, 0.06);
    }
    section[data-testid="stSidebar"] * {color: #172033;}
    section[data-testid="stSidebar"] div[data-baseweb="select"] * {color: #111827;}
    section[data-testid="stSidebar"] input {color: #111827 !important;}
    h1, h2, h3 {letter-spacing: 0;}
    h1 {font-size: 2.6rem !important; line-height: 1.05 !important;}
    h3 {font-size: 1.28rem !important; margin-top: 1.0rem !important;}
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(226, 232, 240, 0.95);
        border-radius: 8px;
        padding: 8px;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        padding: 0 11px;
        color: #1f2937;
        font-weight: 720;
        font-size: 0.91rem;
    }
    .stTabs [aria-selected="true"] {
        background: #e53037;
        color: #ffffff;
        box-shadow: 0 10px 20px rgba(229, 48, 55, 0.22);
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e7eaee;
        border-radius: 8px;
        padding: 16px 18px;
        min-height: 112px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    div[data-testid="stMetric"] label {
        color: #5b6472;
        font-size: 0.92rem;
    }
    .hero {
        background:
            linear-gradient(120deg, rgba(255,255,255,0.96) 0%, rgba(255,255,255,0.90) 42%, rgba(220, 246, 241, 0.92) 100%);
        color: #172033;
        border-radius: 8px;
        padding: 24px 28px;
        margin-bottom: 14px;
        box-shadow: 0 18px 44px rgba(15, 23, 42, 0.10);
        border: 1px solid rgba(203, 213, 225, 0.92);
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 6px;
        background: linear-gradient(180deg, #e53037, #00947a);
    }
    .hero::after {
        content: "";
        position: absolute;
        right: -90px;
        top: -120px;
        width: 310px;
        height: 310px;
        border-radius: 50%;
        background: rgba(0, 148, 122, 0.12);
        pointer-events: none;
    }
    .hero-title {
        font-size: clamp(1.72rem, 2.8vw, 2.22rem);
        font-weight: 860;
        line-height: 1.08;
        margin: 0;
        letter-spacing: 0;
        position: relative;
        z-index: 1;
    }
    .hero-kicker {
        color: #e53037;
        font-weight: 800;
        text-transform: uppercase;
        font-size: 0.82rem;
        margin-bottom: 8px;
        position: relative;
        z-index: 1;
    }
    .hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 16px;
        position: relative;
        z-index: 1;
    }
    .hero-chip {
        background: #ffffff;
        border: 1px solid #d9e2e7;
        border-radius: 999px;
        padding: 7px 12px;
        color: #344054;
        font-size: 0.88rem;
        font-weight: 650;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
        gap: 14px;
        margin: 14px 0 18px;
    }
    .kpi-card {
        min-height: 118px;
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px 17px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: #64748b;
    }
    .kpi-card.low::before {background: #168a5b;}
    .kpi-card.medium::before {background: #d99a00;}
    .kpi-card.high::before {background: #dc6803;}
    .kpi-card.critical::before {background: #c01048;}
    .kpi-label {
        color: #667085;
        font-size: 0.86rem;
        font-weight: 740;
        margin-bottom: 9px;
    }
    .kpi-value {
        color: #111827;
        font-size: clamp(1.72rem, 2.2vw, 2.0rem);
        font-weight: 860;
        line-height: 1.0;
        white-space: nowrap;
    }
    .kpi-note {
        color: #475467;
        font-size: 0.82rem;
        margin-top: 10px;
        line-height: 1.3;
    }
    .signal-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
        gap: 14px;
        margin: 10px 0 16px;
    }
    .signal-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        min-height: 176px;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
        position: relative;
    }
    .signal-card.low {border-top: 4px solid #168a5b;}
    .signal-card.medium {border-top: 4px solid #d99a00;}
    .signal-card.high {border-top: 4px solid #dc6803;}
    .signal-card.critical {border-top: 4px solid #c01048;}
    .signal-kicker {
        color: #667085;
        font-size: 0.78rem;
        font-weight: 820;
        text-transform: uppercase;
        margin-bottom: 7px;
    }
    .signal-title {
        color: #111827;
        font-size: 1.12rem;
        font-weight: 840;
        line-height: 1.18;
        margin-bottom: 10px;
    }
    .signal-value {
        color: #111827;
        font-size: 1.75rem;
        font-weight: 900;
        margin: 2px 0 8px;
    }
    .signal-evidence {
        color: #475467;
        font-size: 0.86rem;
        line-height: 1.45;
    }
    .risk-pill {
        display: inline-block;
        border-radius: 999px;
        padding: 4px 9px;
        font-size: 0.76rem;
        font-weight: 820;
        color: #ffffff;
        margin-bottom: 9px;
    }
    .risk-pill.low {background: #168a5b;}
    .risk-pill.medium {background: #d99a00;}
    .risk-pill.high {background: #dc6803;}
    .risk-pill.critical {background: #c01048;}
    .section-band {
        background: rgba(255,255,255,0.86);
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        margin: 10px 0 16px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
    }
    .action-strip {
        background: #ffffff;
        color: #172033;
        border-radius: 8px;
        padding: 15px 18px;
        margin: 12px 0 18px;
        border-left: 5px solid #e53037;
        border-top: 1px solid #e5e7eb;
        border-right: 1px solid #e5e7eb;
        border-bottom: 1px solid #e5e7eb;
        box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
    }
    .action-strip b {color: #111827;}
    .action-strip span {color: #475467;}
    .score-logic-lines {
        display: grid;
        gap: 7px;
        color: #475467;
        line-height: 1.36;
    }
    .score-logic-lines div {
        display: block;
    }
    .formula-highlight {
        display: inline-block;
        background: #fff1f2;
        color: #c01048;
        border: 1px solid #fecdd3;
        border-radius: 7px;
        padding: 2px 7px;
        font-weight: 850;
        margin: 0 2px;
    }
    .risk-weight-panel {
        background: linear-gradient(120deg, rgba(255,255,255,0.97) 0%, rgba(255,247,247,0.95) 100%);
        border: 1px solid #fecdd3;
        border-left: 5px solid #e53037;
        border-radius: 8px;
        padding: 14px 16px 10px;
        margin: 12px 0 10px;
        box-shadow: 0 16px 34px rgba(229, 48, 55, 0.08);
    }
    .risk-weight-title {
        color: #111827;
        font-weight: 880;
        font-size: 1.02rem;
        margin-bottom: 4px;
    }
    .risk-weight-note {
        color: #667085;
        font-size: 0.84rem;
        line-height: 1.35;
        margin-bottom: 8px;
    }
    .mapping-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
    }
    .mapping-table th {
        text-align: left;
        color: #475467;
        font-size: 0.82rem;
        background: #f8fafc;
        padding: 11px 12px;
        border-bottom: 1px solid #e5e7eb;
    }
    .mapping-table td {
        padding: 11px 12px;
        border-bottom: 1px solid #eef2f6;
        color: #1f2937;
        vertical-align: middle;
        font-size: 0.9rem;
    }
    .mapping-table tr:last-child td {border-bottom: 0;}
    .mapping-target {
        background: #f8fafc;
        border-left: 3px solid #94a3b8;
        font-weight: 780;
    }
    .mapping-current.done {
        background: #ecfdf3;
        color: #027a48;
        font-weight: 850;
    }
    .mapping-current.watch {
        background: #fffaeb;
        color: #b54708;
        font-weight: 850;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 0.78rem;
        font-weight: 850;
        white-space: nowrap;
    }
    .status-badge.done {
        background: #d1fadf;
        color: #027a48;
        border: 1px solid #a6f4c5;
    }
    .status-badge.watch {
        background: #fef0c7;
        color: #b54708;
        border: 1px solid #fedf89;
    }
    .table-title {
        color: #111827;
        font-weight: 850;
        font-size: 1.05rem;
        margin: 6px 0 10px;
    }
    .zx-lock {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        color: #7c2d12;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 14px;
        font-weight: 720;
    }
    .poc-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);
    }
    .poc-card h4 {
        margin: 0 0 8px 0;
        font-size: 1.02rem;
        color: #111827;
    }
    .poc-small {
        color: #667085;
        font-size: 0.88rem;
        line-height: 1.45;
    }
    .status-dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin-right: 6px;
    }
    @media (max-width: 720px) {
        .kpi-grid, .signal-grid {grid-template-columns: 1fr;}
        .hero-title {font-size: 1.8rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# 1. Data paths and canonical schema
# ==========================================
ROOT = Path(__file__).resolve().parent
RISK_SETTINGS_FILE = ROOT / "quality_dashboard_risk_settings.json"

FACTORIES = {
    "ZX": {
        "name": "ZX / 中兴",
        "supplier": "中兴",
        "location": "ZX",
        "finished": Path("ZX Database/ZX成品质量检验数据.xlsx"),
        "voice": Path("ZX Database/ZX YTD Compare hierarchy.csv"),
        "incoming": Path("ZX Database/ZX 2026年原辅料不合格记录.xlsx"),
        "intern_voice_file": Path("ZX Database/2026 ZX Intern Voice.xlsx"),
        "intern_voice": Path("2026 Intern Voice"),
        "intern_voice_manifest": Path("ZX Database/ZX Intern Voice manifest.csv"),
    },
    "DS": {
        "name": "DS / 鼎盛",
        "supplier": "贵州鼎盛",
        "location": "DS-FG",
        "finished": Path("DS Database/DS 成品质量检验数据.xlsx"),
        "voice": Path("DS Database/DS YTD Compare hierarchy.csv"),
        "incoming": None,
    },
    "JS": {
        "name": "JS / 健盛",
        "supplier": "浙江健盛",
        "location": "JASAN",
        "finished": Path("JS Database/JS 成品质量检验数据.xlsx"),
        "voice": Path("JS Database/JS TYD Compare hierarchy.csv"),
        "incoming": None,
    },
    "TF": {
        "name": "TF / 腾飞",
        "supplier": "衡阳腾飞",
        "location": "TF",
        "finished": None,
        "finished_files": [
            Path("TF Database/数据补充5月29日/尾查数据报表01.xls"),
            Path("TF Database/数据补充5月29日/尾查数据报表02.xls"),
            Path("TF Database/数据补充5月29日/尾查数据报表03.xls"),
            Path("TF Database/数据补充5月29日/尾查数据报表04.xls"),
        ],
        "voice": None,
        "incoming": None,
        "material_files": [
            Path("TF Database/面料检验报告.xls"),
            Path("TF Database/辅料检验登记.xls"),
            Path("TF Database/裁片检验.xls"),
            Path("TF Database/数据补充5月29日/面料检验报告.xls"),
            Path("TF Database/数据补充5月29日/辅料检验登记.xls"),
            Path("TF Database/数据补充5月29日/裁片检验.xls"),
        ],
    },
}

LEVEL_COLORS = {
    "Low": "#168a5b",
    "Medium": "#d99a00",
    "High": "#dc6803",
    "Critical": "#c01048",
}

DEFAULT_RISK_SETTINGS = {
    "supplier_weights": {
        "production_score": 55,
        "client_score": 45,
    },
    "product_weights": {
        "production_score": 55,
        "client_score": 45,
    },
    "client_weights": {
        "rpm_score": 60,
        "intern_voice_score": 40,
    },
    "qc_benchmark_pct": 4.0,
    "process_benchmark_pct": 5.0,
    "rpm_cap": 1500,
    "intern_voice_cap": 30,
    "incoming_reject_cap": 25,
    "incoming_issue_cap": 120,
}


def pick(raw: pd.DataFrame, column: str, default: object = "") -> pd.Series:
    if column in raw.columns:
        return raw[column]
    return pd.Series([default] * len(raw), index=raw.index)


def clean_numeric(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "-"}:
        return np.nan
    text = (
        text.replace(",", "")
        .replace("%", "")
        .replace("↗", "")
        .replace("↘", "")
        .replace(" ", "")
    )
    return pd.to_numeric(text, errors="coerce")


def clean_numeric_series(series: pd.Series) -> pd.Series:
    return series.map(clean_numeric).astype(float)


def extract_product_key(value: object) -> str:
    match = re.search(r"\d+", str(value))
    return match.group(0) if match else ""


def safe_rate(numerator: pd.Series | float, denominator: pd.Series | float) -> pd.Series | float:
    if isinstance(denominator, pd.Series):
        return np.where(denominator > 0, numerator / denominator, 0)
    return numerator / denominator if denominator else 0


def pct(value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):.{digits}%}"


def num(value: object, digits: int = 0) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def compact_num(value: object) -> str:
    if pd.isna(value):
        return "-"
    value = float(value)
    abs_value = abs(value)
    if st.session_state.lang == "中文":
        if abs_value >= 100000000:
            return f"{value / 100000000:.1f}亿"
        if abs_value >= 10000:
            return f"{value / 10000:.1f}万"
        return f"{value:,.0f}"
    if abs_value >= 1000000:
        return f"{value / 1000000:.1f}M"
    if abs_value >= 1000:
        return f"{value / 1000:.1f}K"
    return f"{value:,.0f}"


def risk_level(score: float) -> str:
    if pd.isna(score):
        return "Medium"
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def risk_level_text(level: str) -> str:
    labels = {
        "Low": t("低", "Low"),
        "Medium": t("中", "Medium"),
        "High": t("高", "High"),
        "Critical": t("严重", "Critical"),
    }
    return labels.get(level, level)


def risk_class(level: object) -> str:
    return str(level if pd.notna(level) else "Medium").lower()


def weighted_score(row: pd.Series, weights: dict[str, float]) -> float:
    total_weight = 0.0
    total_score = 0.0
    for col, weight in weights.items():
        value = row.get(col, np.nan)
        if pd.notna(value):
            total_score += float(value) * weight
            total_weight += weight
    return total_score / total_weight if total_weight else np.nan


def default_risk_settings() -> dict:
    return json.loads(json.dumps(DEFAULT_RISK_SETTINGS))


def merge_risk_settings(raw: dict | None) -> dict:
    settings = default_risk_settings()
    if not isinstance(raw, dict):
        return settings
    for section in ["supplier_weights", "product_weights", "client_weights"]:
        if isinstance(raw.get(section), dict):
            for key, value in raw[section].items():
                if key in settings[section]:
                    settings[section][key] = value
    for key in [
        "qc_benchmark_pct",
        "process_benchmark_pct",
        "rpm_cap",
        "intern_voice_cap",
        "incoming_reject_cap",
        "incoming_issue_cap",
    ]:
        if key in raw:
            settings[key] = raw[key]
    return settings


def risk_profile_options() -> list[str]:
    return ["__default__"] + list(FACTORIES.keys())


def risk_profile_label(profile: str) -> str:
    if profile == "__default__":
        return t("全局默认", "Global default")
    return FACTORIES.get(profile, {}).get("name", profile)


def normalize_profile_key(profile: object) -> str:
    profile = str(profile)
    return profile if profile in risk_profile_options() else "__default__"


def default_risk_payload() -> dict:
    return {
        "active_profile": "__default__",
        "profiles": {"__default__": default_risk_settings()},
    }


def merge_risk_payload(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return default_risk_payload()

    if "profiles" not in raw:
        return {
            "active_profile": "__default__",
            "profiles": {"__default__": merge_risk_settings(raw)},
        }

    profiles = {"__default__": merge_risk_settings(raw.get("profiles", {}).get("__default__"))}
    for profile in risk_profile_options()[1:]:
        profile_raw = raw.get("profiles", {}).get(profile)
        if isinstance(profile_raw, dict):
            profiles[profile] = merge_risk_settings(profile_raw)

    return {
        "active_profile": normalize_profile_key(raw.get("active_profile", "__default__")),
        "profiles": profiles,
    }


def profile_settings(payload: dict, profile: str) -> dict:
    payload = merge_risk_payload(payload)
    profile = normalize_profile_key(profile)
    profiles = payload["profiles"]
    return merge_risk_settings(profiles.get(profile, profiles["__default__"]))


def attach_risk_profile_context(settings: dict, payload: dict, active_profile: str) -> dict:
    active_settings = merge_risk_settings(settings)
    merged_payload = merge_risk_payload(payload)
    active_settings["_active_profile"] = normalize_profile_key(active_profile)
    active_settings["_profiles"] = {
        profile: merge_risk_settings(profile_settings(merged_payload, profile))
        for profile in risk_profile_options()
        if profile in merged_payload["profiles"]
    }
    active_settings["_profile_labels"] = {
        profile: risk_profile_label(profile) for profile in risk_profile_options()
    }
    return active_settings


def settings_for_factory(settings: dict, factory_code: object) -> dict:
    factory_code = str(factory_code)
    profiles = settings.get("_profiles")
    if isinstance(profiles, dict):
        if isinstance(profiles.get(factory_code), dict):
            return merge_risk_settings(profiles[factory_code])
        if isinstance(profiles.get("__default__"), dict):
            return merge_risk_settings(profiles["__default__"])
    return merge_risk_settings(settings)


def rpm_risk_score(rpm_value: object, settings: dict) -> float:
    rpm = 0 if pd.isna(rpm_value) else max(float(rpm_value), 0)
    return min(rpm / max(float(settings.get("rpm_cap", 1500)), 1) * 100, 100)


def intern_voice_risk_score(count: object, settings: dict) -> float:
    value = 0 if pd.isna(count) else max(float(count), 0)
    return min(value / max(float(settings.get("intern_voice_cap", 30)), 1) * 100, 100)


def load_risk_payload() -> dict:
    if not RISK_SETTINGS_FILE.exists():
        return default_risk_payload()
    try:
        return merge_risk_payload(json.loads(RISK_SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return default_risk_payload()


def save_risk_payload(payload: dict) -> None:
    try:
        RISK_SETTINGS_FILE.write_text(
            json.dumps(merge_risk_payload(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        st.session_state.risk_settings_persist_warning = True


def normalized_weights(weights: dict[str, float]) -> dict[str, float]:
    clean = {key: max(float(value), 0.0) for key, value in weights.items()}
    total = sum(clean.values())
    if total <= 0:
        return {key: 1 / len(clean) for key in clean}
    return {key: value / total for key, value in clean.items()}


def effective_weight_pct(settings: dict, section: str, key: str) -> float:
    return normalized_weights(settings.get(section, {})).get(key, 0) * 100


def risk_widget_prefix(profile: str) -> str:
    return f"risk_{normalize_profile_key(profile)}"


def risk_settings_from_widget_state(settings: dict, profile: str) -> dict:
    settings = merge_risk_settings(settings)
    prefix = risk_widget_prefix(profile)

    def get_number(key: str, default: float, cast=float):
        try:
            return cast(st.session_state.get(f"{prefix}_{key}", default))
        except (TypeError, ValueError):
            return cast(default)

    return {
        "supplier_weights": {
            "production_score": get_number("supplier_production_weight", settings["supplier_weights"]["production_score"], int),
            "client_score": 100 - get_number("supplier_production_weight", settings["supplier_weights"]["production_score"], int),
        },
        "product_weights": {
            "production_score": get_number("product_production_weight", settings["product_weights"]["production_score"], int),
            "client_score": 100 - get_number("product_production_weight", settings["product_weights"]["production_score"], int),
        },
        "client_weights": {
            "rpm_score": get_number("client_rpm_weight", settings["client_weights"]["rpm_score"], int),
            "intern_voice_score": 100 - get_number("client_rpm_weight", settings["client_weights"]["rpm_score"], int),
        },
        "qc_benchmark_pct": get_number("qc_benchmark_pct", settings["qc_benchmark_pct"], float),
        "process_benchmark_pct": get_number("process_benchmark_pct", settings["process_benchmark_pct"], float),
        "rpm_cap": get_number("rpm_cap", settings["rpm_cap"], float),
        "intern_voice_cap": get_number("intern_voice_cap", settings["intern_voice_cap"], int),
        "incoming_reject_cap": get_number("incoming_reject_cap", settings["incoming_reject_cap"], int),
        "incoming_issue_cap": get_number("incoming_issue_cap", settings["incoming_issue_cap"], int),
    }


def runtime_risk_payload() -> tuple[dict, str, dict]:
    if "risk_payload" not in st.session_state:
        st.session_state.risk_payload = load_risk_payload()

    payload = merge_risk_payload(st.session_state.risk_payload)
    selected_profile = normalize_profile_key(st.session_state.get("risk_profile_selector", payload.get("active_profile", "__default__")))
    current_settings = risk_settings_from_widget_state(profile_settings(payload, selected_profile), selected_profile)
    payload["active_profile"] = selected_profile
    payload["profiles"][selected_profile] = current_settings
    st.session_state.risk_payload = payload
    return payload, selected_profile, current_settings


def current_risk_settings() -> dict:
    payload, selected_profile, current_settings = runtime_risk_payload()
    return attach_risk_profile_context(current_settings, payload, selected_profile)


def render_risk_settings_panel() -> dict:
    payload, active_profile, settings = runtime_risk_payload()
    profile_options = risk_profile_options()
    st.markdown(
        f"""
        <div class="risk-weight-panel">
            <div class="risk-weight-title">{t('权重调整', 'Risk Weight Tuning')}</div>
            <div class="risk-weight-note">
                {t('这里的设置会直接改变下方风险分说明和当前看板排序；保存后下次打开继续使用。', 'These settings directly update the score logic below and the current ranking; save to reuse next time.')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_profile = st.selectbox(
        t("权重方案", "Weight profile"),
        profile_options,
        index=profile_options.index(active_profile),
        format_func=risk_profile_label,
        key="risk_profile_selector",
    )
    settings = profile_settings(payload, selected_profile)
    widget_prefix = risk_widget_prefix(selected_profile)

    st.markdown(t("**生产端权重 vs 客户端权重**", "**Production-side vs Client-side weights**"))
    supplier_cols = st.columns(2)
    supplier_production = supplier_cols[0].slider(
        t("生产端权重：半检/总检质量数据", "Production weight: online/final QC"),
        0,
        100,
        int(settings["supplier_weights"]["production_score"]),
        key=f"{widget_prefix}_supplier_production_weight",
    )
    supplier_client = 100 - int(supplier_production)
    supplier_total = supplier_production + supplier_client
    supplier_cols[1].metric(t("客户端权重", "Client weight"), f"{supplier_client}%")
    st.caption(t(f"当前有效权重：生产端 {supplier_production}% / 客户端 {supplier_client}%。", f"Effective weights: production {supplier_production}% / client {supplier_client}%."))

    with st.expander(t("更多评分基准", "More scoring benchmarks"), expanded=False):
        client_rpm = st.slider(
            t("客户端内权重：RPM百万退货率", "Client sub-weight: RPM return rate"),
            0,
            100,
            int(settings["client_weights"]["rpm_score"]),
            key=f"{widget_prefix}_client_rpm_weight",
        )
        client_iv = 100 - int(client_rpm)
        st.caption(t(f"当前客户端内部权重：RPM {client_rpm}% / Intern Voice {client_iv}%。RPM 和 IV 都是越高风险越高。", f"Client sub-weights: RPM {client_rpm}% / Intern Voice {client_iv}%. Higher RPM and IV means higher risk."))

        b1, b2, b3 = st.columns(3)
        qc_benchmark_pct = b1.number_input(
            t("QC不良率达到多少 = 100分", "QC defect rate for 100 score"),
            min_value=0.5,
            max_value=20.0,
            value=float(settings["qc_benchmark_pct"]),
            step=0.5,
            format="%.1f",
            key=f"{widget_prefix}_qc_benchmark_pct",
        )
        process_benchmark_pct = b2.number_input(
            t("工序不良率达到多少 = 100分", "Process defect rate for 100 score"),
            min_value=0.5,
            max_value=30.0,
            value=float(settings["process_benchmark_pct"]),
            step=0.5,
            format="%.1f",
            key=f"{widget_prefix}_process_benchmark_pct",
        )
        rpm_cap = b3.number_input(
            t("RPM达到多少 = 100分", "RPM for 100 score"),
            min_value=100.0,
            max_value=10000.0,
            value=float(settings["rpm_cap"]),
            step=100.0,
            format="%.0f",
            key=f"{widget_prefix}_rpm_cap",
        )
        st.caption(t("固定口径：Intern Voice 用退货发起次数，默认 30 次封顶 100 分；RPM 为百万退货率，达到上方阈值封顶 100 分。", "Fixed logic: Intern Voice uses return initiation count, capped at 100 at 30; RPM is returns per million, capped at the threshold above."))

    current_settings = risk_settings_from_widget_state(settings, selected_profile)
    current_settings["supplier_weights"] = {
        "production_score": int(supplier_production),
        "client_score": int(supplier_client),
    }
    current_settings["client_weights"] = {
        "rpm_score": int(client_rpm),
        "intern_voice_score": int(client_iv),
    }
    current_settings["qc_benchmark_pct"] = float(qc_benchmark_pct)
    current_settings["process_benchmark_pct"] = float(process_benchmark_pct)
    current_settings["rpm_cap"] = float(rpm_cap)
    runtime_payload = merge_risk_payload(payload)
    runtime_payload["active_profile"] = selected_profile
    runtime_payload["profiles"][selected_profile] = current_settings

    save_col, reset_col, note_col = st.columns([1, 1, 3])
    if st.session_state.pop("risk_save_status", None):
        st.success(t("已保存", "Saved"))
    if st.session_state.pop("risk_settings_persist_warning", None):
        st.warning(
            t(
                "当前环境不支持持久写入文件，本次权重会在当前会话中生效；如需多人长期共用，请接入外部数据存储。",
                "This environment cannot persist local files. The weights apply in the current session; use external storage for shared long-term profiles.",
            )
        )
    if save_col.button(t("保存当前方案", "Save Profile"), key=f"{widget_prefix}_save_risk_settings"):
        save_risk_payload(runtime_payload)
        st.session_state.risk_payload = runtime_payload
        st.session_state.risk_save_status = True
        st.rerun()
    if reset_col.button(t("恢复当前方案", "Reset Profile"), key=f"{widget_prefix}_reset_risk_settings"):
        reset_payload = merge_risk_payload(runtime_payload)
        if selected_profile == "__default__":
            reset_payload["profiles"]["__default__"] = default_risk_settings()
        else:
            reset_payload["profiles"].pop(selected_profile, None)
        reset_payload["active_profile"] = selected_profile
        save_risk_payload(reset_payload)
        st.session_state.risk_payload = reset_payload
        for key in [
            f"{widget_prefix}_supplier_production_weight",
            f"{widget_prefix}_supplier_client_weight",
            f"{widget_prefix}_product_production_weight",
            f"{widget_prefix}_product_client_weight",
            f"{widget_prefix}_client_rpm_weight",
            f"{widget_prefix}_client_iv_weight",
            f"{widget_prefix}_qc_benchmark_pct",
            f"{widget_prefix}_process_benchmark_pct",
            f"{widget_prefix}_rpm_cap",
        ]:
            st.session_state.pop(key, None)
        st.rerun()
    note_col.caption(t("多供应商同屏时，有专属方案的工厂自动使用自己的方案，其余使用全局默认。", "Factory-specific profiles override the global default when multiple suppliers are shown."))

    st.session_state.risk_payload = runtime_payload
    return attach_risk_profile_context(current_settings, runtime_payload, selected_profile)


def render_product_weight_panel() -> dict:
    payload, active_profile, settings = runtime_risk_payload()
    widget_prefix = risk_widget_prefix(active_profile)
    st.markdown(
        f"""
        <div class="risk-weight-panel">
            <div class="risk-weight-title">{t('产品权重方案', 'Product Weight Profile')}</div>
            <div class="risk-weight-note">
                {t('产品风险同样拆成生产端和客户端：生产端来自半检/总检质量数据；客户端来自 RPM 百万退货率和 Intern Voice 退货发起次数。', 'Product risk is also split into production-side QC and client-side RPM plus Intern Voice return initiations.')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    product_production = cols[0].slider(
        t("生产端权重：半检/总检质量数据", "Production weight: online/final QC"),
        0,
        100,
        int(settings["product_weights"]["production_score"]),
        key=f"{widget_prefix}_product_production_weight",
    )
    product_client = 100 - int(product_production)
    cols[1].metric(t("客户端权重", "Client weight"), f"{product_client}%")
    st.caption(t(f"当前有效权重：生产端 {product_production}% / 客户端 {product_client}%。客户端内部 RPM/IV 权重沿用当前方案设置。", f"Effective weights: production {product_production}% / client {product_client}%. Client RPM/IV sub-weights use the current profile."))

    current_settings = risk_settings_from_widget_state(settings, active_profile)
    current_settings["product_weights"] = {
        "production_score": int(product_production),
        "client_score": int(product_client),
    }
    runtime_payload = merge_risk_payload(payload)
    runtime_payload["active_profile"] = active_profile
    runtime_payload["profiles"][active_profile] = current_settings
    if st.session_state.pop("product_risk_save_status", None):
        st.success(t("已保存", "Saved"))
    if st.session_state.pop("risk_settings_persist_warning", None):
        st.warning(
            t(
                "当前环境不支持持久写入文件，本次权重会在当前会话中生效；如需多人长期共用，请接入外部数据存储。",
                "This environment cannot persist local files. The weights apply in the current session; use external storage for shared long-term profiles.",
            )
        )
    if st.button(t("保存产品权重方案", "Save Product Profile"), key=f"{widget_prefix}_save_product_risk_settings"):
        save_risk_payload(runtime_payload)
        st.session_state.risk_payload = runtime_payload
        st.session_state.product_risk_save_status = True
        st.rerun()

    st.session_state.risk_payload = runtime_payload
    return attach_risk_profile_context(current_settings, runtime_payload, active_profile)


def read_excel_any(path: Path, **kwargs) -> pd.DataFrame:
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    return pd.read_excel(path, engine=engine, **kwargs)


def configured_source_count() -> int:
    count = 0
    for cfg in FACTORIES.values():
        for key in ["finished", "voice", "incoming"]:
            rel = cfg.get(key)
            if rel is not None and (ROOT / rel).exists():
                count += 1
        for key in ["finished_files", "material_files"]:
            for rel in cfg.get(key, []):
                if (ROOT / rel).exists():
                    count += 1
        intern_file = cfg.get("intern_voice_file")
        intern_dir = cfg.get("intern_voice")
        intern_manifest = cfg.get("intern_voice_manifest")
        if (intern_file is not None and (ROOT / intern_file).exists()) or (
            intern_dir is not None and any((ROOT / intern_dir).glob("*.png"))
        ) or (
            intern_manifest is not None and (ROOT / intern_manifest).exists()
        ):
            count += 1
    return count


def normalize_finished_qc(canonical: pd.DataFrame) -> pd.DataFrame:
    if canonical.empty:
        return canonical

    canonical = canonical.copy()
    for col in ["qty_ordered", "qty_inspected", "scrap_qty", "defect_qty"]:
        if col not in canonical.columns:
            canonical[col] = 0
        canonical[col] = pd.to_numeric(canonical[col], errors="coerce").fillna(0)

    canonical["date"] = pd.to_datetime(canonical["date"], errors="coerce")
    canonical["product_code"] = canonical["product_code"].astype(str).str.strip()
    canonical["product_key"] = canonical["product_code"].map(extract_product_key)
    canonical["product_label"] = canonical["product_label"].fillna("").astype(str)
    canonical["process"] = canonical["process"].replace("", np.nan).fillna("未记录")
    canonical["worker_team"] = canonical["worker_team"].replace("", np.nan).fillna("未记录")
    canonical["defect_type"] = canonical["defect_type"].replace("", np.nan)
    canonical["defect_type"] = np.where(
        canonical["defect_qty"] > 0,
        canonical["defect_type"].fillna("未知疵点"),
        "良品",
    )
    canonical["defect_rate"] = safe_rate(canonical["defect_qty"], canonical["qty_inspected"])
    canonical["rft"] = 1 - canonical["defect_rate"]
    canonical["month"] = canonical["date"].dt.to_period("M").astype(str)
    return canonical


def load_tf_finished_qc(cfg: dict) -> pd.DataFrame:
    detail_frames: list[pd.DataFrame] = []
    inspection_frames: list[pd.DataFrame] = []
    inspection_key = ["date", "workshop", "product_code", "work_order", "item_code", "product_label"]

    for rel in cfg.get("finished_files", []):
        path = ROOT / rel
        if not path.exists():
            continue

        raw = read_excel_any(path, sheet_name=0, header=3)
        raw.columns = [str(c).strip() for c in raw.columns]
        rename = {
            "Unnamed: 0": "date",
            "Unnamed: 1": "updated_at",
            "Unnamed: 2": "workshop",
            "Unnamed: 3": "product_code",
            "Unnamed: 4": "work_order",
            "Unnamed: 5": "item_code",
            "Unnamed: 6": "product_label",
            "Unnamed: 7": "inspection_defects",
            "Unnamed: 8": "inspection_qty",
            "Unnamed: 9": "inspection_defect_rate",
            "Unnamed: 10": "inspector_code",
            "Unnamed: 11": "inspector",
            "Unnamed: 12": "reviewer_code",
            "Unnamed: 13": "reviewer",
            "工序名称": "process",
            "返工名称": "defect_name",
            "员工姓名": "worker_team",
            "疵点类型": "defect_grade",
            "不良数": "detail_defects",
        }
        raw = raw.rename(columns=rename)
        main_cols = [
            "date",
            "updated_at",
            "workshop",
            "product_code",
            "work_order",
            "item_code",
            "product_label",
            "inspection_defects",
            "inspection_qty",
            "inspection_defect_rate",
            "inspector_code",
            "inspector",
            "reviewer_code",
            "reviewer",
        ]
        raw["_summary_row"] = pd.to_datetime(raw["date"], errors="coerce").notna()
        raw["inspection_id"] = raw["_summary_row"].cumsum()
        for col in main_cols:
            if col in raw.columns:
                raw[col] = raw[col].ffill()

        raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
        for col in inspection_key[1:]:
            raw[col] = raw.get(col, "").fillna("").astype(str).str.strip()

        inspection = raw[raw["_summary_row"]].copy()
        inspection["inspection_qty"] = pd.to_numeric(inspection["inspection_qty"], errors="coerce")
        inspection["inspection_defects"] = pd.to_numeric(inspection["inspection_defects"], errors="coerce")
        rate_text = inspection["inspection_defect_rate"].fillna("").astype(str).str.strip()
        rate_value = pd.to_numeric(rate_text.str.replace("%", "", regex=False), errors="coerce")
        rate_value = np.where(rate_text.str.contains("%", regex=False), rate_value / 100, np.where(rate_value > 1, rate_value / 100, rate_value))
        derived_qty = inspection["inspection_defects"] / pd.Series(rate_value, index=inspection.index).replace(0, np.nan)
        inspection["inspection_qty"] = inspection["inspection_qty"].where(inspection["inspection_qty"] > 0, derived_qty)
        inspection["source_file"] = str(rel)
        inspection_frames.append(inspection[inspection_key + ["inspection_qty", "source_file"]])

        raw["detail_defects"] = pd.to_numeric(raw.get("detail_defects", 0), errors="coerce").fillna(0)
        detail = raw[(raw["product_code"].notna()) & (raw["detail_defects"] > 0)].copy()
        if detail.empty:
            continue
        detail["source_file"] = str(rel)
        detail_frames.append(detail)

    if not detail_frames or not inspection_frames:
        return pd.DataFrame()

    detail = pd.concat(detail_frames, ignore_index=True)
    inspection = pd.concat(inspection_frames, ignore_index=True)
    inspection_qty = (
        inspection.groupby(inspection_key, dropna=False, as_index=False)["inspection_qty"]
        .sum(min_count=1)
        .fillna({"inspection_qty": 0})
    )
    detail = detail.merge(inspection_qty, on=inspection_key, how="left", suffixes=("", "_merged"))
    detail_total = detail.groupby(inspection_key, dropna=False)["detail_defects"].transform("sum").replace(0, np.nan)
    detail["allocated_qty"] = detail["inspection_qty_merged"].fillna(0) * detail["detail_defects"] / detail_total
    detail["allocated_qty"] = detail["allocated_qty"].fillna(0)

    canonical = pd.DataFrame(
        {
            "factory_code": "TF",
            "factory_name": cfg["name"],
            "supplier": cfg["supplier"],
            "location": cfg["location"],
            "product_line": "Apparel / TF",
            "customer": "Decathlon",
            "product_code": detail["product_code"],
            "product_label": detail["product_label"],
            "item_code": detail["item_code"],
            "inspection_type": "尾查",
            "work_order": detail["work_order"],
            "workshop": detail["workshop"],
            "process": detail.get("process", "未记录"),
            "worker_team": detail.get("worker_team", "未记录"),
            "inspector": detail.get("inspector", ""),
            "qty_ordered": 0,
            "qty_inspected": detail["allocated_qty"],
            "scrap_qty": 0,
            "defect_qty": detail["detail_defects"],
            "defect_type": detail.get("defect_name", "").fillna(detail.get("defect_grade", "")),
            "defect_grade": detail.get("defect_grade", ""),
            "date": detail["date"],
            "source_file": detail["source_file"],
        }
    )
    canonical["inspection_stage"] = "End QC / FQC"
    return normalize_finished_qc(canonical)


# ==========================================
# 2. Data loading
# ==========================================
@st.cache_data(show_spinner=False)
def load_finished_qc() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for factory_code, cfg in FACTORIES.items():
        if factory_code == "TF":
            tf_finished = load_tf_finished_qc(cfg)
            if not tf_finished.empty:
                frames.append(tf_finished)
            continue

        if cfg.get("finished") is None:
            continue
        path = ROOT / cfg["finished"]
        if not path.exists():
            continue

        raw = read_excel_any(path, sheet_name=0)
        raw.columns = [str(c).strip() for c in raw.columns]

        if factory_code == "ZX":
            canonical = pd.DataFrame(
                {
                    "factory_code": factory_code,
                    "factory_name": cfg["name"],
                    "supplier": cfg["supplier"],
                    "location": cfg["location"],
                    "product_line": "300 FG GLOVES",
                    "customer": pick(raw, "客户", ""),
                    "product_code": pick(raw, "款式", ""),
                    "product_label": pick(raw, "颜色", ""),
                    "item_code": pick(raw, "尺码", ""),
                    "inspection_type": pick(raw, "质检类型", ""),
                    "work_order": pick(raw, "生产通知单", ""),
                    "workshop": pick(raw, "车间", ""),
                    "process": pick(raw, "不良工序", ""),
                    "worker_team": pick(raw, "生产工人", ""),
                    "inspector": pick(raw, "检验员", ""),
                    "qty_ordered": pick(raw, "订单数量", 0),
                    "qty_inspected": pick(raw, "检验数量", 0),
                    "scrap_qty": 0,
                    "defect_qty": pick(raw, "疵点个数", 0),
                    "defect_type": pick(raw, "疵点类型", ""),
                    "defect_grade": "",
                    "date": pick(raw, "检验日期", pd.NaT),
                    "source_file": str(cfg["finished"]),
                }
            )
            canonical["inspection_stage"] = np.where(
                canonical["inspection_type"].astype(str).str.contains("中间|在线", na=False),
                "Online QC",
                "End QC / FQC",
            )
        else:
            canonical = pd.DataFrame(
                {
                    "factory_code": factory_code,
                    "factory_name": cfg["name"],
                    "supplier": pick(raw, "供应商", cfg["supplier"]),
                    "location": pick(raw, "Location", cfg["location"]),
                    "product_line": pick(raw, "产品类型", ""),
                    "customer": pick(raw, "品牌", ""),
                    "product_code": pick(raw, "CC", ""),
                    "product_label": pick(raw, "Model Name", ""),
                    "item_code": pick(raw, "Item Code", ""),
                    "inspection_type": pick(raw, "Good Type", "Finish Good"),
                    "work_order": pick(raw, "迪卡侬订单号", ""),
                    "workshop": pick(raw, "生产部门", ""),
                    "process": pick(raw, "不良工序", ""),
                    "worker_team": pick(raw, "生产工人", ""),
                    "inspector": pick(raw, "检验人", ""),
                    "qty_ordered": pick(raw, "订单数量", 0),
                    "qty_inspected": pick(raw, "已检数量", 0),
                    "scrap_qty": pick(raw, "报废件数", 0),
                    "defect_qty": pick(raw, "疵点个数", 0),
                    "defect_type": pick(raw, "疵点类型", ""),
                    "defect_grade": pick(raw, "疵点等级", ""),
                    "date": pick(raw, "检验日期", pd.NaT),
                    "source_file": str(cfg["finished"]),
                }
            )
            canonical["inspection_stage"] = "End QC / FQC"

        frames.append(normalize_finished_qc(canonical))

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


@st.cache_data(show_spinner=False)
def load_customer_voice() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for factory_code, cfg in FACTORIES.items():
        if cfg.get("voice") is None:
            continue
        path = ROOT / cfg["voice"]
        if not path.exists():
            continue

        raw = pd.read_csv(path, encoding="utf-16", sep="\t")
        raw.columns = [str(c).strip() for c in raw.columns]
        products = raw.get("Products", pd.Series([""] * len(raw))).astype(str)

        voice = pd.DataFrame(
            {
                "factory_code": factory_code,
                "factory_name": cfg["name"],
                "supplier": cfg["supplier"],
                "hierarchy_1": raw.get("Hierarchy 1", ""),
                "hierarchy_2": raw.get("Hierarchy 2", raw.get("Hierarchy 2  ", "")),
                "product_raw": products,
                "product_code": products.str.extract(r"^(\d+)")[0].fillna(""),
                "product_name": products.str.replace(r"^\d+\s*", "", regex=True),
                "avg_score_prev": clean_numeric_series(raw.get("Avg score N-X", pd.Series([np.nan] * len(raw)))),
                "avg_score_now": clean_numeric_series(raw.get("Avg score N0", pd.Series([np.nan] * len(raw)))),
                "delta_avg_score": clean_numeric_series(raw.get("Delta avg score N-X", pd.Series([np.nan] * len(raw)))),
                "rpm_prev": clean_numeric_series(raw.get("RPM  N-X", pd.Series([np.nan] * len(raw)))),
                "rpm_now": clean_numeric_series(raw.get("RPM n 0", pd.Series([np.nan] * len(raw)))),
                "delta_rpm": clean_numeric_series(raw.get("delta RPM N-X", pd.Series([np.nan] * len(raw)))),
                "reviews_prev": clean_numeric_series(raw.get("Nb reviews N-X", pd.Series([np.nan] * len(raw)))),
                "reviews_now": clean_numeric_series(raw.get("nb_reviews_N_0", pd.Series([np.nan] * len(raw)))),
                "nqc_prev": clean_numeric_series(raw.get("NQC N-X", pd.Series([np.nan] * len(raw)))),
                "nqc_now": clean_numeric_series(raw.get("non_quality_cost_N_0", pd.Series([np.nan] * len(raw)))),
                "returned_prev": clean_numeric_series(raw.get("Qty returned N-X", pd.Series([np.nan] * len(raw)))),
                "returned_now": clean_numeric_series(raw.get("qty_returned_1stlife_N_0", pd.Series([np.nan] * len(raw)))),
                "sold_prev": clean_numeric_series(raw.get("Qty sold N-X", pd.Series([np.nan] * len(raw)))),
                "sold_now": clean_numeric_series(raw.get("qty_sold_RPM_without_workshop_N_0", pd.Series([np.nan] * len(raw)))),
                "intern_voice_count": 0,
                "voice_source": "YTD Compare",
                "source_file": str(cfg["voice"]),
            }
        )
        voice["product_key"] = voice["product_code"].map(extract_product_key)
        voice["customer_score"] = (
            np.minimum(voice["rpm_now"].fillna(0).clip(lower=0) / 4000 * 35, 35)
            + np.minimum(voice["delta_rpm"].fillna(0).clip(lower=0) / 1500 * 20, 20)
            + np.minimum(voice["returned_now"].fillna(0).clip(lower=0) / 150 * 15, 15)
            + np.minimum((4.5 - voice["avg_score_now"].fillna(4.5)).clip(lower=0) / 1.0 * 20, 20)
            + np.minimum(voice["nqc_now"].fillna(0).clip(lower=0) / 1000 * 10, 10)
        )
        frames.append(voice)

    intern_file = ROOT / FACTORIES["ZX"]["intern_voice_file"]
    intern_dir = ROOT / FACTORIES["ZX"]["intern_voice"]
    intern_manifest = ROOT / FACTORIES["ZX"]["intern_voice_manifest"]
    intern = pd.DataFrame()
    intern_source_file = None
    if intern_file.exists():
        raw_intern = read_excel_any(intern_file, sheet_name=0)
        raw_intern.columns = [str(col).strip() for col in raw_intern.columns]
        row_count = len(raw_intern)
        intern = pd.DataFrame(
            {
                "iv_no": raw_intern.get("IV No.", pd.Series(range(row_count), index=raw_intern.index)).astype(str),
                "product_code": raw_intern.get("CC", pd.Series("", index=raw_intern.index)).astype(str),
                "model_code": raw_intern.get("MODEL", pd.Series("", index=raw_intern.index)).astype(str),
                "product_name": raw_intern.get("款式颜色 Model Name", pd.Series("", index=raw_intern.index)).fillna("").astype(str),
                "quality_issue": raw_intern.get("质量问题", pd.Series("", index=raw_intern.index)).fillna("").astype(str),
                "feedback_date": pd.to_datetime(raw_intern.get("反馈日期", pd.Series(pd.NaT, index=raw_intern.index)), errors="coerce"),
            }
        )
        fallback_case_id = pd.Series(intern.index.astype(str), index=intern.index)
        intern["case_id"] = intern["iv_no"].replace({"": np.nan, "nan": np.nan}).fillna(fallback_case_id)
        intern["file_name"] = intern["case_id"]
        intern_source_file = FACTORIES["ZX"]["intern_voice_file"]
    elif intern_manifest.exists():
        intern = pd.read_csv(intern_manifest)
        if "file_name" not in intern.columns:
            intern["file_name"] = ""
        intern["file_name"] = intern["file_name"].fillna("").astype(str)
        intern_source_file = FACTORIES["ZX"]["intern_voice_manifest"]
    elif intern_dir.exists():
        image_files = [p for p in intern_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        if image_files:
            intern = pd.DataFrame({"file_name": [p.name for p in image_files]})
            intern_source_file = FACTORIES["ZX"]["intern_voice"]
    if not intern.empty:
        if "product_code" not in intern.columns:
            intern["product_code"] = intern["file_name"].str.extract(r"^(\d+)")[0].fillna("")
        intern["product_code"] = intern["product_code"].fillna("").astype(str)
        if "case_id" not in intern.columns:
            intern["case_id"] = intern["file_name"].fillna("").astype(str)
        if "product_name" not in intern.columns:
            intern["product_name"] = "Intern Voice"
        intern_summary = (
            intern[intern["product_code"] != ""]
            .groupby("product_code", as_index=False)
            .agg(
                intern_voice_count=("case_id", "nunique"),
                evidence_files=("file_name", lambda s: ", ".join(s.head(3))),
                product_name=("product_name", lambda s: next((str(v) for v in s if str(v).strip()), "Intern Voice")),
            )
        )
        if not intern_summary.empty:
            voice = pd.DataFrame(
                {
                    "factory_code": "ZX",
                    "factory_name": FACTORIES["ZX"]["name"],
                    "supplier": FACTORIES["ZX"]["supplier"],
                    "hierarchy_1": "Intern Voice",
                    "hierarchy_2": "Intern Voice",
                    "product_raw": intern_summary["product_code"],
                    "product_code": intern_summary["product_code"],
                    "product_name": intern_summary["product_name"],
                    "avg_score_prev": np.nan,
                    "avg_score_now": np.nan,
                    "delta_avg_score": np.nan,
                    "rpm_prev": np.nan,
                    "rpm_now": np.nan,
                    "delta_rpm": np.nan,
                    "reviews_prev": np.nan,
                    "reviews_now": np.nan,
                    "nqc_prev": np.nan,
                    "nqc_now": np.nan,
                    "returned_prev": np.nan,
                    "returned_now": np.nan,
                    "sold_prev": np.nan,
                    "sold_now": np.nan,
                    "intern_voice_count": intern_summary["intern_voice_count"],
                    "voice_source": "Intern Voice",
                    "source_file": str(intern_source_file or FACTORIES["ZX"]["intern_voice_file"]),
                }
            )
            voice["product_key"] = voice["product_code"].map(extract_product_key)
            voice["customer_score"] = np.minimum(voice["intern_voice_count"].fillna(0) / 3 * 45, 45)
            frames.append(voice)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


@st.cache_data(show_spinner=False)
def load_incoming_material() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    path = ROOT / FACTORIES["ZX"]["incoming"]
    sheet_map = {
        "辅料不良明细记录": "辅料",
        "主料不良明细记录": "主料",
    }

    if path.exists():
        for sheet_name, material_type in sheet_map.items():
            raw = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")
            header_candidates = raw.index[raw.eq("批次").any(axis=1)].tolist()
            if not header_candidates:
                continue

            header_index = header_candidates[0]
            data = raw.iloc[header_index + 1 :].copy()
            columns = [
                "batch",
                "material_supplier",
                "customer",
                "material_name",
                "material_color",
                "material_qty",
                "unit",
                "issue",
                "decision",
                "date",
                "remark",
                "extra",
            ]
            data = data.iloc[:, : len(columns)]
            data.columns = columns[: data.shape[1]]
            data = data.dropna(how="all")
            data = data[data["batch"].notna() | data["issue"].notna()]
            if data.empty:
                continue

            data["factory_code"] = "ZX"
            data["factory_name"] = FACTORIES["ZX"]["name"]
            data["supplier"] = FACTORIES["ZX"]["supplier"]
            data["material_type"] = material_type
            data["date"] = pd.to_datetime(data["date"], errors="coerce")
            data["material_qty"] = pd.to_numeric(data["material_qty"], errors="coerce").fillna(0)
            data["decision"] = data["decision"].fillna("未记录").astype(str)
            data["issue"] = data["issue"].fillna("未知问题").astype(str)
            data["material_supplier"] = data["material_supplier"].fillna("未记录").astype(str)
            data["source_file"] = str(FACTORIES["ZX"]["incoming"])
            frames.append(data)

    tf_cfg = FACTORIES.get("TF", {})
    for rel in tf_cfg.get("material_files", []):
        material_path = ROOT / rel
        if not material_path.exists():
            continue

        if material_path.name == "辅料检验登记.xls":
            accessory = read_excel_any(material_path, sheet_name=0, header=2)
            accessory.columns = [str(c).strip() for c in accessory.columns]
            accessory["不良数"] = pd.to_numeric(accessory.get("不良数", 0), errors="coerce").fillna(0)
            accessory = accessory[
                (accessory["日期"].notna())
                & ((accessory["不良数"] > 0) | (~accessory["抽检结果"].astype(str).str.contains("合格|OK", case=False, na=False)))
            ].copy()
            if accessory.empty:
                continue
            data = pd.DataFrame(
                {
                    "batch": pick(accessory, "编号", ""),
                    "material_supplier": pick(accessory, "供应商", "未记录"),
                    "customer": "Decathlon",
                    "material_name": pick(accessory, "物料名称", ""),
                    "material_color": pick(accessory, "颜色", ""),
                    "material_qty": pick(accessory, "来料数量", 0),
                    "unit": pick(accessory, "物料单位", ""),
                    "issue": pick(accessory, "问题描述", "辅料抽检异常").fillna("辅料抽检异常"),
                    "decision": pick(accessory, "抽检结果", "未记录"),
                    "date": pick(accessory, "日期", pd.NaT),
                    "remark": pick(accessory, "备注", ""),
                    "extra": pick(accessory, "检验标准", ""),
                    "factory_code": "TF",
                    "factory_name": tf_cfg.get("name", "TF / 腾飞"),
                    "supplier": tf_cfg.get("supplier", "衡阳腾飞"),
                    "material_type": "辅料",
                    "source_file": str(rel),
                }
            )
            data["material_supplier"] = data["material_supplier"].fillna("未记录").astype(str)

        elif material_path.name == "裁片检验.xls":
            cut = read_excel_any(material_path, sheet_name=0, header=2)
            cut.columns = [str(c).strip() for c in cut.columns]
            main_cols = ["测试类型", "日期", "款号", "颜色", "总数量", "部位名称", "抽检结果", "复检结果", "检验人", "审核人", "抽检数量", "不良数"]
            for col in main_cols:
                if col in cut.columns:
                    cut[col] = cut[col].ffill()
            cut["问题不良数"] = pd.to_numeric(cut.get("Unnamed: 34", 0), errors="coerce").fillna(0)
            cut["主不良数"] = pd.to_numeric(cut.get("不良数", 0), errors="coerce").fillna(0)
            cut = cut[
                (cut["款号"].notna())
                & (cut.get("问题列表", pd.Series(index=cut.index, dtype=object)).notna())
                & (cut.get("问题列表", "").astype(str) != "问题描述")
                & ((cut["问题不良数"] > 0) | (cut["主不良数"] > 0))
            ].copy()
            if cut.empty:
                continue
            data = pd.DataFrame(
                {
                    "batch": pick(cut, "订单号", "").fillna(pick(cut, "款号", "")),
                    "material_supplier": pick(cut, "检验人", "衡阳腾飞").fillna("衡阳腾飞"),
                    "customer": "Decathlon",
                    "material_name": pick(cut, "部位名称", "").fillna(pick(cut, "款号", "")),
                    "material_color": pick(cut, "颜色", ""),
                    "material_qty": pick(cut, "抽检数量", 0).fillna(pick(cut, "总数量", 0)),
                    "unit": "pcs",
                    "issue": pick(cut, "问题列表", "裁片异常"),
                    "decision": pick(cut, "抽检结果", "未记录"),
                    "date": pick(cut, "日期", pd.NaT),
                    "remark": pick(cut, "检验内容", ""),
                    "extra": cut["问题不良数"],
                    "factory_code": "TF",
                    "factory_name": tf_cfg.get("name", "TF / 腾飞"),
                    "supplier": tf_cfg.get("supplier", "衡阳腾飞"),
                    "material_type": "裁片",
                    "source_file": str(rel),
                }
            )

        elif material_path.name == "面料检验报告.xls":
            fabric = read_excel_any(material_path, sheet_name=0, header=2)
            fabric.columns = [str(c).strip() for c in fabric.columns]
            main_cols = ["来料日期", "检验日期", "面料型号", "单号", "供应商", "客户名称", "客户花色号", "送货总数", "检验结果", "异常处理方式"]
            for col in main_cols:
                if col in fabric.columns:
                    fabric[col] = fabric[col].ffill()
            fabric["总扣分"] = pd.to_numeric(fabric.get("Unnamed: 31", 0), errors="coerce").fillna(0)
            fabric = fabric[
                (fabric["单号"].notna())
                & ((fabric["总扣分"] > 0) | (~fabric["检验结果"].astype(str).str.contains("合格|OK", case=False, na=False)))
            ].copy()
            if fabric.empty:
                continue
            issue = np.where(
                fabric["总扣分"] > 0,
                "面料外观扣分",
                pick(fabric, "异常处理方式", "面料检验异常").fillna("面料检验异常"),
            )
            data = pd.DataFrame(
                {
                    "batch": pick(fabric, "单号", ""),
                    "material_supplier": pick(fabric, "供应商", "未记录"),
                    "customer": pick(fabric, "客户名称", "Decathlon"),
                    "material_name": pick(fabric, "面料型号", ""),
                    "material_color": pick(fabric, "客户花色号", ""),
                    "material_qty": pick(fabric, "送货总数", 0),
                    "unit": "fabric",
                    "issue": issue,
                    "decision": pick(fabric, "检验结果", "未记录"),
                    "date": pick(fabric, "检验日期", pd.NaT),
                    "remark": pick(fabric, "外观检验详情", ""),
                    "extra": fabric["总扣分"],
                    "factory_code": "TF",
                    "factory_name": tf_cfg.get("name", "TF / 腾飞"),
                    "supplier": tf_cfg.get("supplier", "衡阳腾飞"),
                    "material_type": "面料",
                    "source_file": str(rel),
                }
            )
        else:
            continue

        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data["material_qty"] = pd.to_numeric(data["material_qty"], errors="coerce").fillna(0)
        frames.append(data)

    if not frames:
        return pd.DataFrame()

    incoming = pd.concat(frames, ignore_index=True)
    for col, default in {
        "batch": "",
        "material_supplier": "未记录",
        "material_name": "",
        "material_color": "",
        "issue": "未知问题",
        "decision": "未记录",
        "remark": "",
        "extra": "",
    }.items():
        if col not in incoming.columns:
            incoming[col] = default
        incoming[col] = incoming[col].fillna(default).astype(str)
    incoming["date"] = pd.to_datetime(incoming["date"], errors="coerce")
    if "material_qty" not in incoming.columns:
        incoming["material_qty"] = 0
    incoming["material_qty"] = pd.to_numeric(incoming["material_qty"], errors="coerce").fillna(0)
    duplicate_key = [
        "factory_code",
        "material_type",
        "date",
        "batch",
        "material_supplier",
        "material_name",
        "material_color",
        "material_qty",
        "issue",
        "decision",
        "extra",
    ]
    incoming = incoming.drop_duplicates(subset=duplicate_key, keep="last").reset_index(drop=True)
    return incoming


@st.cache_data(show_spinner=False)
def load_all_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return load_finished_qc(), load_customer_voice(), load_incoming_material()


# ==========================================
# 3. Metric builders
# ==========================================
def add_supplier_trend(summary: pd.DataFrame, finished: pd.DataFrame) -> pd.DataFrame:
    if finished.empty or summary.empty:
        summary["trend_delta"] = 0.0
        summary["risk_trend"] = "Stable"
        return summary

    latest_date = finished["date"].max()
    current_start = latest_date - pd.Timedelta(days=30)
    previous_start = latest_date - pd.Timedelta(days=60)

    trend_rows = []
    for factory_code, group in finished.groupby("factory_code"):
        current = group[group["date"] >= current_start]
        previous = group[(group["date"] >= previous_start) & (group["date"] < current_start)]
        current_rate = current["defect_qty"].sum() / current["qty_inspected"].sum() if current["qty_inspected"].sum() else 0
        previous_rate = previous["defect_qty"].sum() / previous["qty_inspected"].sum() if previous["qty_inspected"].sum() else 0
        trend_delta = current_rate - previous_rate
        if trend_delta > 0.002:
            trend = "Up"
        elif trend_delta < -0.002:
            trend = "Down"
        else:
            trend = "Stable"
        trend_rows.append({"factory_code": factory_code, "trend_delta": trend_delta, "risk_trend": trend})

    return summary.merge(pd.DataFrame(trend_rows), on="factory_code", how="left")


def compute_supplier_summary(
    finished: pd.DataFrame,
    voice: pd.DataFrame,
    incoming: pd.DataFrame,
    risk_settings: dict,
) -> pd.DataFrame:
    if finished.empty:
        return pd.DataFrame()

    summary = (
        finished.groupby(["factory_code", "factory_name", "supplier"], as_index=False)
        .agg(
            qty_inspected=("qty_inspected", "sum"),
            defect_qty=("defect_qty", "sum"),
            scrap_qty=("scrap_qty", "sum"),
            product_count=("product_key", pd.Series.nunique),
            process_count=("process", pd.Series.nunique),
            work_order_count=("work_order", pd.Series.nunique),
            latest_date=("date", "max"),
        )
    )
    summary["defect_rate"] = safe_rate(summary["defect_qty"], summary["qty_inspected"])
    summary["rft"] = 1 - summary["defect_rate"]
    summary["qc_score"] = summary.apply(
        lambda row: min(
            row["defect_rate"]
            / max(float(settings_for_factory(risk_settings, row["factory_code"]).get("qc_benchmark_pct", 4.0)) / 100, 0.0001)
            * 100,
            100,
        ),
        axis=1,
    )

    if not voice.empty:
        voice_summary = (
            voice.groupby("factory_code", as_index=False)
            .agg(
                avg_rpm=("rpm_now", "mean"),
                avg_score=("avg_score_now", "mean"),
                returned_now=("returned_now", "sum"),
                nqc_now=("nqc_now", "sum"),
                customer_score=("customer_score", "mean"),
                voice_products=("product_key", pd.Series.nunique),
                intern_voice_count=("intern_voice_count", "sum"),
            )
        )
        summary = summary.merge(voice_summary, on="factory_code", how="left")
    else:
        summary["customer_score"] = np.nan

    if not incoming.empty:
        incoming_summary = (
            incoming.groupby("factory_code", as_index=False)
            .agg(
                incoming_issues=("issue", "count"),
                incoming_returns=("decision", lambda s: s.astype(str).str.contains("退货|Reject", case=False, na=False).sum()),
                material_suppliers=("material_supplier", pd.Series.nunique),
            )
        )
        incoming_summary["incoming_score"] = incoming_summary.apply(
            lambda row: min(
                row["incoming_returns"]
                / max(float(settings_for_factory(risk_settings, row["factory_code"]).get("incoming_reject_cap", 25)), 1)
                * 70
                + row["incoming_issues"]
                / max(float(settings_for_factory(risk_settings, row["factory_code"]).get("incoming_issue_cap", 120)), 1)
                * 30,
                100,
            ),
            axis=1,
        )
        summary = summary.merge(incoming_summary, on="factory_code", how="left")
    else:
        summary["incoming_score"] = np.nan

    for col in ["customer_score", "avg_rpm", "incoming_score", "intern_voice_count"]:
        if col not in summary.columns:
            summary[col] = np.nan
    for col in ["voice_products", "intern_voice_count", "incoming_issues", "incoming_returns", "material_suppliers"]:
        if col not in summary.columns:
            summary[col] = 0
        summary[col] = summary[col].fillna(0)
    summary["intern_voice_score"] = summary.apply(
        lambda row: intern_voice_risk_score(row["intern_voice_count"], settings_for_factory(risk_settings, row["factory_code"])),
        axis=1,
    )
    summary["rpm_score"] = summary.apply(
        lambda row: rpm_risk_score(row.get("avg_rpm", 0), settings_for_factory(risk_settings, row["factory_code"])),
        axis=1,
    )
    summary["client_score"] = summary.apply(
        lambda row: weighted_score(
            row,
            normalized_weights(settings_for_factory(risk_settings, row["factory_code"]).get("client_weights", DEFAULT_RISK_SETTINGS["client_weights"])),
        ),
        axis=1,
    ).clip(0, 100)
    summary["production_score"] = summary["qc_score"]

    summary["risk_score"] = summary.apply(
        lambda row: weighted_score(
            row,
            normalized_weights(
                settings_for_factory(risk_settings, row["factory_code"]).get(
                    "supplier_weights", DEFAULT_RISK_SETTINGS["supplier_weights"]
                )
            ),
        ),
        axis=1,
    ).clip(0, 100)
    summary["risk_level"] = summary["risk_score"].map(risk_level)
    summary = add_supplier_trend(summary, finished)
    return summary.sort_values("risk_score", ascending=False)


def compute_top_defects(finished: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    bad = finished[finished["defect_qty"] > 0].copy()
    if bad.empty:
        return pd.DataFrame(columns=group_cols + ["top_defect", "top_defect_qty"])
    defects = (
        bad.groupby(group_cols + ["defect_type"], as_index=False)["defect_qty"]
        .sum()
        .sort_values(group_cols + ["defect_qty"], ascending=[True] * len(group_cols) + [False])
    )
    defects = defects.drop_duplicates(group_cols)
    return defects.rename(columns={"defect_type": "top_defect", "defect_qty": "top_defect_qty"})


def compute_product_summary(finished: pd.DataFrame, voice: pd.DataFrame, risk_settings: dict) -> pd.DataFrame:
    qc = pd.DataFrame()
    if not finished.empty:
        qc = (
            finished.groupby(["factory_code", "factory_name", "supplier", "product_key", "product_code", "product_label"], as_index=False)
            .agg(
                qty_inspected=("qty_inspected", "sum"),
                defect_qty=("defect_qty", "sum"),
                process_count=("process", pd.Series.nunique),
                work_order_count=("work_order", pd.Series.nunique),
                latest_date=("date", "max"),
            )
        )
        qc["defect_rate"] = safe_rate(qc["defect_qty"], qc["qty_inspected"])
        top_defects = compute_top_defects(
            finished,
            ["factory_code", "product_key", "product_code", "product_label"],
        )
        qc = qc.merge(top_defects, on=["factory_code", "product_key", "product_code", "product_label"], how="left")

    cust = pd.DataFrame()
    if not voice.empty:
        cust = (
            voice.groupby(["factory_code", "factory_name", "supplier", "product_key"], as_index=False)
            .agg(
                voice_product_code=("product_code", "first"),
                voice_product_name=("product_name", "first"),
                hierarchy_2=("hierarchy_2", "first"),
                rpm_now=("rpm_now", "mean"),
                rpm_prev=("rpm_prev", "mean"),
                delta_rpm=("delta_rpm", "mean"),
                avg_score_now=("avg_score_now", "mean"),
                returned_now=("returned_now", "sum"),
                nqc_now=("nqc_now", "sum"),
                customer_score=("customer_score", "mean"),
                intern_voice_count=("intern_voice_count", "sum"),
            )
        )

    if qc.empty and cust.empty:
        return pd.DataFrame()
    if qc.empty:
        product = cust.copy()
    elif cust.empty:
        product = qc.copy()
        product["customer_score"] = np.nan
    else:
        product = qc.merge(
            cust,
            on=["factory_code", "factory_name", "supplier", "product_key"],
            how="outer",
        )

    product["product_code"] = product.get("product_code", pd.Series(index=product.index, dtype=object)).fillna(
        product.get("voice_product_code", pd.Series(index=product.index, dtype=object))
    )
    product["product_label"] = product.get("product_label", pd.Series(index=product.index, dtype=object)).fillna(
        product.get("voice_product_name", pd.Series(index=product.index, dtype=object))
    )
    product["qty_inspected"] = product.get("qty_inspected", 0).fillna(0)
    product["defect_qty"] = product.get("defect_qty", 0).fillna(0)
    product["defect_rate"] = product.get("defect_rate", np.nan)
    product["qc_score"] = product.apply(
        lambda row: min(
            (row["defect_rate"] if pd.notna(row.get("defect_rate")) else 0)
            / max(float(settings_for_factory(risk_settings, row["factory_code"]).get("qc_benchmark_pct", 4.0)) / 100, 0.0001)
            * 100,
            100,
        ),
        axis=1,
    )
    product.loc[product["qty_inspected"] == 0, "qc_score"] = np.nan
    if "customer_score" not in product.columns:
        product["customer_score"] = np.nan
    if "intern_voice_count" not in product.columns:
        product["intern_voice_count"] = 0
    product["intern_voice_count"] = product["intern_voice_count"].fillna(0)
    if "rpm_now" not in product.columns:
        product["rpm_now"] = np.nan
    product["rpm_score"] = product.apply(
        lambda row: rpm_risk_score(row.get("rpm_now", 0), settings_for_factory(risk_settings, row["factory_code"])),
        axis=1,
    )
    product["intern_voice_score"] = product.apply(
        lambda row: intern_voice_risk_score(row.get("intern_voice_count", 0), settings_for_factory(risk_settings, row["factory_code"])),
        axis=1,
    )
    product["client_score"] = product.apply(
        lambda row: weighted_score(
            row,
            normalized_weights(settings_for_factory(risk_settings, row["factory_code"]).get("client_weights", DEFAULT_RISK_SETTINGS["client_weights"])),
        ),
        axis=1,
    ).clip(0, 100)
    product["production_score"] = product["qc_score"]

    product["risk_score"] = product.apply(
        lambda row: weighted_score(
            row,
            normalized_weights(
                settings_for_factory(risk_settings, row["factory_code"]).get(
                    "product_weights", DEFAULT_RISK_SETTINGS["product_weights"]
                )
            ),
        ),
        axis=1,
    ).clip(0, 100)
    product["risk_level"] = product["risk_score"].map(risk_level)

    reasons = []
    for _, row in product.iterrows():
        row_reasons = []
        if pd.notna(row.get("defect_rate")) and row.get("defect_rate", 0) >= 0.02:
            row_reasons.append(t("QC 不良率高", "High QC defect rate"))
        if pd.notna(row.get("rpm_now")) and row.get("rpm_now", 0) >= 1000:
            row_reasons.append(t("RPM 高", "High RPM"))
        if pd.notna(row.get("delta_rpm")) and row.get("delta_rpm", 0) > 0:
            row_reasons.append(t("RPM 上升", "RPM increasing"))
        if pd.notna(row.get("avg_score_now")) and row.get("avg_score_now", 5) < 4.5:
            row_reasons.append(t("客户评分偏低", "Low customer score"))
        if row.get("intern_voice_count", 0) > 0:
            row_reasons.append(f"Intern Voice x {int(row.get('intern_voice_count', 0))}")
        if pd.notna(row.get("top_defect")):
            row_reasons.append(f"{t('Top 疵点', 'Top defect')}: {row.get('top_defect')}")
        reasons.append(" / ".join(row_reasons) if row_reasons else t("无单一突出触发项", "No single dominant trigger"))
    product["alert_reason"] = reasons
    return product.sort_values("risk_score", ascending=False)


def compute_process_summary(finished: pd.DataFrame, risk_settings: dict) -> pd.DataFrame:
    if finished.empty:
        return pd.DataFrame()

    process = (
        finished.groupby(["factory_code", "factory_name", "supplier", "process"], as_index=False)
        .agg(
            qty_inspected=("qty_inspected", "sum"),
            defect_qty=("defect_qty", "sum"),
            product_count=("product_key", pd.Series.nunique),
            worker_team_count=("worker_team", pd.Series.nunique),
        )
    )
    process = process[process["qty_inspected"] > 0].copy()
    process["defect_rate"] = safe_rate(process["defect_qty"], process["qty_inspected"])
    process["risk_score"] = process.apply(
        lambda row: min(
            row["defect_rate"]
            / max(float(settings_for_factory(risk_settings, row["factory_code"]).get("process_benchmark_pct", 5.0)) / 100, 0.0001)
            * 100,
            100,
        ),
        axis=1,
    )
    process["risk_level"] = process["risk_score"].map(risk_level)

    top_defects = compute_top_defects(finished, ["factory_code", "process"])
    process = process.merge(top_defects, on=["factory_code", "process"], how="left")
    return process.sort_values("risk_score", ascending=False)


def compute_worker_clusters(finished: pd.DataFrame) -> pd.DataFrame:
    if finished.empty:
        return pd.DataFrame()

    worker = (
        finished.groupby(["factory_code", "worker_team", "process"], as_index=False)
        .agg(qty_inspected=("qty_inspected", "sum"), defect_qty=("defect_qty", "sum"))
    )
    worker = worker[worker["qty_inspected"] >= 20].copy()
    if worker.empty:
        return worker
    worker["defect_rate"] = safe_rate(worker["defect_qty"], worker["qty_inspected"])

    if len(worker) >= 6:
        rate_rank = worker["defect_rate"].rank(pct=True)
        qty_rank = np.log1p(worker["qty_inspected"]).rank(pct=True)
        worker["cluster_score"] = rate_rank * 0.75 + qty_rank * 0.25
        worker["skill_tag"] = np.select(
            [
                worker["cluster_score"] >= worker["cluster_score"].quantile(0.72),
                worker["cluster_score"] >= worker["cluster_score"].quantile(0.38),
            ],
            [t("重点改善组", "Priority"), t("观察组", "Watch")],
            default=t("稳定组", "Stable"),
        )
    else:
        worker["skill_tag"] = np.where(worker["defect_rate"] > worker["defect_rate"].median(), t("观察组", "Watch"), t("稳定组", "Stable"))
    return worker.sort_values("defect_rate", ascending=False)


def compute_cap_effectiveness(finished: pd.DataFrame) -> pd.DataFrame:
    if finished.empty:
        return pd.DataFrame()

    latest_date = finished["date"].max()
    after_start = latest_date - pd.Timedelta(days=45)
    before_start = after_start - pd.Timedelta(days=45)
    before = finished[(finished["date"] >= before_start) & (finished["date"] < after_start)]
    after = finished[finished["date"] >= after_start]
    if before.empty or after.empty:
        return pd.DataFrame()

    keys = ["factory_code", "process"]
    before_metrics = before.groupby(keys, as_index=False).agg(before_qty=("qty_inspected", "sum"), before_defects=("defect_qty", "sum"))
    after_metrics = after.groupby(keys, as_index=False).agg(after_qty=("qty_inspected", "sum"), after_defects=("defect_qty", "sum"))
    eff = before_metrics.merge(after_metrics, on=keys, how="inner")
    eff = eff[(eff["before_qty"] > 0) & (eff["after_qty"] > 0)].copy()
    eff["before_rate"] = safe_rate(eff["before_defects"], eff["before_qty"])
    eff["after_rate"] = safe_rate(eff["after_defects"], eff["after_qty"])
    eff = eff[eff["before_defects"] >= 5].copy()
    if eff.empty:
        return pd.DataFrame()

    improvement = (eff["before_rate"] - eff["after_rate"]) / eff["before_rate"].replace(0, np.nan)
    eff["effectiveness_score"] = np.clip(50 + improvement.fillna(0) * 60, 0, 100)
    eff["recurrence"] = np.where(eff["after_defects"] > 0, t("有复发", "Recurring"), t("未复发", "No recurrence"))
    eff["next_decision"] = np.where(
        eff["effectiveness_score"] >= 75,
        t("关闭后继续监控", "Close with monitoring"),
        np.where(eff["effectiveness_score"] >= 55, t("继续观察两周", "Monitor two weeks"), t("升级 CAP", "Escalate CAP")),
    )
    return eff.sort_values("effectiveness_score", ascending=True).head(8)


def detect_abnormal_work_orders(finished: pd.DataFrame) -> pd.DataFrame:
    if len(finished) < 30:
        return pd.DataFrame()

    model_data = finished[["qty_inspected", "defect_qty", "defect_rate"]].fillna(0).copy()
    if model_data["defect_qty"].sum() == 0:
        return pd.DataFrame()

    features = pd.DataFrame(
        {
            "log_qty": np.log1p(model_data["qty_inspected"].clip(lower=0)),
            "defect_rate": model_data["defect_rate"].clip(lower=0),
            "log_defects": np.log1p(model_data["defect_qty"].clip(lower=0)),
        },
        index=model_data.index,
    )
    median = features.median()
    mad = (features - median).abs().median().replace(0, np.nan)
    robust_z = ((features - median).abs() / (mad * 1.4826)).replace([np.inf, -np.inf], np.nan).fillna(0)
    model_data["anomaly_score"] = robust_z["defect_rate"] * 0.55 + robust_z["log_defects"] * 0.35 + robust_z["log_qty"] * 0.10
    threshold = max(float(model_data["anomaly_score"].quantile(0.96)), 2.5)
    abnormal = finished.loc[model_data["anomaly_score"] >= threshold].copy()
    if abnormal.empty:
        return pd.DataFrame()
    abnormal["anomaly_score"] = model_data.loc[abnormal.index, "anomaly_score"]
    return abnormal.sort_values("defect_rate", ascending=False)


def compute_pareto(df: pd.DataFrame, category_col: str, value_col: str, limit: int = 12) -> pd.DataFrame:
    if df.empty or category_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame()

    pareto = (
        df.groupby(category_col, as_index=False)[value_col]
        .sum()
        .sort_values(value_col, ascending=False)
        .head(limit)
    )
    total = pareto[value_col].sum()
    if total <= 0:
        return pd.DataFrame()
    pareto["share"] = pareto[value_col] / total
    pareto["cum_share"] = pareto[value_col].cumsum() / total
    return pareto


def compute_process_shift(finished: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    if finished.empty or finished["date"].dropna().empty:
        return pd.DataFrame()

    latest = finished["date"].max()
    current_start = latest - pd.Timedelta(days=days)
    previous_start = current_start - pd.Timedelta(days=days)
    current = finished[finished["date"] >= current_start]
    previous = finished[(finished["date"] >= previous_start) & (finished["date"] < current_start)]
    if current.empty or previous.empty:
        return pd.DataFrame()

    keys = ["factory_code", "factory_name", "process"]
    cur = current.groupby(keys, as_index=False).agg(cur_qty=("qty_inspected", "sum"), cur_defects=("defect_qty", "sum"))
    prev = previous.groupby(keys, as_index=False).agg(prev_qty=("qty_inspected", "sum"), prev_defects=("defect_qty", "sum"))
    shift = cur.merge(prev, on=keys, how="inner")
    shift = shift[(shift["cur_qty"] >= 50) & (shift["prev_qty"] >= 50)].copy()
    if shift.empty:
        return shift
    shift["cur_rate"] = safe_rate(shift["cur_defects"], shift["cur_qty"])
    shift["prev_rate"] = safe_rate(shift["prev_defects"], shift["prev_qty"])
    shift["delta_rate"] = shift["cur_rate"] - shift["prev_rate"]
    shift["process_view"] = shift["factory_code"] + " / " + shift["process"].astype(str)
    shift["change_type"] = np.where(shift["delta_rate"] >= 0, t("上升", "Worse"), t("下降", "Better"))
    return shift.sort_values("delta_rate", ascending=False)


def compute_weekly_material_process(finished: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    if finished.empty or incoming.empty:
        return pd.DataFrame()

    qc = finished.copy()
    qc["week"] = qc["date"].dt.to_period("W").astype(str)
    qc_week = qc.groupby(["factory_code", "week"], as_index=False).agg(qty=("qty_inspected", "sum"), defects=("defect_qty", "sum"))
    qc_week["defect_rate"] = safe_rate(qc_week["defects"], qc_week["qty"])

    mat = incoming.copy()
    mat["week"] = mat["date"].dt.to_period("W").astype(str)
    mat_week = mat.groupby(["factory_code", "week"], as_index=False).size().rename(columns={"size": "material_issues"})

    weekly = qc_week.merge(mat_week, on=["factory_code", "week"], how="left")
    weekly["material_issues"] = weekly["material_issues"].fillna(0)
    weekly["factory"] = weekly["factory_code"].map(lambda code: FACTORIES.get(code, {}).get("name", code))
    return weekly


# ==========================================
# 4. Render helpers
# ==========================================
def chart_layout(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=38, b=20),
        legend_title_text="",
        hoverlabel=dict(align="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def plotly_hover_labels() -> dict[str, str]:
    return {
        "factory": t("工厂", "Factory"),
        "factory_code": t("工厂代码", "Factory Code"),
        "factory_name": t("工厂", "Factory"),
        "supplier": t("供应商", "Supplier"),
        "risk_level": t("风险等级", "Risk Level"),
        "risk_score": t("风险分", "Risk Score"),
        "production_score": t("生产端风险", "Production Risk"),
        "client_score": t("客户端风险", "Client Risk"),
        "rpm_score": t("RPM 风险分", "RPM Risk"),
        "intern_voice_score": t("Intern Voice 风险分", "Intern Voice Risk"),
        "component": t("风险分项", "Risk Component"),
        "metric": t("指标", "Metric"),
        "score": t("分数", "Score"),
        "inspection_stage": t("检验阶段", "Inspection Stage"),
        "month": t("月份", "Month"),
        "process": t("工序", "Process"),
        "process_view": t("工厂 / 工序", "Factory / Process"),
        "defect_type": t("疵点类型", "Defect Type"),
        "defect_qty": t("疵点数", "Defects"),
        "qty_inspected": t("检验数量", "Inspected Qty"),
        "defect_rate": t("不良率", "Defect Rate"),
        "qc_rate": t("QC 不良率", "QC Defect Rate"),
        "customer_signal": t("客户端风险信号", "Client Risk Signal"),
        "risk_zone": t("风险分区", "Risk Zone"),
        "axis_note": t("坐标说明", "Axis Note"),
        "product_code": t("CC / 款式", "CC / Style"),
        "product_label": t("产品名称 / 颜色", "Product / Color"),
        "work_order": t("工单", "Work Order"),
        "material_type": t("材料类型", "Material Type"),
        "material_issues": t("来料问题数", "Material Issues"),
        "issue_view": t("工厂 / 质量问题点", "Factory / Issue"),
        "supplier_view": t("来料供应商", "Material Supplier"),
        "size": t("数量", "Count"),
        "combined_signal": t("组合信号强度", "Combined Signal"),
        "rpm_now": "RPM N0",
        "intern_voice_count": "Intern Voice",
        "delta_rpm": t("RPM 变化", "RPM Change"),
        "returned_now": t("退货数", "Returns"),
        "nqc_now": "NQC",
        "avg_score_now": t("客户评分", "Customer Score"),
        "change_type": t("变化方向", "Change"),
        "delta_rate": t("不良率变化", "Defect-Rate Change"),
        "week": t("周", "Week"),
        "defects": t("疵点数", "Defects"),
        "effectiveness_score": t("有效性评分", "Effectiveness Score"),
        "recurrence": t("复发状态", "Recurrence"),
    }


def plotly_hover_formats() -> dict[str, str]:
    return {
        t("综合风险分", "Risk Score"): ".1f",
        t("风险分", "Risk Score"): ".1f",
        t("分数", "Score"): ".1f",
        t("分项风险分", "Component Risk"): ".1f",
        t("工序风险分", "Process Risk Score"): ".1f",
        t("组合信号强度", "Combined signal"): ".1f",
        t("客户端风险信号", "Client Risk Signal"): ".1f",
        t("有效性评分", "Effectiveness score"): ".1f",
        t("不良率", "Defect Rate"): ".2%",
        t("QC 不良率", "QC Defect Rate"): ".2%",
        t("过程/成品不良率", "QC defect rate"): ".2%",
        t("不良率变化", "Defect-rate change"): "+.2%",
        t("检验数量", "Inspected Qty"): ",.0f",
        t("疵点数", "Defects"): ",.0f",
        t("数量", "Count"): ",.0f",
        t("批次数", "Batches"): ",.0f",
        t("问题批次", "Issue Batches"): ",.0f",
        t("来料问题数", "Material Issues"): ",.0f",
        "RPM N0": ",.0f",
        "Intern Voice": ",.0f",
        t("RPM 变化", "RPM Change"): ",.0f",
        t("退货数", "Returns"): ",.0f",
        "NQC": ",.0f",
        t("客户评分", "Customer Score"): ".2f",
    }


def clean_plotly_hover(fig: go.Figure) -> go.Figure:
    labels = plotly_hover_labels()
    formats = plotly_hover_formats()
    level_names = {level: risk_level_text(level) for level in LEVEL_COLORS}

    for trace in fig.data:
        if trace.name in level_names:
            trace.name = level_names[trace.name]

        template = getattr(trace, "hovertemplate", None)
        if not template:
            continue

        # Plotly Express repeats the visible bar label as "text=..." in hover.
        template = re.sub(r"(?:^|<br>)[^=<]*=%\{text[^}]*\}", "", template)
        for field, label in labels.items():
            template = re.sub(
                rf"(^|<br>){re.escape(field)}=",
                lambda match, localized=label: f"{match.group(1)}{localized}=",
                template,
            )
        risk_label = labels["risk_level"]
        for level, localized_level in level_names.items():
            template = template.replace(f"{risk_label}={level}", f"{risk_label}={localized_level}")
        for label, number_format in formats.items():
            template = re.sub(
                rf"({re.escape(label)}=)%\{{([^}}:]+)(?::[^}}]+)?\}}",
                lambda match, fmt=number_format: f"{match.group(1)}%{{{match.group(2)}:{fmt}}}",
                template,
            )
        trace.hovertemplate = template

    return fig


def plot_chart(fig: go.Figure, height: int = 420):
    st.plotly_chart(
        chart_layout(clean_plotly_hover(fig), height),
        config={"displayModeBar": False, "responsive": True},
    )


def dataframe_with_format(df: pd.DataFrame, column_config: dict | None = None, height: int = 360):
    display_labels = {
        "factory_code": t("工厂代码", "Factory Code"),
        "factory_name": t("工厂", "Factory"),
        "supplier": t("供应商", "Supplier"),
        "product_code": t("CC / 款式", "CC / Style"),
        "product_label": t("产品名称 / 颜色", "Product / Color"),
        "risk_level": t("风险等级", "Risk Level"),
        "risk_score": t("风险分", "Risk Score"),
        "production_score": t("生产端风险", "Production Risk"),
        "client_score": t("客户端风险", "Client Risk"),
        "rpm_score": t("RPM 风险分", "RPM Risk"),
        "intern_voice_score": t("Intern Voice 风险分", "Intern Voice Risk"),
        "qty_inspected": t("检验数量", "Inspected Qty"),
        "defect_qty": t("疵点数", "Defects"),
        "defect_rate": t("不良率", "Defect Rate"),
        "top_defect": t("主要疵点", "Top Defect"),
        "rpm_now": "RPM N0",
        "delta_rpm": t("RPM 变化", "RPM Change"),
        "avg_score_now": t("客户评分", "Customer Score"),
        "intern_voice_count": "Intern Voice",
        "alert_reason": t("风险原因", "Risk Reason"),
        "process": t("工序", "Process"),
        "worker_team": t("班组 / 岗位", "Team / Position"),
        "work_order": t("工单", "Work Order"),
        "material_type": t("材料类型", "Material Type"),
        "material_supplier": t("来料供应商", "Material Supplier"),
        "issue": t("质量问题点", "Quality Issue"),
        "decision": t("判定", "Decision"),
        "risk_trend": t("趋势", "Trend"),
    }
    resolved_config = dict(column_config or {})
    for column in df.columns:
        if column in display_labels and column not in resolved_config:
            resolved_config[column] = st.column_config.Column(display_labels[column])
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        height=height,
        column_config=resolved_config,
    )


def render_requirement_mapping(rows: list[dict[str, str]]):
    header = [
        t("验收项", "Acceptance Item"),
        t("目标", "Target"),
        t("当前状态", "Current Status"),
        t("判定", "Result"),
    ]
    rows_html = [
        "<table class='mapping-table'>",
        "<thead><tr>",
        *(f"<th>{html.escape(col)}</th>" for col in header),
        "</tr></thead><tbody>",
    ]
    for row in rows:
        level = row.get("level", "watch")
        status_text = row.get("status", t("需关注", "Watch"))
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(str(row['item']))}</td>"
            f"<td class='mapping-target'>{html.escape(str(row['target']))}</td>"
            f"<td class='mapping-current {level}'>{html.escape(str(row['current']))}</td>"
            f"<td><span class='status-badge {level}'>{html.escape(status_text)}</span></td>"
            "</tr>"
        )
    rows_html.append("</tbody></table>")
    st.markdown("".join(rows_html), unsafe_allow_html=True)


def render_ai_card(title: str, priority: str, evidence: Iterable[str], root_cause: str, action: str, owner: str, timeline: str):
    evidence_html = "<br>".join(f"- {item}" for item in evidence)
    st.markdown(
        f"""
        <div class="poc-card">
            <h4>{title}</h4>
            <div class="poc-small"><b>{t('优先级', 'Priority')}:</b> {priority}</div>
            <div class="poc-small"><b>{t('证据', 'Evidence')}:</b><br>{evidence_html}</div>
            <div class="poc-small"><b>{t('可能原因', 'Possible Root Cause')}:</b> {root_cause}</div>
            <div class="poc-small"><b>{t('建议行动', 'Recommended Action')}:</b> {action}</div>
            <div class="poc-small"><b>{t('Owner / Timeline', 'Owner / Timeline')}:</b> {owner} / {timeline}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def source_date_range(df: pd.DataFrame, date_col: str = "date") -> str:
    if df.empty or date_col not in df.columns:
        return "-"
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if dates.empty:
        return "-"
    return f"{dates.min().date()} - {dates.max().date()}"


def render_hero(start_date: dt.date, end_date: dt.date, supplier_count: int, source_count: int):
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-kicker">NEA QUALITY DASHBOARD</div>
            <div class="hero-title">{t('迪卡侬NEA质量看板', 'Decathlon NEA Quality Dashboard')}</div>
            <div class="hero-meta">
                <span class="hero-chip">{t('供应商', 'Suppliers')}: {supplier_count}</span>
                <span class="hero-chip">{t('数据源', 'Data sources')}: {source_count}</span>
                <span class="hero-chip">{t('数据周期', 'Data period')}: {start_date} - {end_date}</span>
                <span class="hero-chip">QC + RPM + Intern Voice + Material</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(cards: list[dict[str, str]]):
    html = ['<div class="kpi-grid">']
    for card in cards:
        html.append(
            f"<div class=\"kpi-card {card.get('level', 'medium')}\">"
            f"<div class=\"kpi-label\">{card['label']}</div>"
            f"<div class=\"kpi-value\">{card['value']}</div>"
            f"<div class=\"kpi-note\">{card['note']}</div>"
            f"</div>"
        )
    html.append("</div>")
    st.markdown("\n".join(html), unsafe_allow_html=True)


def render_signal_cards(cards: list[dict[str, str]]):
    html = ['<div class="signal-grid">']
    for card in cards:
        level = card.get("level", "medium")
        html.append(
            f"<div class=\"signal-card {level}\">"
            f"<span class=\"risk-pill {level}\">{card['pill']}</span>"
            f"<div class=\"signal-kicker\">{card['kicker']}</div>"
            f"<div class=\"signal-title\">{card['title']}</div>"
            f"<div class=\"signal-value\">{card['value']}</div>"
            f"<div class=\"signal-evidence\">{card['evidence']}</div>"
            f"</div>"
        )
    html.append("</div>")
    st.markdown("\n".join(html), unsafe_allow_html=True)


def product_alert_cards(product_summary: pd.DataFrame, limit: int = 4) -> list[dict[str, str]]:
    cards = []
    for _, row in product_summary.head(limit).iterrows():
        level = risk_class(row.get("risk_level", "Medium"))
        evidence = [
            f"{t('QC不良率', 'QC defect')} {pct(row.get('defect_rate', np.nan))}",
            f"RPM {num(row.get('rpm_now', np.nan))}",
        ]
        if row.get("intern_voice_count", 0) > 0:
            evidence.append(f"Intern Voice {int(row.get('intern_voice_count', 0))}")
        evidence.append(f"{t('Top问题', 'Top issue')} {row.get('top_defect', '-')}")
        cards.append(
            {
                "level": level,
                "pill": risk_level_text(row.get("risk_level", "Medium")),
                "kicker": f"{row.get('factory_code', '')} / CC {row.get('product_code', '-')}",
                "title": str(row.get("product_label", row.get("voice_product_name", "")))[:46],
                "value": f"{row.get('risk_score', 0):.1f}",
                "evidence": "<br>".join(evidence),
            }
        )
    return cards


def prepare_product_risk_view(product_summary: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    view = product_summary.copy()
    view["qc_rate"] = pd.to_numeric(view.get("defect_rate", 0), errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    view["customer_signal"] = pd.to_numeric(view.get("client_score", view.get("customer_score", 0)), errors="coerce").fillna(0).clip(0, 100)
    view["qty_inspected"] = pd.to_numeric(view.get("qty_inspected", 0), errors="coerce").fillna(0)
    view["defect_qty"] = pd.to_numeric(view.get("defect_qty", 0), errors="coerce").fillna(0)
    view["intern_voice_count"] = pd.to_numeric(view.get("intern_voice_count", 0), errors="coerce").fillna(0)

    qc_threshold = 0.02
    customer_threshold = 35
    zone_double = t("QC + 客户端双高", "QC + client high")
    zone_qc = t("QC 高", "QC high")
    zone_customer = t("客户端信号高", "Client signal high")
    zone_normal = t("常规关注", "Routine")
    view["risk_zone"] = np.select(
        [
            (view["qc_rate"] >= qc_threshold) & (view["customer_signal"] >= customer_threshold),
            view["qc_rate"] >= qc_threshold,
            view["customer_signal"] >= customer_threshold,
        ],
        [zone_double, zone_qc, zone_customer],
        default=zone_normal,
    )

    positive_qc = view.loc[view["qc_rate"] > 0, "qc_rate"]
    x_cap = positive_qc.quantile(0.95) * 1.2 if not positive_qc.empty else 0.04
    x_cap = float(np.clip(x_cap, 0.04, 0.12))
    y_cap = view["customer_signal"].quantile(0.95) * 1.15 if not view.empty else 45
    y_cap = float(np.clip(y_cap, 45, 100))

    view["qc_rate_plot"] = view["qc_rate"].clip(upper=x_cap)
    view["customer_signal_plot"] = view["customer_signal"].clip(upper=y_cap)
    view["axis_note"] = np.where(
        (view["qc_rate"] > x_cap) | (view["customer_signal"] > y_cap),
        t("超出聚焦区", "Outside focus range"),
        t("聚焦区内", "In focus range"),
    )
    view["plot_size"] = np.log1p(view["qty_inspected"].clip(lower=0) + view["defect_qty"].clip(lower=0) * 20) + 4
    return view, x_cap, y_cap


# ==========================================
# 5. Load data and sidebar filters
# ==========================================
with st.spinner(t("正在读取供应商质量数据...", "Loading supplier quality data...")):
    finished_all, voice_all, incoming_all = load_all_data()

if finished_all.empty:
    st.error(t("未能读取本地成品检验数据，请检查各 Database 文件夹。", "No finished QC data was loaded."))
    st.stop()

st.sidebar.radio("Language / 语言", ["中文", "English"], key="lang", horizontal=True)
st.sidebar.markdown("---")
st.sidebar.markdown(t("**数据筛选**", "**Filters**"))

factory_options = list(FACTORIES.keys())
selected_factories = st.sidebar.multiselect(
    t("供应商 / 工厂", "Supplier / Factory"),
    factory_options,
    default=factory_options,
    format_func=lambda code: FACTORIES[code]["name"],
)
if not selected_factories:
    selected_factories = factory_options

valid_dates = finished_all["date"].dropna()
min_date = valid_dates.min().date()
max_date = valid_dates.max().date()
default_start = max(min_date, max_date - dt.timedelta(days=180))
date_range = st.sidebar.date_input(
    t("检验日期", "Inspection Date"),
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, max_date

stage_options = sorted(finished_all["inspection_stage"].dropna().unique().tolist())
selected_stages = st.sidebar.multiselect(
    t("检验阶段", "Inspection Stage"),
    stage_options,
    default=stage_options,
)

process_options = sorted(finished_all["process"].dropna().unique().tolist())
selected_processes = st.sidebar.multiselect(
    t("关键工序", "Key Process"),
    process_options,
    default=[],
)

product_search = st.sidebar.text_input(t("CC / 款式搜索", "CC / Product Search"), "")
risk_settings = current_risk_settings()
active_profile_label = risk_profile_label(risk_settings.get("_active_profile", "__default__"))
supplier_prod_w = effective_weight_pct(risk_settings, "supplier_weights", "production_score")
supplier_client_w = effective_weight_pct(risk_settings, "supplier_weights", "client_score")

finished = finished_all[
    (finished_all["factory_code"].isin(selected_factories))
    & (finished_all["date"].dt.date >= start_date)
    & (finished_all["date"].dt.date <= end_date)
]
if selected_stages:
    finished = finished[finished["inspection_stage"].isin(selected_stages)]
if selected_processes:
    finished = finished[finished["process"].isin(selected_processes)]
if product_search.strip():
    needle = product_search.strip().lower()
    finished = finished[
        finished["product_code"].astype(str).str.lower().str.contains(needle, na=False)
        | finished["product_label"].astype(str).str.lower().str.contains(needle, na=False)
    ]

voice = voice_all[voice_all["factory_code"].isin(selected_factories)].copy()
if product_search.strip():
    needle = product_search.strip().lower()
    voice = voice[
        voice["product_raw"].astype(str).str.lower().str.contains(needle, na=False)
        | voice["product_code"].astype(str).str.lower().str.contains(needle, na=False)
    ]

incoming = incoming_all[
    (incoming_all["factory_code"].isin(selected_factories))
    & (incoming_all["date"].dt.date >= start_date)
    & (incoming_all["date"].dt.date <= end_date)
].copy()

if finished.empty:
    st.warning(t("当前筛选条件下没有成品检验数据。", "No finished QC data under current filters."))
    st.stop()

supplier_summary = compute_supplier_summary(finished, voice, incoming, risk_settings)
product_summary = compute_product_summary(finished, voice, risk_settings)
process_summary = compute_process_summary(finished, risk_settings)
worker_clusters = compute_worker_clusters(finished)
defect_pareto = compute_pareto(finished[finished["defect_qty"] > 0], "defect_type", "defect_qty")

process_material_codes = [code for code in selected_factories if code in {"ZX", "TF"}]
if not process_material_codes:
    process_material_codes = ["ZX", "TF"]

pm_finished = finished_all[
    (finished_all["factory_code"].isin(process_material_codes))
    & (finished_all["date"].dt.date >= start_date)
    & (finished_all["date"].dt.date <= end_date)
].copy()
if selected_stages:
    pm_finished = pm_finished[pm_finished["inspection_stage"].isin(selected_stages)]
if selected_processes:
    pm_finished = pm_finished[pm_finished["process"].isin(selected_processes)]
if product_search.strip():
    needle = product_search.strip().lower()
    pm_finished = pm_finished[
        pm_finished["product_code"].astype(str).str.lower().str.contains(needle, na=False)
        | pm_finished["product_label"].astype(str).str.lower().str.contains(needle, na=False)
    ]
pm_incoming = incoming_all[
    (incoming_all["factory_code"].isin(process_material_codes))
    & (incoming_all["date"].dt.date >= start_date)
    & (incoming_all["date"].dt.date <= end_date)
].copy()
pm_process_summary = compute_process_summary(pm_finished, risk_settings)
pm_worker_clusters = compute_worker_clusters(pm_finished)
if not pm_incoming.empty:
    pm_incoming["issue_count"] = 1
pm_material_pareto = compute_pareto(pm_incoming, "issue", "issue_count")


# ==========================================
# 6. Header
# ==========================================
total_sources = configured_source_count()

render_hero(start_date, end_date, supplier_summary["factory_code"].nunique(), total_sources)

tabs = st.tabs(
    [
        t("01 总览", "01 Overview"),
        t("02 地图", "02 Map"),
        t("03 供应商", "03 Supplier"),
        t("04 产品", "04 Product"),
        t("05 Panel管理", "05 Panel"),
        t("06 过程/来料", "06 P/M"),
        t("07 方法", "07 Methods"),
    ]
)


# ==========================================
# 7. Executive overview
# ==========================================
with tabs[0]:
    total_qty = finished["qty_inspected"].sum()
    total_defects = finished["defect_qty"].sum()
    total_defect_rate = total_defects / total_qty if total_qty else 0
    high_supplier_count = supplier_summary[supplier_summary["risk_level"].isin(["High", "Critical"])].shape[0]
    high_product_count = product_summary[product_summary["risk_level"].isin(["High", "Critical"])].shape[0] if not product_summary.empty else 0
    top_supplier = supplier_summary.iloc[0] if not supplier_summary.empty else None
    top_product = product_summary.iloc[0] if not product_summary.empty else None
    top_process = process_summary.iloc[0] if not process_summary.empty else None
    top_material = None
    if not incoming.empty:
        top_material = incoming.groupby(["factory_code", "material_type", "issue"], as_index=False).size().sort_values("size", ascending=False).iloc[0]

    kpi_level = "critical" if high_product_count >= 20 else "high" if high_product_count >= 8 else "medium" if high_product_count else "low"
    render_kpi_cards(
        [
            {
                "label": t("覆盖供应商", "Suppliers"),
                "value": str(supplier_summary["factory_code"].nunique()),
                "note": t("ZX、DS、JS、TF 横向 benchmark", "ZX, DS, JS, TF benchmark"),
                "level": "low",
            },
            {
                "label": t("检验总数", "Inspected Qty"),
                "value": compact_num(total_qty),
                "note": f"{compact_num(total_defects)} defects captured",
                "level": "medium",
            },
            {
                "label": t("综合不良率", "Defect Rate"),
                "value": pct(total_defect_rate),
                "note": t("来自在线 / 终检统一口径", "Unified online / final QC"),
                "level": "high" if total_defect_rate >= 0.015 else "low",
            },
            {
                "label": t("高风险产品", "High-Risk Products"),
                "value": str(high_product_count),
                "note": f"{high_supplier_count} {t('个高风险供应商', 'high-risk suppliers')}",
                "level": kpi_level,
            },
        ]
    )

    left, right = st.columns([1.05, 1])
    with left:
        st.subheader(t("供应商风险排序", "Supplier Risk Ranking"))
        supplier_plot = supplier_summary.copy()
        supplier_col = t("供应商", "Supplier")
        risk_level_col = t("风险等级", "Risk Level")
        supplier_plot[supplier_col] = supplier_plot["factory_name"]
        supplier_plot[risk_level_col] = supplier_plot["risk_level"].map(risk_level_text)
        fig = px.bar(
            supplier_plot,
            x=supplier_col,
            y="risk_score",
            color=risk_level_col,
            color_discrete_map={risk_level_text(level): color for level, color in LEVEL_COLORS.items()},
            text=supplier_plot["risk_score"].round(1),
            labels={"risk_score": t("综合风险分", "Risk Score"), supplier_col: supplier_col, risk_level_col: risk_level_col},
        )
        fig.update_traces(textposition="outside")
        fig.update_yaxes(range=[0, max(100, supplier_plot["risk_score"].max() * 1.15)])
        plot_chart(fig, 380)
        st.caption(
            t(
                f"数据来源：{', '.join(selected_factories)} QC data + RPM + Intern Voice。计算逻辑：综合风险 = 生产端质量风险 {supplier_prod_w:.0f}% + 客户端风险 {supplier_client_w:.0f}%；生产端来自半检/总检不良率，客户端来自 RPM 百万退货率和 IV 退货发起次数。",
                f"Source: {', '.join(selected_factories)} QC data + RPM + Intern Voice. Logic: overall risk = production risk {supplier_prod_w:.0f}% + client risk {supplier_client_w:.0f}%; production uses online/final defect rate, client uses RPM and IV return initiations.",
            )
        )

    with right:
        st.subheader(t("质量趋势", "Quality Trend"))
        trend = (
            finished.groupby(["month", "factory_code", "inspection_stage"], as_index=False)
            .agg(qty_inspected=("qty_inspected", "sum"), defect_qty=("defect_qty", "sum"))
        )
        trend["defect_rate"] = safe_rate(trend["defect_qty"], trend["qty_inspected"])
        trend["factory"] = trend["factory_code"].map(lambda code: FACTORIES[code]["name"])
        trend["trend_line"] = trend["factory"] + " / " + trend["inspection_stage"].astype(str)
        fig = px.line(
            trend,
            x="month",
            y="defect_rate",
            color="factory",
            line_dash="inspection_stage",
            markers=True,
            labels={"defect_rate": t("不良率", "Defect Rate"), "month": t("月份", "Month"), "inspection_stage": t("检验阶段", "Inspection Stage")},
        )
        fig.update_yaxes(tickformat=".1%")
        plot_chart(fig, 380)
        st.caption(t(f"数据来源：{', '.join(selected_factories)} QC data；按 Online QC / End QC-FQC 分线展示。", f"Source: {', '.join(selected_factories)} QC data; split by Online QC and End QC/FQC."))

    with st.expander(t("产品风险明细（可选）", "Product risk detail (optional)")):
        alert_cols = [
            "factory_name",
            "product_code",
            "product_label",
            "risk_level",
            "risk_score",
            "defect_rate",
            "rpm_now",
            "avg_score_now",
            "intern_voice_count",
            "alert_reason",
        ]
        alerts = product_summary.head(12).copy()
        alerts["risk_level"] = alerts["risk_level"].map(risk_level_text)
        dataframe_with_format(
            alerts[[c for c in alert_cols if c in alerts.columns]],
            column_config={
                "risk_score": st.column_config.NumberColumn(t("风险分", "Risk Score"), format="%.1f"),
                "defect_rate": st.column_config.ProgressColumn(t("QC 不良率", "QC Defect Rate"), format="%.2f%%", min_value=0, max_value=0.08),
                "rpm_now": st.column_config.NumberColumn("RPM N0", format="%.0f"),
                "avg_score_now": st.column_config.NumberColumn(t("客户评分", "Customer Score"), format="%.2f"),
                "intern_voice_count": st.column_config.NumberColumn("Intern Voice", format="%d"),
            },
            height=360,
        )


# ==========================================
# 8. Data map
# ==========================================
with tabs[1]:
    st.subheader(t("数据地图", "Data Map"))
    render_kpi_cards(
        [
            {
                "label": "Online / End QC",
                "value": compact_num(len(finished_all)),
                "note": t("四家供应商统一字段", "Canonical schema across four suppliers"),
                "level": "low",
            },
            {
                "label": "RPM + Intern Voice",
                "value": compact_num(len(voice_all)),
                "note": t("YTD 客诉 + ZX Intern Voice 按 CC 连接", "YTD voice plus ZX Intern Voice linked by CC"),
                "level": "medium",
            },
            {
                "label": "Material / Incoming",
                "value": compact_num(len(incoming_all)),
                "note": t("ZX Incoming + TF 面料/辅料/裁片", "ZX incoming plus TF fabric/accessory/cut pieces"),
                "level": "medium",
            },
            {
                "label": t("主数据映射", "Master Data Mapping"),
                "value": "CC",
                "note": t("QC 与 RPM 使用产品代码连接", "QC and RPM joined by product code"),
                "level": "low",
            },
            {
                "label": t("可用性标记", "Availability"),
                "value": str(total_sources),
                "note": t("每个数据源已标注状态和行数", "Each source has visible status and rows"),
                "level": "low",
            },
        ]
    )
    source_rows = []
    for code, cfg in FACTORIES.items():
        f_finished = finished_all[finished_all["factory_code"] == code]
        f_voice = voice_all[voice_all["factory_code"] == code]
        f_incoming = incoming_all[incoming_all["factory_code"] == code] if not incoming_all.empty else pd.DataFrame()
        finished_files = [cfg["finished"]] if cfg.get("finished") is not None else []
        finished_files.extend(cfg.get("finished_files", []))
        source_rows.append(
            {
                t("工厂", "Factory"): cfg["name"],
                t("数据源", "Source"): "Online / End QC",
                t("文件", "File"): " / ".join(str(p) for p in finished_files) if finished_files else "-",
                t("行数", "Rows"): len(f_finished),
                t("日期范围", "Date Range"): source_date_range(f_finished),
                t("可用维度", "Available Dimensions"): "Supplier / Product / Process / Worker-Team / WO",
                t("状态", "Status"): t("已接入", "Loaded") if len(f_finished) else t("本期无数据", "No data in current dataset"),
            }
        )

        ytd_voice = f_voice[f_voice.get("voice_source", "") == "YTD Compare"] if not f_voice.empty else pd.DataFrame()
        source_rows.append(
            {
                t("工厂", "Factory"): cfg["name"],
                t("数据源", "Source"): "RPM / Intern Voice",
                t("文件", "File"): str(cfg["voice"]) if cfg.get("voice") is not None else "-",
                t("行数", "Rows"): len(ytd_voice),
                t("日期范围", "Date Range"): "YTD N0 / N-X" if len(ytd_voice) else "-",
                t("可用维度", "Available Dimensions"): "Product / Product Line / RPM / Review / NQC" if len(ytd_voice) else "-",
                t("状态", "Status"): t("已接入", "Loaded") if len(ytd_voice) else t("本期无 RPM/YTD", "No RPM/YTD in current dataset"),
            }
        )

        intern_source_path = cfg.get("intern_voice_file") or cfg.get("intern_voice_manifest") or cfg.get("intern_voice")
        if intern_source_path is not None:
            intern_voice = f_voice[f_voice.get("voice_source", "") == "Intern Voice"] if not f_voice.empty else pd.DataFrame()
            iv_count = int(intern_voice["intern_voice_count"].sum()) if not intern_voice.empty else 0
            source_rows.append(
                {
                    t("工厂", "Factory"): cfg["name"],
                    t("数据源", "Source"): "Intern Voice",
                    t("文件", "File"): str(intern_source_path),
                    t("行数", "Rows"): iv_count,
                    t("日期范围", "Date Range"): "-",
                    t("可用维度", "Available Dimensions"): "CC / IV No. / Issue / Risk Signal",
                    t("状态", "Status"): t("已接入", "Loaded") if iv_count else t("本期无数据", "No data in current dataset"),
                }
            )

        material_files = [cfg["incoming"]] if cfg.get("incoming") is not None else []
        material_files.extend(cfg.get("material_files", []))
        source_rows.append(
            {
                t("工厂", "Factory"): cfg["name"],
                t("数据源", "Source"): "Incoming / Material QC",
                t("文件", "File"): " / ".join(str(p) for p in material_files) if material_files else "-",
                t("行数", "Rows"): len(f_incoming),
                t("日期范围", "Date Range"): source_date_range(f_incoming),
                t("可用维度", "Available Dimensions"): "Material / Material Supplier / Issue / Decision" if len(f_incoming) else "-",
                t("状态", "Status"): t("已接入", "Loaded") if len(f_incoming) else t("本期无数据", "No data in current dataset"),
            }
        )
    with st.expander(t("数据源明细", "Source details")):
        dataframe_with_format(pd.DataFrame(source_rows), height=410)

    with st.expander(t("项目计划映射", "Requirement mapping")):
        source_ok = 10 <= total_sources <= 15
        supplier_count = supplier_summary["factory_code"].nunique()
        sku_count = min(30, product_summary["product_key"].nunique())
        process_count = process_summary["process"].nunique()
        requirement_rows = [
            {
                "item": t("数据源接入数量", "Loaded data sources"),
                "target": "10-15",
                "current": t(f"{total_sources} 个数据源已接入", f"{total_sources} sources loaded"),
                "status": t("达成", "Met") if source_ok else t("需补齐", "Watch"),
                "level": "done" if source_ok else "watch",
            },
            {
                "item": t("样板供应商数量", "Sample suppliers"),
                "target": "3-5",
                "current": t(f"{supplier_count} 家供应商", f"{supplier_count} suppliers"),
                "status": t("达成", "Met") if 3 <= supplier_count <= 5 else t("需关注", "Watch"),
                "level": "done" if 3 <= supplier_count <= 5 else "watch",
            },
            {
                "item": t("重点产品 / SKU", "Key products / SKU"),
                "target": "10-30",
                "current": t(f"{sku_count} 个重点 CC 已进入看板", f"{sku_count} key CCs in dashboard"),
                "status": t("达成", "Met") if 10 <= sku_count <= 30 else t("需补齐", "Watch"),
                "level": "done" if 10 <= sku_count <= 30 else "watch",
            },
            {
                "item": t("By Supplier 看板", "By Supplier dashboard"),
                "target": t("可用 MVP", "Usable MVP"),
                "current": t("已完成：风险拆解 + 权重方案", "Done: risk components + profiles"),
                "status": t("达成", "Met"),
                "level": "done",
            },
            {
                "item": t("By Product 看板", "By Product dashboard"),
                "target": t("可用 MVP", "Usable MVP"),
                "current": t("已完成：聚焦矩阵 + Top CC", "Done: focus matrix + top CC"),
                "status": t("达成", "Met"),
                "level": "done",
            },
            {
                "item": t("Panel 对比", "Panel comparison"),
                "target": t("至少 2 个场景", "At least two scenarios"),
                "current": t("3 个场景：总览 / Intern Voice+RPM / 工序", "3 scenarios: overview / Intern Voice+RPM / process"),
                "status": t("达成", "Met"),
                "level": "done",
            },
            {
                "item": t("By Process", "By Process"),
                "target": t("3-5 个关键工序", "3-5 key processes"),
                "current": t(f"{process_count} 个工序可钻取，建议演示时筛选 Top 5", f"{process_count} processes available; filter Top 5 for demo"),
                "status": t("覆盖充足", "Covered") if process_count >= 3 else t("需补齐", "Watch"),
                "level": "done" if process_count >= 3 else "watch",
            },
            {
                "item": t("整改有效性反馈", "CAP effectiveness"),
                "target": t("看板验证", "Dashboard validation"),
                "current": t("已用前后周期模拟，待真实 CAP 闭环数据", "Period-based simulation; awaiting live CAP closure data"),
                "status": t("演示可用", "Demo-ready"),
                "level": "watch",
            },
        ]
        render_requirement_mapping(requirement_rows)

    with st.expander(t("统一字段字典", "Canonical field dictionary")):
        field_dict = pd.DataFrame(
            [
                ["factory_code", t("工厂代码", "Factory code"), "ZX / DS / JS / TF"],
                ["supplier", t("供应商名称", "Supplier name"), t("供应商风险聚合主键", "Supplier risk grouping key")],
                ["product_code / product_key", t("CC / 款式", "CC / style"), t("连接 QC 与 RPM 数据", "Join key for QC and RPM")],
                ["inspection_stage", t("检验阶段", "Inspection stage"), "Online QC / End QC / FQC"],
                ["process", t("不良工序", "Defect process"), t("By Process 风险标签", "By Process risk tag")],
                ["qty_inspected", t("检验数量", "Inspected quantity"), t("QC 分母", "QC denominator")],
                ["defect_qty", t("疵点个数", "Defect quantity"), t("QC 分子", "QC numerator")],
                ["defect_rate / rft", t("不良率 / 一次通过率", "Defect rate / RFT"), t("核心质量指标", "Core quality metric")],
                ["rpm_now / delta_rpm", t("当前 RPM / RPM 变化", "Current RPM / delta RPM"), t("客户体验风险", "Customer experience risk")],
                ["material_supplier / issue", t("来料供应商 / 问题点", "Material supplier / issue"), t("ZX + TF 来料风险", "ZX + TF material risk")],
            ],
            columns=[t("标准字段", "Canonical Field"), t("含义", "Meaning"), t("用途", "Use")],
        )
        dataframe_with_format(field_dict, height=380)


# ==========================================
# 9. By Supplier
# ==========================================
with tabs[2]:
    st.subheader(t("By Supplier 供应商质量风险看板", "By Supplier Quality Risk Dashboard"))
    risk_settings = render_risk_settings_panel()
    active_profile_label = risk_profile_label(risk_settings.get("_active_profile", "__default__"))
    supplier_prod_w = effective_weight_pct(risk_settings, "supplier_weights", "production_score")
    supplier_client_w = effective_weight_pct(risk_settings, "supplier_weights", "client_score")
    client_rpm_w = effective_weight_pct(risk_settings, "client_weights", "rpm_score")
    client_iv_w = effective_weight_pct(risk_settings, "client_weights", "intern_voice_score")
    score_logic_cn = (
        f"<div>当前编辑方案：<span class='formula-highlight'>{html.escape(active_profile_label)}</span>。</div>"
        f"<div>综合风险分 = <span class='formula-highlight'>生产端 {supplier_prod_w:.0f}% + 客户端 {supplier_client_w:.0f}%</span>。</div>"
        f"<div>生产端 = min(半检/总检QC不良率 / {risk_settings['qc_benchmark_pct']:.1f}% * 100, 100)。</div>"
        f"<div>客户端 = 标准化后的 RPM风险分 {client_rpm_w:.0f}% + 标准化后的 Intern Voice风险分 {client_iv_w:.0f}%。</div>"
        f"<div>RPM风险分 = min(RPM百万退货率 / {risk_settings['rpm_cap']:.0f} * 100, 100)，{risk_settings['rpm_cap']:.0f} 是当前POC的100分封顶阈值，可在“更多评分基准”调整。</div>"
        f"<div>Intern Voice风险分 = min(退货发起次数 / {risk_settings['intern_voice_cap']} * 100, 100)，{risk_settings['intern_voice_cap']} 是当前POC的100分封顶阈值。</div>"
        "<div>说明：权重是按 0-100 风险分加权，不是直接按原始数量相加；默认 RPM 30% / IV 70% 是为了让更直接的退货发起信号在POC里更敏感。</div>"
    )
    score_logic_en = (
        f"<div>Editing profile: <span class='formula-highlight'>{html.escape(active_profile_label)}</span>.</div>"
        f"<div>Overall risk = <span class='formula-highlight'>Production {supplier_prod_w:.0f}% + Client {supplier_client_w:.0f}%</span>.</div>"
        f"<div>Production = min(online/final QC defect rate / {risk_settings['qc_benchmark_pct']:.1f}% * 100, 100).</div>"
        f"<div>Client = normalized RPM risk {client_rpm_w:.0f}% + normalized Intern Voice risk {client_iv_w:.0f}%.</div>"
        f"<div>RPM risk = min(RPM returns per million / {risk_settings['rpm_cap']:.0f} * 100, 100); {risk_settings['rpm_cap']:.0f} is the current POC cap for 100 points and can be adjusted in More benchmarks.</div>"
        f"<div>Intern Voice risk = min(return initiations / {risk_settings['intern_voice_cap']} * 100, 100); {risk_settings['intern_voice_cap']} is the current POC cap for 100 points.</div>"
        "<div>Note: weights apply to normalized 0-100 risk scores, not directly to raw counts. The default RPM 30% / IV 70% makes direct return-initiation evidence more sensitive in this POC.</div>"
    )
    st.markdown(
        f"""
        <div class="action-strip">
            <b>{t('风险分说明', 'Score logic')}:</b>
            <div class="score-logic-lines">{t(score_logic_cn, score_logic_en)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    supplier_display = supplier_summary.copy()
    supplier_display[t("风险等级", "Risk Level")] = supplier_display["risk_level"].map(risk_level_text)
    supplier_table = supplier_display[
        [
            "factory_name",
            "supplier",
            t("风险等级", "Risk Level"),
            "risk_score",
            "production_score",
            "client_score",
            "rpm_score",
            "defect_rate",
            "rft",
            "qty_inspected",
            "defect_qty",
            "avg_rpm",
            "avg_score",
            "intern_voice_count",
            "intern_voice_score",
            "incoming_issues",
            "risk_trend",
        ]
    ].rename(
        columns={
            "factory_name": t("工厂", "Factory"),
            "supplier": t("供应商", "Supplier"),
            "risk_score": t("综合风险分", "Risk Score"),
            "production_score": t("生产端风险", "Production Risk"),
            "client_score": t("客户端风险", "Client Risk"),
            "rpm_score": "RPM 风险分",
            "defect_rate": t("QC 不良率", "QC Defect Rate"),
            "rft": "RFT",
            "qty_inspected": t("检验数量", "Inspected Qty"),
            "defect_qty": t("疵点数", "Defects"),
            "avg_rpm": "Avg RPM",
            "avg_score": t("客户评分", "Customer Score"),
            "intern_voice_count": "Intern Voice",
            "intern_voice_score": t("Intern Voice 风险分", "Intern Voice Risk"),
            "incoming_issues": t("来料问题", "Incoming Issues"),
            "risk_trend": t("趋势", "Trend"),
        }
    )

    left, right = st.columns([1.1, 1])
    with left:
        component = supplier_summary.melt(
            id_vars=["factory_name"],
            value_vars=[c for c in ["production_score", "rpm_score", "intern_voice_score", "client_score"] if c in supplier_summary.columns],
            var_name="component",
            value_name="score",
        )
        component["component"] = component["component"].map(
            {
                "production_score": t("生产端", "Production"),
                "rpm_score": "RPM",
                "intern_voice_score": "Intern Voice",
                "client_score": t("客户端合成", "Client composite"),
            }
        )
        component["score_label"] = component["score"].map(lambda x: f"{x:.0f}")
        fig = px.bar(
            component,
            x="factory_name",
            y="score",
            color="component",
            barmode="group",
            text="score_label",
            labels={"factory_name": t("工厂", "Factory"), "score": t("分项风险分", "Component Risk")},
            color_discrete_sequence=["#2563eb", "#d97706", "#c01048", "#059669"],
        )
        fig.update_traces(textposition="outside")
        fig.update_yaxes(range=[0, 115])
        plot_chart(fig, 390)
        st.caption(t(f"数据来源：{', '.join(selected_factories)} QC data + RPM + Intern Voice。分项风险越高，代表该信号越需要优先下钻。", f"Source: {', '.join(selected_factories)} QC data + RPM + Intern Voice. Higher component score means higher drill-down priority."))

    with right:
        selected_supplier = st.selectbox(
            t("供应商下钻", "Supplier Drill-down"),
            supplier_summary["factory_code"].tolist(),
            format_func=lambda code: FACTORIES[code]["name"],
        )
        focus = finished[finished["factory_code"] == selected_supplier].copy()
        if not focus.empty:
            defect_mix = (
                focus[focus["defect_qty"] > 0]
                .groupby("defect_type", as_index=False)["defect_qty"]
                .sum()
                .sort_values("defect_qty", ascending=False)
                .head(10)
            )
            fig = px.bar(
                defect_mix,
                x="defect_qty",
                y="defect_type",
                orientation="h",
                text="defect_qty",
                labels={"defect_qty": t("疵点数", "Defects"), "defect_type": t("疵点类型", "Defect Type")},
                color_discrete_sequence=["#c01048"],
            )
            fig.update_traces(textposition="outside")
            fig.update_yaxes(autorange="reversed")
            plot_chart(fig, 390)
            st.caption(t(f"数据来源：{selected_supplier} QC data。展示该供应商 Top 疵点类型和疵点数。", f"Source: {selected_supplier} QC data. Shows top defect types and defect counts for the selected supplier."))

    with st.expander(t("供应商明细（可选）", "Supplier detail (optional)")):
        dataframe_with_format(
            supplier_table,
            column_config={
                t("综合风险分", "Risk Score"): st.column_config.NumberColumn(format="%.1f"),
                t("生产端风险", "Production Risk"): st.column_config.NumberColumn(format="%.1f"),
                t("客户端风险", "Client Risk"): st.column_config.NumberColumn(format="%.1f"),
                "RPM 风险分": st.column_config.NumberColumn(format="%.1f"),
                t("QC 不良率", "QC Defect Rate"): st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=0.06),
                "RFT": st.column_config.ProgressColumn(format="%.2f%%", min_value=0.9, max_value=1),
                "Avg RPM": st.column_config.NumberColumn(format="%.0f"),
                t("Intern Voice 风险分", "Intern Voice Risk"): st.column_config.NumberColumn(format="%.1f"),
            },
            height=260,
        )


# ==========================================
# 10. By Product
# ==========================================
with tabs[3]:
    st.subheader(t("By Product 产品风险看板", "By Product Risk Dashboard"))
    if product_summary.empty:
        st.info(t("没有可展示的产品数据。", "No product data to show."))
    else:
        risk_settings = render_product_weight_panel()
        active_profile_label = risk_profile_label(risk_settings.get("_active_profile", "__default__"))
        product_prod_w = effective_weight_pct(risk_settings, "product_weights", "production_score")
        product_client_w = effective_weight_pct(risk_settings, "product_weights", "client_score")
        client_rpm_w = effective_weight_pct(risk_settings, "client_weights", "rpm_score")
        client_iv_w = effective_weight_pct(risk_settings, "client_weights", "intern_voice_score")
        product_logic_cn = (
            f"<div>当前编辑方案：<span class='formula-highlight'>{html.escape(active_profile_label)}</span>。</div>"
            f"<div>产品风险分 = <span class='formula-highlight'>生产端 {product_prod_w:.0f}% + 客户端 {product_client_w:.0f}%</span>。</div>"
            "<div>生产端来自该 CC 的半检/总检 QC 不良率。</div>"
            f"<div>客户端 = 标准化后的 RPM风险分 {client_rpm_w:.0f}% + 标准化后的 Intern Voice风险分 {client_iv_w:.0f}%。</div>"
            f"<div>RPM和Intern Voice先各自换算成0-100风险分，再按权重加权；不是按原始数量直接相加。</div>"
        )
        product_logic_en = (
            f"<div>Editing profile: <span class='formula-highlight'>{html.escape(active_profile_label)}</span>.</div>"
            f"<div>Product risk = <span class='formula-highlight'>production {product_prod_w:.0f}% + client {product_client_w:.0f}%</span>.</div>"
            "<div>Production uses the CC-level online/final QC defect rate.</div>"
            f"<div>Client = normalized RPM risk {client_rpm_w:.0f}% + normalized Intern Voice risk {client_iv_w:.0f}%.</div>"
            "<div>RPM and Intern Voice are each converted to 0-100 risk scores before weighting; raw values are not added directly.</div>"
        )
        st.markdown(
            f"""
            <div class="action-strip">
                <b>{t('产品风险分说明', 'Product score logic')}:</b>
                <div class="score-logic-lines">{t(product_logic_cn, product_logic_en)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        product_risk_view, x_cap, y_cap = prepare_product_risk_view(product_summary)
        left, right = st.columns([1.2, 1])
        with left:
            zone_colors = {
                t("QC + 客户端双高", "QC + client high"): "#c01048",
                t("QC 高", "QC high"): "#dc6803",
                t("客户端信号高", "Client signal high"): "#d99a00",
                t("常规关注", "Routine"): "#168a5b",
            }
            fig = px.scatter(
                product_risk_view,
                x="qc_rate_plot",
                y="customer_signal_plot",
                color="risk_zone",
                size="plot_size",
                hover_data={
                    "factory_name": True,
                    "product_code": True,
                    "product_label": True,
                    "qc_rate": ":.2%",
                    "qc_rate_plot": False,
                    "customer_signal": ":.1f",
                    "customer_signal_plot": False,
                    "rpm_now": ":.0f",
                    "avg_score_now": ":.2f",
                    "intern_voice_count": ":.0f",
                    "axis_note": True,
                    "plot_size": False,
                    "risk_zone": True,
                },
                color_discrete_map=zone_colors,
                labels={
                    "qc_rate_plot": t("QC 不良率（聚焦区）", "QC defect rate - focused"),
                    "customer_signal_plot": t("客户端风险信号（RPM/Intern Voice）", "Client risk signal"),
                    "risk_zone": t("风险分区", "Risk zone"),
                },
            )
            fig.update_xaxes(tickformat=".1%")
            fig.update_layout(xaxis_range=[0, x_cap * 1.04], yaxis_range=[0, y_cap * 1.08])
            fig.add_vline(x=0.02, line_width=1, line_dash="dash", line_color="#dc6803")
            fig.add_hline(y=35, line_width=1, line_dash="dash", line_color="#dc6803")
            fig.add_annotation(
                x=min(0.022, x_cap * 0.72),
                y=min(38, y_cap * 0.86),
                text=t("右上角 = QC + 客户端信号双高", "Upper right = QC + client signal"),
                showarrow=False,
                font=dict(color="#c01048", size=12),
                bgcolor="rgba(255,255,255,0.82)",
            )
            plot_chart(fig, 450)
            st.caption(t(
                f"数据来源：{', '.join(selected_factories)} QC data + RPM + Intern Voice。坐标轴按 P95 聚焦：QC ≤ {pct(x_cap)}，客户端风险信号 ≤ {y_cap:.0f}；超出部分仍在 hover 中保留真实值。",
                f"Source: {', '.join(selected_factories)} QC data + RPM + Intern Voice. Axes focus on P95: QC <= {pct(x_cap)}, client signal <= {y_cap:.0f}; hover keeps actual values for clipped points.",
            ))

        with right:
            top_products = product_risk_view.sort_values(["defect_qty", "customer_signal", "risk_score"], ascending=False).head(8).copy()
            top_products["label"] = top_products["factory_code"] + " / " + top_products["product_code"].astype(str)
            fig = px.bar(
                top_products.sort_values("defect_qty"),
                x="defect_qty",
                y="label",
                color="risk_zone",
                orientation="h",
                text="defect_qty",
                color_discrete_map=zone_colors,
                labels={"defect_qty": t("疵点数", "Defects"), "label": "CC", "risk_zone": t("风险分区", "Risk zone")},
            )
            fig.update_traces(texttemplate="%{text:.0f}", textposition="inside", insidetextanchor="middle", textfont_color="#ffffff")
            plot_chart(fig, 430)
            st.caption(t(f"数据来源：{', '.join(selected_factories)} QC data。按疵点数优先展示 Top CC，用于快速找出生产端主问题。", f"Source: {', '.join(selected_factories)} QC data. Top CCs by defect count for quick production-side triage."))

        zone_count = (
            product_risk_view.groupby(["factory_code", "risk_zone"], as_index=False)
            .size()
            .rename(columns={"size": t("产品数", "Products")})
        )
        fig = px.bar(
            zone_count,
            x="factory_code",
            y=t("产品数", "Products"),
            color="risk_zone",
            barmode="stack",
            color_discrete_map=zone_colors,
            labels={"factory_code": t("工厂", "Factory"), "risk_zone": t("风险分区", "Risk zone")},
        )
        plot_chart(fig, 300)
        st.caption(t(f"数据来源：{', '.join(selected_factories)} QC data + RPM + Intern Voice。展示各工厂产品落在哪些风险分区。", f"Source: {', '.join(selected_factories)} QC data + RPM + Intern Voice. Shows how products distribute across risk zones by factory."))

        with st.expander(t("产品明细（可选）", "Product detail (optional)")):
            product_table = product_summary.head(30).copy()
            product_table["risk_level"] = product_table["risk_level"].map(risk_level_text)
            product_table = product_table[
                [
                    "factory_name",
                    "product_code",
                    "product_label",
                    "risk_level",
                    "risk_score",
                    "qty_inspected",
                    "defect_rate",
                    "top_defect",
                    "rpm_now",
                    "delta_rpm",
                    "avg_score_now",
                    "intern_voice_count",
                    "alert_reason",
                ]
            ]
            dataframe_with_format(
                product_table,
                column_config={
                    "risk_score": st.column_config.NumberColumn(t("风险分", "Risk Score"), format="%.1f"),
                    "defect_rate": st.column_config.ProgressColumn(t("QC 不良率", "QC Defect Rate"), format="%.2f%%", min_value=0, max_value=0.08),
                    "rpm_now": st.column_config.NumberColumn("RPM N0", format="%.0f"),
                    "delta_rpm": st.column_config.NumberColumn("Delta RPM", format="%.0f"),
                    "avg_score_now": st.column_config.NumberColumn(t("客户评分", "Customer Score"), format="%.2f"),
                    "intern_voice_count": st.column_config.NumberColumn("Intern Voice", format="%d"),
                },
                height=420,
            )


# ==========================================
# 11. Panel benchmark
# ==========================================
with tabs[4]:
    st.subheader(t("Panel 管理 / 供应商横向 Benchmark", "Panel Management / Supplier Benchmark"))
    scenario = st.radio(
        t("Benchmark 场景", "Benchmark Scenario"),
        [
            t("风险视图", "Risk view"),
            "Intern Voice / RPM",
            t("过程风险", "Process risk"),
        ],
        horizontal=True,
    )

    if scenario == t("风险视图", "Risk view"):
        panel_df = supplier_summary.copy()
        st.markdown(
            f"""
            <div class="action-strip">
                <b>{t('风险视图说明', 'Risk view logic')}:</b>
                <span>{t(
                    f'供应商综合风险 = 生产端 {supplier_prod_w:.0f}% + 客户端 {supplier_client_w:.0f}%；生产端来自半检/总检 QC 不良率，客户端来自 RPM 百万退货率和 Intern Voice 退货发起次数。',
                    f'Supplier risk = production {supplier_prod_w:.0f}% + client {supplier_client_w:.0f}%; production uses online/final QC defect rate, client uses RPM returns per million and Intern Voice return initiations.'
                )}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        metrics = ["production_score", "rpm_score", "intern_voice_score", "client_score", "risk_score"]
        metric_labels = {
            "production_score": t("生产端", "Production"),
            "rpm_score": "RPM",
            "intern_voice_score": "Intern Voice",
            "client_score": t("客户端", "Client"),
            "risk_score": t("综合风险", "Overall Risk"),
        }
        panel_long = panel_df.melt(id_vars=["factory_name"], value_vars=metrics, var_name="metric", value_name="score")
        panel_long["metric"] = panel_long["metric"].map(metric_labels)
        fig = px.bar(
            panel_long,
            x="metric",
            y="score",
            color="factory_name",
            barmode="group",
            text=panel_long["score"].map(lambda x: f"{x:.0f}"),
            labels={
                "metric": t("指标", "Metric"),
                "score": t("风险分", "Risk Score"),
                "factory_name": t("工厂", "Factory"),
            },
        )
        fig.update_traces(textposition="outside")
        fig.update_yaxes(range=[0, 115])
        plot_chart(fig, 450)
        st.caption(t(f"数据来源：{', '.join(selected_factories)} QC data + RPM + Intern Voice。", f"Source: {', '.join(selected_factories)} QC data + RPM + Intern Voice."))
        with st.expander(t("Panel 数据明细（可选）", "Panel detail (optional)")):
            dataframe_with_format(
                panel_df[["factory_name", "risk_score", "production_score", "client_score", "avg_rpm", "rpm_score", "intern_voice_count", "intern_voice_score"]].rename(
                    columns={
                        "factory_name": t("工厂", "Factory"),
                        "risk_score": t("综合风险", "Overall Risk"),
                        "production_score": t("生产端", "Production"),
                        "client_score": t("客户端", "Client"),
                        "avg_rpm": "Avg RPM",
                        "rpm_score": "RPM Risk",
                        "intern_voice_count": "Intern Voice",
                        "intern_voice_score": t("Intern Voice 风险分", "Intern Voice Risk"),
                    }
                ),
                height=220,
            )

    elif scenario == "Intern Voice / RPM":
        if voice.empty:
            st.info(t("当前筛选范围没有 Intern Voice / RPM 数据。", "No Intern Voice / RPM data available."))
        else:
            voice_panel = (
                voice.groupby(["factory_code", "factory_name"], as_index=False)
                .agg(
                    rpm_now=("rpm_now", "mean"),
                    delta_rpm=("delta_rpm", "mean"),
                    avg_score_now=("avg_score_now", "mean"),
                    returned_now=("returned_now", "sum"),
                    nqc_now=("nqc_now", "sum"),
                    intern_voice_count=("intern_voice_count", "sum"),
                )
            )
            for col in ["rpm_now", "delta_rpm", "avg_score_now", "returned_now", "nqc_now", "intern_voice_count"]:
                voice_panel[col] = pd.to_numeric(voice_panel[col], errors="coerce").fillna(0)
            rpm_cap = max(float(voice_panel["rpm_now"].quantile(0.9)), 1.0)
            delta_positive = voice_panel["delta_rpm"].clip(lower=0)
            delta_cap = max(float(delta_positive.quantile(0.9)), 1.0)
            return_nqc = voice_panel["returned_now"] + voice_panel["nqc_now"]
            return_nqc_cap = max(float(return_nqc.quantile(0.9)), 1.0)
            voice_panel["rpm_score"] = np.minimum(voice_panel["rpm_now"] / rpm_cap * 100, 100)
            voice_panel["trend_score"] = np.minimum(delta_positive / delta_cap * 100, 100)
            voice_panel["return_nqc_score"] = np.minimum(return_nqc / return_nqc_cap * 100, 100)
            voice_panel["intern_voice_score"] = voice_panel.apply(
                lambda row: min(
                    row["intern_voice_count"]
                    / max(float(settings_for_factory(risk_settings, row["factory_code"]).get("intern_voice_cap", 30)), 1)
                    * 100,
                    100,
                ),
                axis=1,
            )
            voice_panel["combined_signal"] = (
                voice_panel["rpm_score"] * 0.45
                + voice_panel["intern_voice_score"] * 0.30
                + voice_panel["trend_score"] * 0.15
                + voice_panel["return_nqc_score"] * 0.10
            ).clip(0, 100)
            voice_panel["risk_level"] = voice_panel["combined_signal"].map(risk_level)
            st.caption(
                t(
                    f"数据来源：{', '.join(selected_factories)} RPM data + Intern Voice。这个视图把 RPM、Intern Voice、RPM 上升和退货/NQC 都转成 0-100 信号强度；颜色越深，越值得优先下钻。",
                    f"Source: {', '.join(selected_factories)} RPM data + Intern Voice. This view normalizes RPM, Intern Voice, RPM increase, and returns/NQC into 0-100 signal strength; darker means higher priority.",
                )
            )
            signal_long = voice_panel.melt(
                id_vars=["factory_name"],
                value_vars=["rpm_score", "intern_voice_score", "trend_score", "return_nqc_score"],
                var_name="signal",
                value_name="score",
            )
            signal_labels = {
                "rpm_score": "RPM N0",
                "intern_voice_score": "Intern Voice",
                "trend_score": t("RPM 上升", "RPM increase"),
                "return_nqc_score": t("退货 / NQC", "Returns / NQC"),
            }
            signal_long["signal"] = signal_long["signal"].map(signal_labels)
            heatmap_data = signal_long.pivot(index="factory_name", columns="signal", values="score").fillna(0)
            heatmap_order = ["RPM N0", "Intern Voice", t("RPM 上升", "RPM increase"), t("退货 / NQC", "Returns / NQC")]
            heatmap_data = heatmap_data[[col for col in heatmap_order if col in heatmap_data.columns]]
            left, right = st.columns([1.25, 1])
            with left:
                fig = px.imshow(
                    heatmap_data,
                    aspect="auto",
                    color_continuous_scale=["#eaf7f4", "#ffd166", "#f97316", "#c01048"],
                    labels=dict(x=t("信号", "Signal"), y=t("工厂", "Factory"), color=t("强度", "Intensity")),
                    text_auto=".0f",
                )
                fig.update_layout(title=t("Intern Voice + RPM 信号热力矩阵", "Intern Voice + RPM Signal Matrix"))
                plot_chart(fig, 410)
            with right:
                ranked_voice = voice_panel.sort_values("combined_signal", ascending=True).copy()
                fig = px.bar(
                    ranked_voice,
                    x="combined_signal",
                    y="factory_name",
                    orientation="h",
                    color="risk_level",
                    color_discrete_map=LEVEL_COLORS,
                    text=ranked_voice["combined_signal"].map(lambda x: f"{x:.0f}"),
                    labels={"combined_signal": t("组合信号强度", "Combined signal"), "factory_name": t("工厂", "Factory")},
                    hover_data=["rpm_now", "intern_voice_count", "delta_rpm", "returned_now", "nqc_now"],
                )
                fig.update_xaxes(range=[0, 100])
                plot_chart(fig, 410)
            with st.expander(t("Intern Voice / RPM 明细（可选）", "Intern Voice / RPM detail (optional)")):
                detail = voice_panel[
                    [
                        "factory_name",
                        "combined_signal",
                        "rpm_now",
                        "intern_voice_count",
                        "delta_rpm",
                        "returned_now",
                        "nqc_now",
                        "avg_score_now",
                    ]
                ].rename(
                    columns={
                        "factory_name": t("工厂", "Factory"),
                        "combined_signal": t("组合信号", "Combined Signal"),
                        "rpm_now": "RPM N0",
                        "intern_voice_count": "Intern Voice",
                        "delta_rpm": "Delta RPM",
                        "returned_now": t("退货数", "Returns"),
                        "nqc_now": "NQC",
                        "avg_score_now": t("评分", "Score"),
                    }
                )
                dataframe_with_format(
                    detail,
                    column_config={
                        t("组合信号", "Combined Signal"): st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=100),
                        "RPM N0": st.column_config.NumberColumn(format="%.0f"),
                        "Intern Voice": st.column_config.NumberColumn(format="%d"),
                        "Delta RPM": st.column_config.NumberColumn(format="%.0f"),
                        t("评分", "Score"): st.column_config.NumberColumn(format="%.2f"),
                    },
                    height=260,
                )

    else:
        panel_process = process_summary.copy()
        st.caption(t("展示所有供应商的 Top 工序风险，不再锁定单个工序；适合先看 general，再下钻到 06 过程/来料。", "Shows top process risks across suppliers instead of one selected process; use this for general scanning, then drill into 06 Process/Material."))
        panel_process = panel_process.sort_values("risk_score", ascending=False).head(16).copy()
        panel_process["process_view"] = panel_process["factory_code"] + " / " + panel_process["process"].astype(str)
        fig = px.bar(
            panel_process.sort_values("risk_score"),
            x="risk_score",
            y="process_view",
            color="risk_level",
            color_discrete_map=LEVEL_COLORS,
            orientation="h",
            text=panel_process.sort_values("risk_score")["risk_score"].map(lambda x: f"{x:.0f}"),
            labels={"risk_score": t("工序风险分", "Process Risk Score"), "process_view": t("工厂 / 工序", "Factory / Process")},
        )
        fig.update_traces(textposition="outside")
        fig.update_xaxes(range=[0, 110])
        plot_chart(fig, 420)
        st.caption(t(f"数据来源：{', '.join(selected_factories)} QC data。算法：工序风险 = min(工序不良率 / {risk_settings['process_benchmark_pct']:.1f}% * 100, 100)。", f"Source: {', '.join(selected_factories)} QC data. Logic: process risk = min(process defect rate / {risk_settings['process_benchmark_pct']:.1f}% * 100, 100)."))
        with st.expander(t("工序对比明细（可选）", "Process comparison detail (optional)")):
            dataframe_with_format(
                panel_process[["factory_name", "process", "qty_inspected", "defect_qty", "defect_rate", "top_defect", "risk_score"]],
                column_config={"defect_rate": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=0.08)},
                height=260,
            )


# ==========================================
# 12. By Process and material
# ==========================================
with tabs[5]:
    st.subheader(t("ZX + TF Process / Material 风险看板", "ZX + TF Process / Material Risk Dashboard"))
    st.caption(
        t(
            f"当前编辑方案：{active_profile_label}。工序风险分 = min(工序不良率 / {risk_settings['process_benchmark_pct']:.1f}% * 100, 100)；基准可在左侧“风险分设置”保存，工厂专属方案会自动套用到对应工序。",
            f"Editing profile: {active_profile_label}. Process risk = min(process defect rate / {risk_settings['process_benchmark_pct']:.1f}% * 100, 100); factory-specific profiles apply to matching processes.",
        )
    )
    st.markdown(
        f"<div class='zx-lock'>{t('聚焦 ZX + TF 的过程与材料信号；DS / JS 当前暂无来料数据。', 'Focus on ZX + TF process and material signals; DS / JS currently have no incoming data.')}</div>",
        unsafe_allow_html=True,
    )

    if pm_finished.empty:
        st.info(t("当前日期、工序或款式筛选下没有 ZX / TF 过程数据。", "No ZX / TF process data under the current date, process, or product filters."))
    else:
        pm_qty = pm_finished["qty_inspected"].sum()
        pm_defects = pm_finished["defect_qty"].sum()
        pm_rate = pm_defects / pm_qty if pm_qty else 0
        pm_returns = 0 if pm_incoming.empty else pm_incoming["decision"].astype(str).str.contains("退货|Reject", case=False, na=False).sum()
        render_kpi_cards(
            [
                {
                    "label": t("过程检验量", "Process Inspected Qty"),
                    "value": compact_num(pm_qty),
                    "note": t("过程/成品统一筛选", "Process and final QC filtered together"),
                    "level": "low",
                },
                {
                    "label": t("过程不良率", "Process Defect Rate"),
                    "value": pct(pm_rate),
                    "note": f"{compact_num(pm_defects)} defects",
                    "level": "high" if pm_rate >= 0.015 else "medium",
                },
                {
                    "label": t("关键工序数", "Key Processes"),
                    "value": str(pm_process_summary["process"].nunique()),
                    "note": t("用于定位工序风险", "Used to locate process risk"),
                    "level": "medium",
                },
                {
                    "label": t("来料问题批次", "Incoming Issue Batches"),
                    "value": str(len(pm_incoming)),
                    "note": f"{pm_returns} {t('批退货判定', 'rejected / returned')}",
                    "level": "high" if pm_returns >= 10 else "medium",
                },
                {
                    "label": t("来料供应商", "Material Suppliers"),
                    "value": str(0 if pm_incoming.empty else pm_incoming["material_supplier"].nunique()),
                    "note": t("ZX 原辅料 + TF 面料/辅料/裁片", "ZX incoming + TF fabric/accessory/cut pieces"),
                    "level": "medium",
                },
            ]
        )

        left, right = st.columns([1.05, 1])
        with left:
            top_process = pm_process_summary.head(12).copy()
            top_process["process_view"] = top_process["factory_code"] + " / " + top_process["process"].astype(str)
            fig = px.bar(
                top_process.sort_values("defect_rate"),
                x="defect_rate",
                y="process_view",
                color="risk_level",
                color_discrete_map=LEVEL_COLORS,
                orientation="h",
                text=top_process.sort_values("defect_rate")["defect_rate"].map(lambda x: pct(x, 1)),
                labels={"defect_rate": t("不良率", "Defect Rate"), "process_view": t("工厂 / 工序", "Factory / Process")},
            )
            fig.update_xaxes(tickformat=".1%")
            plot_chart(fig, 430)
            st.caption(t("数据来源：ZX/TF QC data。按工厂/工序展示 Top 过程不良率，用于定位生产端过程风险。", "Source: ZX/TF QC data. Shows top process defect rates by factory/process for production-side risk triage."))

        with right:
            heat_source = pm_finished[pm_finished["defect_qty"] > 0].copy()
            heat_source["process_view"] = heat_source["factory_code"] + " / " + heat_source["process"].astype(str)
            matrix = (
                heat_source
                .groupby(["process", "defect_type"], as_index=False)["defect_qty"]
                .sum()
            )
            if not matrix.empty:
                top_defects = matrix.groupby("defect_type")["defect_qty"].sum().nlargest(8).index
                matrix = (
                    heat_source[heat_source["defect_type"].isin(top_defects)]
                    .groupby(["process_view", "defect_type"], as_index=False)["defect_qty"]
                    .sum()
                )
                heat = matrix.pivot(index="process_view", columns="defect_type", values="defect_qty").fillna(0)
                fig = px.imshow(
                    heat,
                    text_auto=True,
                    color_continuous_scale=["#fff7ed", "#fb923c", "#c01048"],
                    aspect="auto",
                    labels=dict(x=t("疵点类型", "Defect Type"), y=t("工序", "Process"), color=t("疵点数", "Defects")),
                )
                plot_chart(fig, 430)
                st.caption(t("数据来源：ZX/TF QC data。热力矩阵展示工序和疵点类型的交叉集中度，颜色越深代表疵点越集中。", "Source: ZX/TF QC data. Heatmap shows concentration between processes and defect types; darker means more concentrated defects."))

        with st.expander(t("班组 / 岗位聚类明细（可选）", "Team / position cluster detail (optional)")):
            worker_view = pm_worker_clusters.head(25).copy()
            dataframe_with_format(
                worker_view[["factory_code", "worker_team", "process", "qty_inspected", "defect_qty", "defect_rate", "skill_tag"]],
                column_config={"defect_rate": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=0.12)},
                height=360,
            )

    st.subheader(t("ZX + TF By Material 来料风险", "ZX + TF By Material Incoming Risk"))
    if pm_incoming.empty:
        st.info(t("当前筛选范围没有 ZX / TF 来料或材料检验数据。", "No ZX / TF incoming or material inspection data under the current filters."))
    else:
        c1, c2 = st.columns(2)
        with c1:
            mat_issue = pm_incoming.groupby(["factory_code", "material_type", "issue"], as_index=False).size().sort_values("size", ascending=False).head(12)
            mat_issue["issue_view"] = mat_issue["factory_code"] + " / " + mat_issue["issue"].astype(str)
            fig = px.bar(
                mat_issue,
                x="size",
                y="issue_view",
                color="material_type",
                orientation="h",
                labels={"size": t("批次数", "Batches"), "issue_view": t("工厂 / 质量问题点", "Factory / Issue")},
            )
            fig.update_yaxes(autorange="reversed")
            plot_chart(fig, 390)
            st.caption(t("数据来源：ZX Material data + TF Material data。按问题批次展示来料/材料风险点。", "Source: ZX Material data + TF Material data. Shows material risk points by issue batches."))
        with c2:
            mat_supplier = pm_incoming.groupby(["factory_code", "material_supplier"], as_index=False).size().sort_values("size", ascending=False).head(12)
            mat_supplier["supplier_view"] = mat_supplier["factory_code"] + " / " + mat_supplier["material_supplier"].astype(str)
            fig = px.bar(
                mat_supplier,
                x="supplier_view",
                y="size",
                labels={"supplier_view": t("来料供应商", "Material Supplier"), "size": t("问题批次", "Issue Batches")},
                color_discrete_sequence=["#059669"],
            )
            plot_chart(fig, 390)
            st.caption(t("数据来源：ZX Material data + TF Material data。按来料供应商聚合问题批次，便于识别上游供应商风险。", "Source: ZX Material data + TF Material data. Aggregates issue batches by material supplier to identify upstream risk."))


# ==========================================
# 13. Analysis methods
# ==========================================
with tabs[6]:
    st.subheader(t("分析方法", "Analysis Methods"))

    method_finished_scope = finished_all[
        (finished_all["date"].dt.date >= start_date)
        & (finished_all["date"].dt.date <= end_date)
    ].copy()
    if selected_stages:
        method_finished_scope = method_finished_scope[method_finished_scope["inspection_stage"].isin(selected_stages)]
    if selected_processes:
        method_finished_scope = method_finished_scope[method_finished_scope["process"].isin(selected_processes)]
    if product_search.strip():
        method_needle = product_search.strip().lower()
        method_finished_scope = method_finished_scope[
            method_finished_scope["product_code"].astype(str).str.lower().str.contains(method_needle, na=False)
            | method_finished_scope["product_label"].astype(str).str.lower().str.contains(method_needle, na=False)
        ]
    method_incoming_scope = incoming_all[
        (incoming_all["date"].dt.date >= start_date)
        & (incoming_all["date"].dt.date <= end_date)
    ].copy()

    method_factory_options = method_finished_scope["factory_code"].dropna().astype(str).drop_duplicates().tolist()
    if st.session_state.get("method_factory_filter") not in method_factory_options:
        st.session_state.pop("method_factory_filter", None)
    method_factory = st.selectbox(
        t("分析工厂", "Analysis Factory"),
        method_factory_options,
        format_func=lambda code: FACTORIES.get(code, {}).get("name", code),
        key="method_factory_filter",
    )
    method_finished = method_finished_scope[method_finished_scope["factory_code"] == method_factory].copy()
    method_incoming = method_incoming_scope[method_incoming_scope["factory_code"] == method_factory].copy()
    process_shift = compute_process_shift(method_finished)
    abnormal_orders = detect_abnormal_work_orders(method_finished)
    weekly_material_process = compute_weekly_material_process(method_finished, method_incoming)
    cap_effectiveness = compute_cap_effectiveness(method_finished)
    method_factory_name = FACTORIES.get(method_factory, {}).get("name", method_factory)
    method_date_min = method_finished["date"].min()
    method_date_max = method_finished["date"].max()
    method_period = (
        f"{method_date_min:%Y-%m-%d} - {method_date_max:%Y-%m-%d}"
        if pd.notna(method_date_min) and pd.notna(method_date_max)
        else "-"
    )
    st.caption(
        t(
            f"当前分析范围：{method_factory_name}｜QC记录 {len(method_finished):,} 条｜来料问题 {len(method_incoming):,} 条｜数据周期 {method_period}。工厂选择仅影响07方法，日期、检验阶段、工序和款式沿用左侧筛选。",
            f"Current scope: {method_factory_name} | {len(method_finished):,} QC records | {len(method_incoming):,} incoming issues | {method_period}. Factory selection only affects 07 Methods; date, stage, process, and product follow the sidebar filters.",
        )
    )

    left, right = st.columns(2)
    with left:
        st.subheader(t("近30天过程变化｜双窗口差分模型", "Recent Process Shift | Two-Window Delta"))
        if process_shift.empty:
            st.info(t(f"{method_factory_name} 当前数据不足以比较近30天与前30天。", f"{method_factory_name} does not have enough data to compare recent and prior 30-day windows."))
        else:
            shift_plot = pd.concat([process_shift.head(8), process_shift.tail(4)]).drop_duplicates("process_view")
            fig = px.bar(
                shift_plot.sort_values("delta_rate"),
                x="delta_rate",
                y="process_view",
                color="change_type",
                orientation="h",
                color_discrete_map={t("上升", "Worse"): "#c01048", t("下降", "Better"): "#059669"},
                labels={"delta_rate": t("不良率变化", "Defect-rate change"), "process_view": t("工厂 / 工序", "Factory / Process")},
            )
            fig.update_xaxes(tickformat="+.1%")
            plot_chart(fig, 390)
            st.caption(t(f"数据来源：{method_factory} QC data。算法：近30天不良率 - 前30天不良率；向右/红色代表过程恶化，向左/绿色代表改善。", f"Source: {method_factory} QC data. Logic: recent 30-day defect rate minus prior 30-day defect rate; red/right means worse, green/left means better."))

    with right:
        st.subheader(t("异常工单分布｜鲁棒 Z-Score 离群检测", "Work-Order Anomaly | Robust Z-Score Outlier"))
        if abnormal_orders.empty:
            st.info(t(f"{method_factory_name} 当前未识别到显著离群工单。", f"No obvious abnormal work order was detected for {method_factory_name}."))
        else:
            anomaly_plot = abnormal_orders.copy()
            anomaly_plot["plot_size"] = np.sqrt(anomaly_plot["defect_qty"].clip(lower=1)) * 9 + 12
            fig = px.scatter(
                anomaly_plot,
                x="qty_inspected",
                y="defect_rate",
                size="plot_size",
                size_max=36,
                color="factory_name",
                hover_data=["work_order", "product_code", "product_label", "process"],
                labels={"qty_inspected": t("检验数量", "Inspected qty"), "defect_rate": t("不良率", "Defect rate")},
            )
            fig.update_yaxes(tickformat=".1%")
            plot_chart(fig, 390)
            st.caption(t(f"数据来源：{method_factory} QC work order data。算法：对检验量、不良率、疵点数做鲁棒 Z-Score 离群检测；点越大代表疵点压力越高，越靠上不良率越高。", f"Source: {method_factory} QC work-order data. Logic: robust Z-Score outlier detection using inspected qty, defect rate, and defect count; larger points mean higher defect pressure, higher position means higher defect rate."))

    left, right = st.columns(2)
    with left:
        st.subheader(t("来料与过程周度关系｜周度关联分析", "Material vs Process by Week | Weekly Association"))
        if weekly_material_process.empty:
            st.info(t(f"{method_factory_name} 当前没有可连接的来料和过程周度数据。", f"No linked weekly material/process data is available for {method_factory_name}."))
        else:
            weekly_plot = weekly_material_process.copy()
            weekly_plot["plot_size"] = np.log1p(weekly_plot["qty"].clip(lower=1)) * 7 + 12
            fig = px.scatter(
                weekly_plot,
                x="material_issues",
                y="defect_rate",
                size="plot_size",
                size_max=38,
                color="factory",
                hover_data=["week", "defects"],
                labels={"material_issues": t("来料问题数", "Material issues"), "defect_rate": t("过程/成品不良率", "QC defect rate")},
            )
            fig.update_yaxes(tickformat=".1%")
            plot_chart(fig, 390)
            st.caption(t(f"数据来源：{method_factory} Material data + QC data。算法：按周连接来料问题批次与同周过程/成品不良率；右上角代表来料问题多且质量表现差，适合优先复盘。", f"Source: {method_factory} Material data + QC data. Logic: weekly material issue batches are linked with same-week QC defect rate; upper-right means more material issues and worse quality."))

    with right:
        st.subheader(t("整改前后效果｜Before/After 对照评分", "Before / After Effect | Matched Period Scoring"))
        if cap_effectiveness.empty:
            st.info(t(f"{method_factory_name} 当前数据不足以形成前后周期对比。", f"{method_factory_name} does not have enough data for a before/after comparison."))
        else:
            cap_plot = cap_effectiveness.copy()
            cap_plot["process_view"] = cap_plot["factory_code"] + " / " + cap_plot["process"].astype(str)
            fig = px.bar(
                cap_plot.sort_values("effectiveness_score"),
                x="effectiveness_score",
                y="process_view",
                color="recurrence",
                orientation="h",
                labels={"effectiveness_score": t("有效性评分", "Effectiveness score"), "process_view": t("工厂 / 工序", "Factory / Process")},
            )
            plot_chart(fig, 390)
            st.caption(t(f"数据来源：{method_factory} QC data。算法：对比整改前后周期不良率并计算有效性评分；分数越高代表改善越明显，复发项需要继续追踪。", f"Source: {method_factory} QC data. Logic: compares before/after defect rates and converts improvement into an effectiveness score; higher is better, recurring items need follow-up."))

            with st.expander(t("整改效果明细（可选）", "Effectiveness detail (optional)")):
                cap_view = cap_effectiveness.rename(
                    columns={
                        "factory_code": t("工厂", "Factory"),
                        "process": t("相关风险", "Related Risk"),
                        "before_rate": t("整改前不良率", "Before"),
                        "after_rate": t("整改后不良率", "After"),
                        "effectiveness_score": t("有效性评分", "Effectiveness Score"),
                        "recurrence": t("复发", "Recurrence"),
                        "next_decision": t("下一步", "Next Decision"),
                    }
                )
                dataframe_with_format(
                    cap_view,
                    column_config={
                        t("整改前不良率", "Before"): st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=0.1),
                        t("整改后不良率", "After"): st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=0.1),
                        t("有效性评分", "Effectiveness Score"): st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=100),
                    },
                    height=300,
                )
