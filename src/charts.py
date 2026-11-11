"""Pick a sensible chart from the shape of a result table.

Rules (simple on purpose, easy to explain):
  * 1 row x 1 number            -> KPI card (no chart)
  * a date/month column + number -> line chart
  * a text column + number       -> bar chart (up to 30 rows)
  * anything else                -> table only
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DATE_HINTS = ("date", "month", "year", "quarter", "period", "week", "day")


@dataclass
class ChartSpec:
    kind: str                     # kpi | line | bar | none
    figure: go.Figure | None = None
    kpi_label: str = ""
    kpi_value: str = ""


def _is_time_column(df: pd.DataFrame, col: str) -> bool:
    if any(h in col.lower() for h in DATE_HINTS):
        return True
    sample = df[col].dropna().astype(str).head(5)
    return bool(not sample.empty and sample.str.match(r"^\d{4}(-\d{2})?(-\d{2})?$").all())


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


def choose_chart(df: pd.DataFrame | None) -> ChartSpec:
    if df is None or df.empty:
        return ChartSpec("none")
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not c.lower().endswith("_id")]
    others = [c for c in df.columns if c not in numeric]

    if len(df) == 1 and len(df.columns) == 1 and numeric:
        col = numeric[0]
        return ChartSpec("kpi", kpi_label=col.replace("_", " ").capitalize(),
                         kpi_value=_format_number(df[col].iloc[0]))
    if not numeric or not others or len(df) < 2:
        return ChartSpec("none")

    x = others[0]
    y = numeric[0]
    if _is_time_column(df, x):
        fig = px.line(df.sort_values(x), x=x, y=numeric[:3], markers=True)
        kind = "line"
    elif len(df) <= 30:
        color = others[1] if len(others) > 1 and df[others[1]].nunique() <= 8 else None
        fig = px.bar(df, x=x, y=y, color=color)
        kind = "bar"
    else:
        return ChartSpec("none")
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=360,
                      xaxis_title=x.replace("_", " "), yaxis_title=y.replace("_", " "),
                      legend_title_text="")
    return ChartSpec(kind, figure=fig)
