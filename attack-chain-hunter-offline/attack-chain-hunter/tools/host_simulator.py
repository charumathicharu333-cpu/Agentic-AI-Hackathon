from __future__ import annotations

from engine.state import AgentState


def execute(state: AgentState, scenario: dict, action: str) -> dict[str, object]:
    if action not in {"ISOLATE_HOST", "RESTORE_HOST"}:
        return {"status": "rejected", "action": action, "reason": "Host simulator received an invalid action."}
    asset = (scenario.get("assets") or [{}])[0]
    hostname = str(asset.get("hostname", "unknown-host"))
    if action == "RESTORE_HOST":
        state.environment["isolated_hosts"] = [item for item in state.environment.get("isolated_hosts", []) if item != hostname]
        for service in state.environment.get("service_health", []):
            service["status"] = "healthy"
            service["dependency_status"] = "healthy"
            service["availability"] = 100
        return {"status": "success", "action": action, "reason": f"{hostname} restored and synthetic dependencies healthy.", "hostname": hostname}
    failure = scenario.get("failure") or {}
    if failure.get("action") == "ISOLATE_HOST" and (failure.get("type") == "service_failure" or any(item.get("dependency_status") == "unavailable" for item in state.environment.get("service_health", []))):
        return {"status": "service_failure", "action": action, "reason": failure.get("reason", "Required dependency is unavailable."), "hostname": hostname}
    if hostname not in state.environment.setdefault("isolated_hosts", []):
        state.environment["isolated_hosts"].append(hostname)
    state.environment["malicious_traffic"] = False
    return {"status": "success", "action": action, "reason": f"{hostname} isolated inside the sandbox.", "hostname": hostname}
