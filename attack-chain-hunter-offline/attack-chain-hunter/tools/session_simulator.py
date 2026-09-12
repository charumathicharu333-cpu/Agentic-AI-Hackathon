from __future__ import annotations

from engine.state import AgentState


def execute(state: AgentState, action: str) -> dict[str, object]:
    if action not in {"REVOKE_SESSION", "DISABLE_ACCOUNT", "REVOKE_SESSION + BLOCK_IP"}:
        return {"status": "rejected", "action": action, "reason": "Session simulator received an invalid action."}
    changed = 0
    for identity in state.environment.get("identities", []):
        if identity.get("active_session"):
            identity["active_session"] = False
            identity["compromised_status"] = "secured"
            changed += 1
    state.environment["malicious_traffic"] = False
    return {"status": "success", "action": action, "reason": f"{changed} synthetic active session(s) revoked.", "revoked_sessions": changed}
