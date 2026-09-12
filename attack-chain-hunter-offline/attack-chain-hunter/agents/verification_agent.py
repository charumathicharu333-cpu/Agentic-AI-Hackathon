"""Independent checks after every response attempt."""
from __future__ import annotations

from typing import Any

from engine.state import AgentState


class VerificationAgent:
    def verify(self, state: AgentState, scenario: dict[str, Any]) -> list[dict[str, Any]]:
        sessions = sum(1 for identity in state.environment.get("identities", []) if identity.get("active_session"))
        suspicious_activity = 1 if state.environment.get("malicious_traffic") else 0
        required = scenario.get("verification", {}).get("required_services", [])
        services = {item.get("service"): item for item in state.environment.get("service_health", [])}
        service_ok = all(services.get(name, {}).get("status") == "healthy" and services.get(name, {}).get("dependency_status") == "healthy" for name in required)
        checks = [
            {"check": "Network threat removed", "passed": suspicious_activity == 0, "observed": f"suspicious traffic = {suspicious_activity}"},
            {"check": "Active compromised sessions = 0", "passed": sessions == 0, "observed": f"active sessions = {sessions}"},
            {"check": "Suspicious account activity = 0", "passed": sessions == 0, "observed": "account state is secured" if sessions == 0 else "active identity remains"},
            {"check": "Attack path inactive", "passed": suspicious_activity == 0 and sessions == 0, "observed": "path state = inactive" if suspicious_activity == 0 and sessions == 0 else "path still has an active edge"},
            {"check": "Required service healthy", "passed": service_ok, "observed": "all dependencies healthy" if service_ok else "dependency or service unavailable"},
        ]
        state.verification_results = checks
        passed = all(item["passed"] for item in checks)
        if passed:
            state.risk_score = 8
            state.final_status = "CONTAINED & VERIFIED"
            state.successful_recovery = state.iteration > 1
            for node in state.attack_path:
                node["state"] = "verified"
        else:
            state.final_status = "CONTAINMENT PENDING"
        return checks
