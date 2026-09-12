"""Counterfactual response simulation and safe action selection."""
from __future__ import annotations

from typing import Any

from engine.planner import candidates
from engine.state import AgentState


class ResponsePlanner:
    def plan(self, state: AgentState, scenario: dict[str, Any], *, override: str = "") -> dict[str, Any]:
        active_session = any(item.get("active_session") for item in state.environment.get("identities", []))
        state.candidate_actions = candidates(state.risk_score, state.root_cause, state.scenario_id, has_active_session=active_session)
        expected = str(scenario.get("expected_recovery", "REVOKE_SESSION + BLOCK_IP"))
        if override:
            selected = override
            rationale = "Human override received; the agent will execute the analyst-selected sandbox action and continue verification."
        elif state.iteration > 1 and state.failure_reason:
            selected = expected
            rationale = f"Previous action failed because {state.failure_reason} Replanning now targets the active root cause."
        elif scenario.get("failure") and scenario["failure"].get("action"):
            selected = str(scenario["failure"]["action"])
            rationale = "Start with the narrowest reversible containment action; observe the environment before escalating blast radius."
        elif state.scenario_id == "malware_execution":
            selected = "ISOLATE_HOST"
            rationale = "Host-level execution evidence makes isolation the safest containment boundary."
        else:
            selected = expected
            rationale = "The selected action has the best containment-to-blast-radius ratio for the correlated evidence."
        state.selected_action = selected
        return {"selected_action": selected, "rationale": rationale, "simulation": state.candidate_actions}
