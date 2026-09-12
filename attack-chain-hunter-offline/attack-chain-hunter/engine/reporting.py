"""Offline incident report generation."""
from __future__ import annotations

import html
import json
from pathlib import Path

from engine.state import AgentState


def build_report(state: AgentState) -> dict:
    return {
        "incident_summary": {
            "incident_id": state.incident_id,
            "scenario": state.scenario_name,
            "alert": state.alert,
            "final_status": state.final_status,
            "attack_status": "SUCCESSFUL" if state.confidence >= 72 else "UNCONFIRMED",
        },
        "evidence": state.evidence,
        "attack_path": state.attack_path,
        "risk": {"initial": state.initial_risk_score, "final": state.risk_score, "reduction_percent": state.risk_reduction},
        "root_cause": state.root_cause,
        "decisions": [{"action": item.get("action"), "status": item.get("status"), "reason": item.get("reason")} for item in state.action_history],
        "adaptation": {"failure": state.failure_reason, "reason": state.adaptation_reason, "successful_recovery": state.successful_recovery},
        "verification": state.verification_results,
        "metrics": {"iterations": state.iteration, "evidence_sources": state.evidence_sources, "tool_calls": state.tool_calls, "response_attempts": state.response_attempts, "failed_actions": state.failed_actions},
        "timeline": state.timeline,
    }


def generate_reports(state: AgentState, output_dir: str | Path) -> dict[str, str]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    safe_id = state.incident_id.replace("/", "-")
    payload = build_report(state)
    json_path = directory / f"{safe_id}.json"
    html_path = directory / f"{safe_id}.html"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rows = "".join(f"<tr><td>{html.escape(str(item.get('display_time', '')))}</td><td>{html.escape(str(item.get('phase', '')))}</td><td>{html.escape(str(item.get('title', '')))}</td><td>{html.escape(str(item.get('detail', '')))}</td></tr>" for item in state.timeline)
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Incident Report</title><style>body{font:15px system-ui;background:#0b1120;color:#e5edf5;max-width:1080px;margin:40px auto;padding:0 24px}section{background:#111c30;border:1px solid #243551;border-radius:16px;padding:22px;margin:16px 0}h1{color:#7ce3cf}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #243551;text-align:left}code{color:#f4c97b}</style></head><body>"
        f"<h1>Autonomous Attack-Chain Hunter</h1><p><code>{html.escape(state.incident_id)}</code> · {html.escape(state.final_status)}</p>"
        f"<section><h2>Summary</h2><p>{html.escape(state.root_cause)}</p><p>Risk {state.initial_risk_score} → {state.risk_score} · Confidence {state.confidence}% · Iterations {state.iteration}</p></section>"
        f"<section><h2>Auditable timeline</h2><table><thead><tr><th>Time</th><th>Phase</th><th>Event</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table></section>"
        f"<section><h2>Verification</h2><pre>{html.escape(json.dumps(state.verification_results, indent=2))}</pre></section></body></html>",
        encoding="utf-8",
    )
    return {"json": str(json_path), "html": str(html_path)}
