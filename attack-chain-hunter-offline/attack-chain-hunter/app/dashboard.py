"""Judge-facing Streamlit dashboard for the offline agent."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components import attack_graph, hero, inject_css, metric, offline_panel, panel_end, panel_start, provenance
from engine.orchestrator import AgentController
from engine.reporting import build_report


def _controller() -> AgentController:
    if "controller" not in st.session_state:
        st.session_state.controller = AgentController(base_dir=ROOT, db_path=os.getenv("ACH_DB_PATH") or None)
        st.session_state.controller.reset("credential_compromise")
    return st.session_state.controller


def _df(rows: Any) -> pd.DataFrame:
    return pd.DataFrame(rows if isinstance(rows, list) else [rows])


def _run_progress(controller: AgentController, mode: str, scenario_id: str, action: str = "") -> None:
    status = st.empty()
    progress = st.progress(0, text="Preparing local agent...")

    def on_step(event: dict[str, Any], state: Any) -> None:
        fraction = min(1.0, len(state.timeline) / 25)
        progress.progress(fraction, text=f"{event['phase']} · {event['title']}")
        status.markdown(f"**{event['phase']}**  ·  {event['detail']}")

    if mode == "Human override":
        state = controller.run_with_override(action, scenario_id=scenario_id, step_delay=0.06, on_step=on_step)
    else:
        state = controller.run_demo(scenario_id=scenario_id, step_delay=0.06, on_step=on_step)
    st.session_state.state = state
    progress.progress(1.0, text="Workflow complete · state persisted locally")


def _sidebar(controller: AgentController) -> None:
    st.sidebar.markdown("### Mission control")
    scenario_ids = list(controller.scenarios)
    labels = {key: controller.scenarios[key].get("name", key) for key in scenario_ids}
    current_id = controller.state.scenario_id if controller.state else scenario_ids[0]
    selected = st.sidebar.selectbox("Scenario", scenario_ids, index=scenario_ids.index(current_id) if current_id in scenario_ids else 0, format_func=lambda key: labels[key])
    if controller.state and selected != controller.state.scenario_id:
        controller.reset(selected)
        st.session_state.state = controller.state
        st.rerun()
    mode = st.sidebar.radio("Control mode", ["Autonomous mode", "Human override"], index=0)
    override = st.sidebar.selectbox("Override action", ["BLOCK_IP", "ISOLATE_HOST", "REVOKE_SESSION", "REVOKE_SESSION + BLOCK_IP", "MONITOR"], disabled=mode != "Human override")
    st.sidebar.markdown("---")
    button_label = "🚀 RUN AUTONOMOUS DEMO" if mode == "Autonomous mode" else "▶ RUN WITH OVERRIDE"
    if st.sidebar.button(button_label, type="primary", use_container_width=True):
        _run_progress(controller, mode, selected, override)
        st.rerun()
    if st.sidebar.button("↻ Replay Incident", use_container_width=True):
        _run_progress(controller, mode, selected, override)
        st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.caption("Every action is validated, recorded, and applied only to the local synthetic sandbox.")
    st.sidebar.success("OFFLINE MODE · SANDBOX ACTIVE")


def _overview(state: Any, scenario: dict[str, Any]) -> None:
    st.markdown("#### Operational picture")
    cols = st.columns(6)
    values = [
        ("Risk score", f"{state.risk_score}/100", f"initial {state.initial_risk_score}"),
        ("Confidence", f"{state.confidence}%", "evidence-weighted"),
        ("Iterations", str(state.iteration), "replan count"),
        ("Evidence sources", str(state.evidence_sources), f"{state.tool_calls} tool calls"),
        ("Response", "VERIFIED" if state.final_status == "CONTAINED & VERIFIED" else "PENDING", "independent checks"),
        ("Status", "CONTAINED" if state.final_status == "CONTAINED & VERIFIED" else "ACTIVE", state.current_phase),
    ]
    for col, item in zip(cols, values):
        with col:
            metric(*item)
    left, right = st.columns([1.05, .95])
    with left:
        panel_start("INCIDENT SIGNAL", "What the agent is working on")
        alert = scenario.get("alert", {})
        st.markdown(f"**{alert.get('signature', 'Unknown')}** · `{state.incident_id}`")
        st.markdown(f"`{alert.get('source_ip', 'unknown')}` → `{alert.get('destination', 'unknown')}` · port `{alert.get('port', 'n/a')}`")
        st.markdown(f"Severity: **{alert.get('severity', 'unknown')}**  ·  Current phase: **{state.current_phase}**")
        provenance("ROOT CAUSE", state.root_cause)
        provenance("ATTACK STATUS", "Successful impact established from connected identity, log, network, asset, and vulnerability evidence." if state.confidence >= 72 else "Impact remains unconfirmed.")
        panel_end()
    with right:
        panel_start("DECISION PROVENANCE", "Why the agent changed course")
        latest = state.action_history[-1] if state.action_history else None
        provenance("SELECTED RESPONSE", latest.get("action", "Awaiting response") if latest else "Awaiting response")
        provenance("EVIDENCE", " · ".join(list(state.evidence)[:4]) or "No evidence yet")
        provenance("WHY", state.adaptation_reason or "The planner chose the narrowest reversible response before escalating.")
        panel_end()
    if state.final_status == "CONTAINED & VERIFIED":
        st.markdown(f"<div class='success-box'><h2>🟢 INCIDENT CONTAINED</h2><div class='big'>AUTONOMOUS RECOVERY VERIFIED</div><div>Attack path: <b>NEUTRALIZED</b> · Sessions: <b>0</b> · Suspicious traffic: <b>0</b> · Services: <b>HEALTHY</b></div><div class='small-muted'>Risk {state.initial_risk_score} → {state.risk_score} · {state.iteration} iteration(s) · {state.risk_reduction}% risk reduction</div></div>", unsafe_allow_html=True)


def _investigation(state: Any) -> None:
    left, right = st.columns([.9, 1.1])
    with left:
        panel_start("INVESTIGATION AGENT", "Evidence loop")
        st.markdown("**What do I know?**")
        st.markdown(" ".join(f"<span class='tag'>{key}</span>" for key in state.evidence), unsafe_allow_html=True)
        st.markdown("**What am I missing?**")
        if state.missing_evidence:
            st.warning(" · ".join(state.missing_evidence))
        else:
            st.success("Evidence sufficient for current decision")
        next_tool = state.missing_evidence[0] if state.missing_evidence else "Recheck after response"
        provenance("NEXT INVESTIGATION STEP", next_tool)
        provenance("REASON", "The agent selects a tool based on the unresolved control gap, not a fixed all-tools sweep.")
        panel_end()
    with right:
        panel_start("LOCAL TOOL LAYER", "Evidence register")
        rows = []
        for item in state.investigation_history:
            rows.append({"Tool": item.get("tool"), "Status": str(item.get("status", "")).upper(), "Evidence key": item.get("evidence_key"), "Summary": item.get("summary")})
        st.dataframe(_df(rows), use_container_width=True, hide_index=True)
        panel_end()
    panel_start("CORRELATION SNAPSHOT", "Most material observations")
    material = []
    for key, value in state.evidence.items():
        material.append({"Source": key, "Observation": json.dumps(value, default=str)[:220]})
    st.dataframe(_df(material), use_container_width=True, hide_index=True)
    panel_end()


def _graph(state: Any) -> None:
    left, right = st.columns([1.4, .6])
    with left:
        panel_start("ATTACK PATH", "Interactive chain state")
        attack_graph(state.attack_path)
        st.caption("Hover a node for its current state. Select a node at right for the audit view.")
        panel_end()
    with right:
        panel_start("NODE AUDIT", "Evidence and risk")
        labels = [node.get("label", node.get("id")) for node in state.attack_path]
        selected = st.selectbox("Inspect node", labels or ["No nodes"])
        node = next((item for item in state.attack_path if item.get("label") == selected), {})
        st.markdown(f"**Entity**  \n`{node.get('label', 'unknown')}`")
        st.markdown(f"**State**  \n`{str(node.get('state', 'unknown')).upper()}`")
        provenance("RELATED EVENTS", "; ".join(item.get("title", "") for item in state.timeline if item.get("phase") in {"EVIDENCE", "ANALYZE", "REPLAN"})[:320] or "Awaiting evidence")
        panel_end()


def _timeline(state: Any) -> None:
    panel_start("AGENT TIMELINE", "Goal → decision → tool → action → adaptation → verification")
    if not state.timeline:
        st.info("Run the demo to populate the auditable event stream.")
    for event in state.timeline:
        st.markdown(f"<div class='timeline-item'><div class='timeline-time'>{event.get('display_time', '')}</div><div class='timeline-phase'>{event.get('phase', '')}</div><div><div class='timeline-title'>{event.get('title', '')}</div><div class='timeline-detail'>{event.get('detail', '')}</div></div></div>", unsafe_allow_html=True)
    panel_end()


def _response(state: Any) -> None:
    left, right = st.columns([1.1, .9])
    with left:
        panel_start("RESPONSE PLANNER", "Counterfactual response simulator")
        rows = []
        for item in state.candidate_actions:
            rows.append({"Candidate": item.get("action"), "Effectiveness": f"{item.get('effectiveness')}%", "Risk": item.get("risk"), "Blast radius": item.get("blast_radius"), "Selected": "YES" if item.get("action") == state.selected_action else ""})
        st.dataframe(_df(rows), use_container_width=True, hide_index=True)
        provenance("SELECTED", state.selected_action or "No action selected")
        provenance("WHY", (state.action_history[-1].get("reason") if state.action_history else "No response executed yet") or "No rationale recorded")
        panel_end()
    with right:
        panel_start("SANDBOX RESULT", "Observe, diagnose, recover")
        if state.action_result:
            result = state.action_result
            st.markdown(f"### {str(result.get('status', 'pending')).upper()}")
            st.markdown(result.get("reason", "No result detail."))
        if state.failure_reason:
            provenance("FAILURE REASON", state.failure_reason)
            provenance("ADAPTATION", state.adaptation_reason)
            recovery_action = state.action_history[-1].get("action", state.selected_action) if state.action_history else state.selected_action
            provenance("RECOVERY", recovery_action)
        panel_end()


def _verification(state: Any) -> None:
    panel_start("VERIFICATION AGENT", "Independent containment checks")
    rows = [{"Check": item.get("check"), "Observed": item.get("observed"), "Result": "PASS" if item.get("passed") else "FAIL"} for item in state.verification_results]
    if rows:
        st.dataframe(_df(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Verification runs after a sandbox action.")
    if state.final_status == "CONTAINED & VERIFIED":
        st.success("All checks passed. The final state is independently verified, not assumed from the action response.")
    else:
        st.warning("Containment is not yet verified.")
    panel_end()


def _scenarios(controller: AgentController) -> None:
    panel_start("SCENARIO LAB", "Six synthetic incidents, one local controller")
    rows = []
    for key, scenario in controller.scenarios.items():
        rows.append({"ID": scenario.get("incident_id"), "Scenario": scenario.get("name"), "Severity": scenario.get("alert", {}).get("severity"), "Failure mode": (scenario.get("failure") or {}).get("type", "none"), "Expected recovery": scenario.get("expected_recovery")})
    st.dataframe(_df(rows), use_container_width=True, hide_index=True)
    st.caption("Use the Scenario selector in Mission control and press Replay Incident to restart any scenario from a clean sandbox state.")
    panel_end()


def _reports(state: Any) -> None:
    payload = build_report(state)
    panel_start("REPORTS", "Auditable local export")
    st.markdown(f"Incident report for `{state.incident_id}` includes evidence provenance, action attempts, adaptation, verification, and the complete timeline.")
    left, right = st.columns(2)
    with left:
        st.download_button("Download JSON report", json.dumps(payload, indent=2), file_name=f"{state.incident_id}.json", mime="application/json", use_container_width=True)
    with right:
        html_path = Path(state.report_paths.get("html", ""))
        html_body = html_path.read_text(encoding="utf-8") if html_path.is_file() else "<h1>Run the demo to generate the HTML report.</h1>"
        st.download_button("Download HTML report", html_body, file_name=f"{state.incident_id}.html", mime="text/html", use_container_width=True)
    st.json({"json": state.report_paths.get("json", "not generated"), "html": state.report_paths.get("html", "not generated")})
    panel_end()


def _system(state: Any, controller: AgentController) -> None:
    offline_panel()
    panel_start("ARCHITECTURE", "Local control plane")
    st.code("Streamlit UI → Agent Controller → Logical Agents → Local Tool Layer → Sandbox Simulators → Verification Engine → SQLite + Reports", language="text")
    st.markdown("No network calls are made by the engine. Synthetic JSON scenarios are loaded from `data/scenarios/`; SQLite snapshots are written to `database/soc.db`.")
    panel_end()
    panel_start("PERSISTED STATE", "Current state object")
    st.json(state.to_dict())
    panel_end()


def render_app() -> None:
    st.set_page_config(page_title="Attack-Chain Hunter", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
    inject_css()
    controller = _controller()
    _sidebar(controller)
    hero()
    state = controller.state
    if state is None:
        state = controller.reset("credential_compromise")
    scenario = controller.scenarios.get(state.scenario_id, {})
    st.markdown(f"<div class='small-muted' style='margin:1rem 0 .65rem'>ACTIVE INCIDENT · <b>{state.incident_id}</b> · {scenario.get('name', 'Local scenario')}</div>", unsafe_allow_html=True)
    tabs = st.tabs(["Overview", "Investigation", "Attack Graph", "Agent Timeline", "Response", "Verification", "Scenarios", "Reports", "System"])
    with tabs[0]:
        _overview(state, scenario)
    with tabs[1]:
        _investigation(state)
    with tabs[2]:
        _graph(state)
    with tabs[3]:
        _timeline(state)
    with tabs[4]:
        _response(state)
    with tabs[5]:
        _verification(state)
    with tabs[6]:
        _scenarios(controller)
    with tabs[7]:
        _reports(state)
    with tabs[8]:
        _system(state, controller)
