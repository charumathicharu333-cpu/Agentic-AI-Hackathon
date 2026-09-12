from __future__ import annotations

from typing import Any

from engine.state import AgentState


def execute(state: AgentState, scenario: dict[str, Any], action: str, *, force: bool = False) -> dict[str, Any]:
    alert = scenario.get("alert", {})
    source_ip = str(alert.get("source_ip", "unknown"))
    if action not in {"BLOCK_IP", "UNBLOCK_IP"}:
        return {"status": "rejected", "action": action, "reason": "Firewall simulator only accepts BLOCK_IP or UNBLOCK_IP."}
    if action == "UNBLOCK_IP":
        state.environment["blocked_ips"] = [item for item in state.environment.get("blocked_ips", []) if item != source_ip]
        state.environment["malicious_traffic"] = True
        return {"status": "success", "action": action, "reason": f"Synthetic block removed for {source_ip}.", "source_ip": source_ip}
    if source_ip not in state.environment.setdefault("blocked_ips", []):
        state.environment["blocked_ips"].append(source_ip)
    failure = scenario.get("failure") or {}
    if failure.get("action") == "BLOCK_IP" and not force and not any(item.get("action") == "REVOKE_SESSION + BLOCK_IP" and item.get("status") == "success" for item in state.action_history):
        return {"status": "partial_failure", "action": action, "reason": failure.get("reason", "An active session remains."), "source_ip": source_ip}
    state.environment["malicious_traffic"] = False
    return {"status": "success", "action": action, "reason": f"Synthetic traffic from {source_ip} is blocked.", "source_ip": source_ip}
