"""Failure interpretation and evidence-driven replanning."""
from __future__ import annotations

from typing import Any

from agents.investigation_agent import InvestigationAgent
from engine.state import AgentState


class RecoveryAgent:
    def adapt(self, state: AgentState, scenario: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        state.failure_reason = str(result.get("reason", "Sandbox action did not complete."))
        state.iteration += 1
        if result.get("status") == "partial_failure":
            state.adaptation_reason = "IP blocking changed the network edge but did not remove the active session. Request identity and authentication evidence again."
            next_evidence = ["Identity Tool", "Server Log Tool"]
        elif result.get("status") == "service_failure":
            state.adaptation_reason = "Host isolation would widen the dependency outage. Check service health, then prefer narrower identity and network containment."
            next_evidence = ["Identity Tool", "Service Health Tool"]
        else:
            state.adaptation_reason = "The observed result differs from the expected containment state. Re-check identity and service evidence before replanning."
            next_evidence = ["Identity Tool", "Service Health Tool"]
        state.missing_evidence = next_evidence
        return {"failure_reason": state.failure_reason, "adaptation_reason": state.adaptation_reason, "requested_evidence": next_evidence}
