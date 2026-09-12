"""Small reusable Streamlit presentation components."""
from __future__ import annotations

from typing import Any

import networkx as nx
import plotly.graph_objects as go
import streamlit as st


COLORS = {
    "bg": "#07111f",
    "panel": "#0f1c2e",
    "border": "#203452",
    "text": "#e7f0f7",
    "muted": "#91a6ba",
    "teal": "#66e3cf",
    "lime": "#b9ed71",
    "orange": "#f6bd72",
    "red": "#ff7b8b",
    "blue": "#7db7ff",
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#e7f0f7; --muted:#91a6ba; --panel:#0f1c2e; --line:#203452; --teal:#66e3cf; --lime:#b9ed71; --red:#ff7b8b; --orange:#f6bd72; }
        .stApp { background: radial-gradient(circle at 80% -10%, #17375a 0, #07111f 38%, #07111f 100%); color:var(--ink); font-family:Inter,Arial,sans-serif; }
        [data-testid='stSidebar'] { background:#091626; border-right:1px solid var(--line); }
        [data-testid='stSidebar'] * { color:var(--ink); }
        .block-container { max-width:1500px; padding-top:2rem; padding-bottom:3rem; }
        .hero { padding:1.5rem 1.8rem 1.35rem; border:1px solid #23425b; border-radius:24px; background:linear-gradient(120deg,rgba(14,40,61,.95),rgba(10,25,42,.72)); box-shadow:0 24px 80px rgba(0,0,0,.22); }
        .eyebrow { color:var(--teal); font:500 .72rem ui-monospace,SFMono-Regular,monospace; letter-spacing:.18em; text-transform:uppercase; }
        .hero h1 { margin:.4rem 0 .35rem; font-size:clamp(1.8rem,4vw,3.15rem); line-height:1.02; letter-spacing:-.055em; }
        .hero p { color:var(--muted); max-width:850px; margin:0; font-size:1rem; }
        .status-pill { display:inline-flex; align-items:center; gap:.45rem; color:var(--lime); font:500 .74rem ui-monospace,SFMono-Regular,monospace; letter-spacing:.08em; margin-top:1rem; }
        .status-dot { width:8px; height:8px; border-radius:50%; background:var(--lime); box-shadow:0 0 14px var(--lime); }
        .metric { background:rgba(15,28,46,.88); border:1px solid var(--line); border-radius:16px; padding:1rem 1.1rem; min-height:108px; }
        .metric-label { color:var(--muted); font:500 .68rem ui-monospace,SFMono-Regular,monospace; letter-spacing:.08em; text-transform:uppercase; }
        .metric-value { font-size:1.65rem; font-weight:700; letter-spacing:-.04em; margin-top:.45rem; }
        .metric-note { color:var(--muted); font-size:.76rem; margin-top:.2rem; }
        .panel { background:rgba(15,28,46,.78); border:1px solid var(--line); border-radius:18px; padding:1.25rem; margin-bottom:1rem; }
        .panel h3 { margin:0 0 .8rem; font-size:1.08rem; }
        .panel-kicker { color:var(--teal); font:500 .68rem ui-monospace,SFMono-Regular,monospace; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.5rem; }
        .provenance { border-left:3px solid var(--teal); background:#0b192b; border-radius:0 12px 12px 0; padding:.9rem 1rem; margin:.55rem 0; }
        .provenance b { color:var(--teal); font:500 .7rem ui-monospace,SFMono-Regular,monospace; letter-spacing:.08em; }
        .provenance p { margin:.35rem 0 0; color:var(--ink); font-size:.9rem; }
        .tag { display:inline-block; border:1px solid #2a4962; border-radius:999px; padding:.23rem .5rem; margin:.15rem .2rem .15rem 0; color:var(--muted); font:500 .68rem ui-monospace,SFMono-Regular,monospace; }
        .success-box { background:linear-gradient(135deg,#102d2d,#0b1f2b); border:1px solid #3b886f; border-radius:22px; padding:1.5rem; text-align:center; }
        .success-box h2 { color:var(--lime); margin:0; letter-spacing:-.04em; }
        .success-box .big { font-size:1.65rem; font-weight:700; color:var(--teal); margin:.7rem 0; }
        .timeline-item { display:grid; grid-template-columns:72px 100px 1fr; gap:.8rem; padding:.75rem .4rem; border-bottom:1px solid rgba(32,52,82,.75); }
        .timeline-time, .timeline-phase { font:500 .68rem ui-monospace,SFMono-Regular,monospace; color:var(--teal); }
        .timeline-phase { color:var(--orange); }
        .timeline-title { font-weight:600; }
        .timeline-detail { color:var(--muted); font-size:.86rem; margin-top:.2rem; }
        .offline-grid { display:grid; grid-template-columns:1fr 1fr; gap:.55rem; }
        .offline-item { padding:.7rem; background:#0b192b; border:1px solid #1d314c; border-radius:12px; }
        .offline-item span { display:block; color:var(--muted); font-size:.73rem; }
        .offline-item strong { color:var(--lime); font:500 .76rem ui-monospace,SFMono-Regular,monospace; }
        .small-muted { color:var(--muted); font-size:.82rem; }
        div[data-testid='stMetric'] { background:rgba(15,28,46,.75); border:1px solid var(--line); padding:1rem; border-radius:16px; }
        button[kind='primary'] { background:linear-gradient(100deg,#2ec5b0,#87dd9a); color:#07111f; border:0; font-weight:700; }
        .stTabs [data-baseweb='tab-list'] { gap:.45rem; border-bottom:1px solid var(--line); }
        .stTabs [data-baseweb='tab'] { color:var(--muted); padding:.65rem .8rem; }
        .stTabs [aria-selected='true'] { color:var(--teal); }
        @media (max-width: 720px) { .timeline-item { grid-template-columns:64px 1fr; } .timeline-item > div:nth-child(3) { grid-column:2; } .offline-grid { grid-template-columns:1fr; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero() -> None:
    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow">Offline SOC Sandbox · Tech Zephyr 4.0 · Track 5</div>
          <h1>Autonomous Attack-Chain Hunter<br><span style="color:#66e3cf">&amp; Recovery Agent</span></h1>
          <p>Investigate → Understand → Respond → Adapt → Verify. A deterministic, auditable agent that changes its plan when the sandbox changes.</p>
          <div class="status-pill"><span class="status-dot"></span>SYSTEM READY · LOCAL SYNTHETIC DATA · PRODUCTION ACCESS DISABLED</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def metric(label: str, value: str, note: str = "") -> None:
    st.markdown(f"<div class='metric'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)


def panel_start(kicker: str, title: str) -> None:
    st.markdown(f"<div class='panel'><div class='panel-kicker'>{kicker}</div><h3>{title}</h3>", unsafe_allow_html=True)


def panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def provenance(label: str, body: str) -> None:
    st.markdown(f"<div class='provenance'><b>{label}</b><p>{body}</p></div>", unsafe_allow_html=True)


def offline_panel() -> None:
    st.markdown(
        """
        <div class="panel"><div class="panel-kicker">System mode</div><h3>Offline by construction</h3>
        <div class="offline-grid">
          <div class="offline-item"><span>Internet</span><strong>NOT REQUIRED</strong></div>
          <div class="offline-item"><span>External API</span><strong>NOT REQUIRED</strong></div>
          <div class="offline-item"><span>Cloud credentials</span><strong>NOT REQUIRED</strong></div>
          <div class="offline-item"><span>Sandbox</span><strong>ACTIVE</strong></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )


def attack_graph(nodes: list[dict[str, Any]]) -> None:
    graph = nx.DiGraph()
    for index, node in enumerate(nodes):
        graph.add_node(node.get("id", str(index)), **node)
        if index:
            graph.add_edge(nodes[index - 1].get("id", str(index - 1)), node.get("id", str(index)))
    positions = nx.spring_layout(graph, seed=9, k=1.7)
    edge_x: list[float] = []
    edge_y: list[float] = []
    for start, end in graph.edges:
        edge_x.extend([positions[start][0], positions[end][0], None])
        edge_y.extend([positions[start][1], positions[end][1], None])
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"color": "#2f5270", "width": 2}, hoverinfo="none")
    color_map = {"unknown": "#91a6ba", "suspicious": "#f6bd72", "compromised": "#ff7b8b", "contained": "#7db7ff", "verified": "#b9ed71"}
    node_x = [positions[key][0] for key in graph.nodes]
    node_y = [positions[key][1] for key in graph.nodes]
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[graph.nodes[key].get("label", key) for key in graph.nodes],
        textposition="bottom center",
        hovertext=[f"{graph.nodes[key].get('label', key)} · {graph.nodes[key].get('state', 'unknown').upper()}" for key in graph.nodes],
        hoverinfo="text",
        marker={"size": 38, "color": [color_map.get(graph.nodes[key].get("state", "unknown"), "#91a6ba") for key in graph.nodes], "line": {"width": 2, "color": "#dce9f3"}},
        textfont={"color": "#e7f0f7", "size": 11},
    )
    figure = go.Figure([edge_trace, node_trace])
    figure.update_layout(height=390, margin={"l": 0, "r": 0, "t": 10, "b": 10}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis={"visible": False}, yaxis={"visible": False}, showlegend=False)
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
