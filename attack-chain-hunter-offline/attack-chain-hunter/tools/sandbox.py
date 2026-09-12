"""Compose local response simulators without touching real systems."""
from __future__ import annotations

from engine.state import AgentState
from tools import firewall_simulator, host_simulator, session_simulator


def execute(state: AgentState, scenario: dict, action: str) -> dict[str, object]:
    if action == "BLOCK_IP":
        return firewall_simulator.execute(state, scenario, action)
    if action == "REVOKE_SESSION":
        return session_simulator.execute(state, action)
    if action == "ISOLATE_HOST":
        return host_simulator.execute(state, scenario, action)
    if action == "REVOKE_SESSION + BLOCK_IP":
        session_result = session_simulator.execute(state, action)
        firewall_result = firewall_simulator.execute(state, scenario, "BLOCK_IP", force=True)
        if session_result.get("status") != "success":
            return session_result
        return {"status": firewall_result.get("status", "success"), "action": action, "reason": f"{session_result.get('reason')} {firewall_result.get('reason')}", "parts": [session_result, firewall_result]}
    if action == "MONITOR":
        return {"status": "success", "action": action, "reason": "Synthetic telemetry level increased; no containment mutation applied."}
    return {"status": "rejected", "action": action, "reason": "Unknown sandbox action."}
