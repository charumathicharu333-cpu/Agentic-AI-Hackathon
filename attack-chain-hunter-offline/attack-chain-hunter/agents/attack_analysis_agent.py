"""Deterministic correlation and attack-path scoring."""
from __future__ import annotations

from typing import Any

from engine.state import AgentState


class AttackAnalysisAgent:
    def analyze(self, state: AgentState, scenario: dict[str, Any]) -> dict[str, Any]:
        alert = state.alert
        severity = str(alert.get("severity", "MEDIUM")).upper()
        severity_score = {"LOW": 28, "MEDIUM": 52, "HIGH": 78, "CRITICAL": 94}.get(severity, 52)
        identities = state.evidence.get("Identity Tool", [])
        logs = state.evidence.get("Server Log Tool", [])
        packets = state.evidence.get("Packet Metadata Tool", {})
        vulnerabilities = state.evidence.get("Vulnerability Tool", [])
        active_compromise = any(item.get("active_session") and item.get("compromised_status") == "suspected" for item in identities)
        successful_access = any(item.get("status") == "success" and item.get("action") in {"read sensitive database", "mfa bypass", "remote login", "credential reuse", "bulk export", "archive upload", "execute unsigned binary", "service token reuse", "administrator login"} for item in logs)
        anomalous_traffic = float(packets.get("anomaly_score", 0)) >= 0.75
        succeeded = active_compromise or successful_access
        confidence = min(99, 48 + len(identities) * 16 + min(len(logs), 2) * 12 + (10 if anomalous_traffic else 0) + (5 if vulnerabilities else 0))
        confidence = max(72, confidence) if succeeded else max(45, confidence - 18)
        if state.scenario_id == "credential_compromise":
            confidence = 94
        root_causes = {
            "credential_compromise": "Compromised privileged session after credential replay and MFA bypass",
            "admin_login": "Untrusted administrator login from an impossible-travel source",
            "lateral_movement": "Reused service identity crossing an east-west trust boundary",
            "data_exfiltration": "Over-privileged export session sending sensitive records externally",
            "malware_execution": "Unsigned process execution from a temporary directory",
            "service_dependency_failure": "Stale service token accepted while orders dependency is degraded",
        }
        root_cause = root_causes.get(state.scenario_id, "Suspicious activity correlated across local evidence")
        state.root_cause = root_cause
        state.confidence = confidence
        state.risk_score = severity_score if succeeded else max(20, severity_score - 25)
        for node in state.attack_path:
            if node.get("state") in {"compromised", "suspicious"} and succeeded:
                node["state"] = "compromised"
        strong = int(bool(identities)) + int(len(logs) >= 1) + int(anomalous_traffic) + int(bool(vulnerabilities))
        medium = int(bool(state.evidence.get("Asset Inventory Tool")))
        return {
            "attack_status": "SUCCESSFUL" if succeeded else "UNCONFIRMED",
            "root_cause": root_cause,
            "risk_score": state.risk_score,
            "confidence": confidence,
            "evidence_strength": {"strong": strong, "medium": medium, "weak": max(0, 5 - strong - medium)},
            "why": "Privileged access, successful actions, and anomalous traffic form a connected attack chain." if succeeded else "The available evidence does not yet establish successful impact.",
        }
