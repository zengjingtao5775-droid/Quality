"""Shared TU/BME presentation components.

Callers supply already-aggregated data, rates and cumulative shares. This layer
never chooses a denominator, reporting period or source population.
"""
from __future__ import annotations

import html
import re

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


QUALITY_SERIES_COLORS = ["#2855C5", "#148A83", "#6B5CC5", "#D98200", "#C83C55", "#475467"]


def apply_quality_chart_style(fig: go.Figure, *, height: int | None = None,
                              showlegend: bool | None = None) -> go.Figure:
    layout = {
        "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "#FFFFFF",
        "font": {"family": "Inter, PingFang SC, Microsoft YaHei, sans-serif", "size": 14, "color": "#475467"},
        "hoverlabel": {"align": "left", "font_size": 14},
    }
    if height is not None:
        layout["height"] = height
    if showlegend is not None:
        layout["showlegend"] = showlegend
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor="#E7EAF0", zerolinecolor="#E7EAF0", tickfont={"size": 13})
    fig.update_yaxes(gridcolor="#E7EAF0", zerolinecolor="#E7EAF0", tickfont={"size": 13})
    return fig


def style_quality_trend(fig: go.Figure, *, height: int, is_rate: bool = True,
                        monthly: bool = False, tick_size: int = 11,
                        month_step: int = 1, show_year: bool = False) -> go.Figure:
    apply_quality_chart_style(fig, height=height, showlegend=len(fig.data) > 1)
    fig.update_traces(line=dict(width=2), marker=dict(size=6))
    fig.update_layout(margin=dict(l=8, r=8, t=25, b=25),
                      legend=dict(orientation="h", y=1.12, x=0, title_text="", font_size=11))
    fig.update_xaxes(title_text=None, tickangle=0, automargin=True, tickfont=dict(size=tick_size))
    if monthly:
        # Cross-year labels need room for the year in narrow three-column cards.
        interval = max(month_step, 3) if show_year and month_step > 1 else month_step
        fig.update_xaxes(tickformat="%b<br>%Y" if show_year else "%b", dtick=f"M{interval}")
    fig.update_yaxes(title_text=None, tickformat=".2%" if is_rate else ",.0f", rangemode="tozero")
    return fig


def build_quality_pareto(ranked: pd.DataFrame, *, name_col: str,
                         qty_col: str, cumulative_col: str, height: int = 245,
                         quantity_label: str = "Quantity",
                         cumulative_label: str = "Cumulative share",
                         issue_label: str = "Issue") -> go.Figure:
    """Render supplied cumulative shares without renormalizing a Top-N subset."""
    labels = [str(i) for i in range(1, len(ranked) + 1)]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=labels, y=ranked[qty_col], name=quantity_label,
        marker_color="#4f6edb", text=ranked[qty_col], texttemplate="%{text:,.0f}",
        textposition="outside", cliponaxis=False, customdata=ranked[[name_col]],
        hovertemplate=f"{issue_label}: %{{customdata[0]}}<br>{quantity_label}: %{{y:,.0f}}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=labels, y=ranked[cumulative_col], name=cumulative_label,
        mode="lines+markers", line=dict(color="#d98200", width=2), marker=dict(size=6),
        hovertemplate=f"{cumulative_label}: %{{y:.1%}}<extra></extra>",
    ), secondary_y=True)
    apply_quality_chart_style(fig, height=height, showlegend=False)
    fig.update_layout(margin=dict(l=8, r=8, t=28, b=30), bargap=.28)
    fig.update_xaxes(title_text=None, tickangle=0, automargin=True, tickfont=dict(size=10),
                     type="category", tickmode="array", tickvals=labels, ticktext=labels,
                     ticklabelstep=1, nticks=len(labels))
    maximum = float(ranked[qty_col].max()) if not ranked.empty else 0.0
    fig.update_yaxes(title_text=None, range=[0, maximum * 1.16 if maximum > 0 else 1], secondary_y=False)
    fig.update_yaxes(title_text=None, tickformat=".0%", range=[0, 1.08], secondary_y=True)
    return fig


def quality_pareto_rows_html(ranked: pd.DataFrame, *, name_col: str, qty_col: str) -> str:
    rows = []
    for index, (_, row) in enumerate(ranked.iterrows(), 1):
        full_name = re.sub(r"\s+", " ", str(row[name_col])).strip()
        display_name = re.sub(r"^\s*\d+[.、]\s*", "", full_name)
        rows.append(
            '<div class="bme-fg-pareto-row">'
            f'<span class="bme-fg-pareto-rank">#{index}</span>'
            f'<span class="bme-fg-pareto-name" title="{html.escape(full_name, quote=True)}">{html.escape(display_name)}</span>'
            f'<span class="bme-fg-pareto-qty">{float(row[qty_col]):,.0f}</span></div>'
        )
    return f'<div class="bme-fg-pareto-list">{"".join(rows)}</div>'
