"""Look-and-feel helpers for the chat app: page style, header, typing indicator, streamed text.

Kept out of streamlit_app.py so they can be unit-tested without running the page.
"""
from __future__ import annotations

import html
import re
import time
from collections.abc import Iterator
from pathlib import Path

import plotly.graph_objects as go

STYLE_FILE = Path(__file__).with_name("style.css")
STREAM_DELAY_S = 0.012  # per word: fast enough not to slow the answer, slow enough to read as typing


def page_style() -> str:
    return f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>"


def hero_html(model: str, tables: int, rows: int) -> str:
    """Header with the animated 3D orb. The model name is user-typed, so it is escaped."""
    short = html.escape(model.rsplit("/", 1)[-1] or "no model")
    return f"""
<div class="ttd-hero">
  <div class="ttd-orb" aria-hidden="true"><i></i><i></i><i></i><span class="core"></span></div>
  <div class="ttd-hero-copy">
    <div class="ttd-chip"><span class="dot"></span>Online · {short} · read-only</div>
    <div class="ttd-title" role="heading" aria-level="1">TalkToData <span>AI</span></div>
    <div class="ttd-sub">Ask your HR &amp; payroll data in plain English. I write safe SQL, run it and explain
      the answer, and you can always see the query.</div>
    <div class="ttd-stats"><span>{tables} tables</span><span>{rows:,} rows</span><span>SQL guard on</span>
      <span>Fictional data</span></div>
  </div>
</div>"""


TYPING_HTML = """
<div class="ttd-typing" role="status">
  <span class="ttd-mini-orb" aria-hidden="true"></span>
  <span class="ttd-shimmer">Thinking</span><span class="ttd-dots" aria-hidden="true"><i></i><i></i><i></i></span>
  <small>picking tables → writing SQL → safety check → running it</small>
</div>"""


NEON = ["#2fe3c5", "#4fa9ff", "#8f7dff", "#ff6f8e", "#ffbf5e", "#43e293", "#6f93ff", "#2fc3e3"]
NEON_SCALE = [[0, "#4fa9ff"], [0.5, "#8f7dff"], [1, "#2fe3c5"]]


def style_figure(fig: go.Figure) -> go.Figure:
    """Give a chart the app's neon-on-glass look: transparent canvas, rounded bars, bold lines.

    Lines stay straight between points: a smoothed curve would invent dips and peaks the data does not have.
    """
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#c3cde6", size=13),
        colorway=NEON, barcornerradius=8, bargap=0.28, hoverlabel=dict(bgcolor="#101a2e", bordercolor="#2fe3c5"),
    )
    fig.update_xaxes(gridcolor="rgba(130,160,255,.08)", zeroline=False, linecolor="rgba(130,160,255,.2)")
    fig.update_yaxes(gridcolor="rgba(130,160,255,.1)", zeroline=False)
    bars = [t for t in fig.data if t.type == "bar"]
    if len(bars) == 1:  # one series: shade each bar by its value so the biggest glows most
        bars[0].update(marker=dict(color=bars[0].y, colorscale=NEON_SCALE, line=dict(width=0)))
    fig.update_traces(selector=dict(type="scatter"), line=dict(width=3),
                      marker=dict(size=7, line=dict(width=2, color="#050912")))
    lines = [t for t in fig.data if t.type == "scatter"]
    if len(lines) == 1:
        lines[0].update(line_color=NEON[0], fill="tozeroy", fillcolor="rgba(47,227,197,.10)")
    return fig


def word_stream(text: str, delay_s: float = STREAM_DELAY_S) -> Iterator[str]:
    """Yield the answer word by word (whitespace kept as-is) so it appears to be typed."""
    for part in re.split(r"(\s+)", text):
        if part:
            yield part
            if delay_s and not part.isspace():
                time.sleep(delay_s)
