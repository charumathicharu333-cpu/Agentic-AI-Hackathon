"""Shared planning helpers for deterministic response decisions."""
from __future__ import annotations

from typing import Any


ACTION_CATALOG: list[dict[str, Any]] = [
    {"action": "BLOCK_IP", "label": "Block source IP", "effectiveness": 65, "risk": "LOW", "blast_radius": "narrow", "description": "Stop new traffic from the observed source."},
    {"action": "ISOLATE_HOST", "label": "Isolate affected host", "effectiveness": 88, "risk": "MEDIUM", "blast_radius": "host", "description": "Quarantine the host from the simulated network."},
    {"action": "REVOKE_SESSION + BLOCK_IP", "label": "Revoke session + block IP", "effectiveness": 96, "risk": "LOW", "blast_radius": "identity + network", "description": "Remove the active access path and stop the observed source."},
    {"action": "REVOKE_SESSION", "label": "Revoke active session", "effectiveness": 84, "risk": "LOW", "blast_radius": "identity", "description": "Invalidate the active session without changing host availability."},
    {"action": "MONITOR", "label": "Increase monitoring", "effectiveness": 32, "risk": "LOW", "blast_radius": "none", "description": "Observe without containment; useful only when confidence is low."},
]


def candidates(risk: int, root_cause: str, scenario_id: str, *, has_active_session: bool = True) -> list[dict[str, Any]]:
    result = [dict(item) for item in ACTION_CATALOG]
    if not has_active_session:
        result = [item for item in result if "SESSION" not in item["action"]]
    for item in result:
        item["score"] = item["effectiveness"] + min(risk, 100) // 10
        item["decision_note"] = f"Matched to {root_cause.lower()} with {item['blast_radius']} blast radius."
    if scenario_id in {"credential_compromise", "data_exfiltration"}:
        result.sort(key=lambda item: (item["action"] != "BLOCK_IP", -item["score"]))
    elif scenario_id == "malware_execution":
        result.sort(key=lambda item: (item["action"] != "ISOLATE_HOST", -item["score"]))
    elif scenario_id in {"lateral_movement", "service_dependency_failure"}:
        result.sort(key=lambda item: (item["action"] != "ISOLATE_HOST", -item["score"]))
    else:
        result.sort(key=lambda item: (item["action"] != "REVOKE_SESSION", -item["score"]))
    return result


def action_definition(action: str) -> dict[str, Any] | None:
    for item in ACTION_CATALOG:
        if item["action"] == action:
            return item
    return None
