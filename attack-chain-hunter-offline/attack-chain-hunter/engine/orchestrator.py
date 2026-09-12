"""Stateful deterministic agent controller for the offline SOC sandbox."""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any, Callable

from agents.attack_analysis_agent import AttackAnalysisAgent
from agents.investigation_agent import InvestigationAgent
from agents.recovery_agent import RecoveryAgent
from agents.response_planner import ResponsePlanner
from agents.verification_agent import VerificationAgent
from engine.event_bus import EventBus
from engine.reporting import generate_reports
from engine.state import AgentState, StateStore
from tools import asset_tool, identity_tool, nids_tool, packet_tool, server_log_tool, service_health, vulnerability_tool
from tools.sandbox import execute as execute_sandbox


ToolFunction = Callable[[dict[str, Any]], dict[str, Any]]


class AgentController:
    def __init__(self, base_dir: str | Path | None = None, db_path: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path(__file__).resolve().parents[1])
        self.scenario_dir = self.base_dir / "data" / "scenarios"
        self.store = StateStore(db_path or self.base_dir / "database" / "soc.db")
        self.scenarios = self._load_scenarios()
        self.scenario: dict[str, Any] = {}
        self.state: AgentState | None = None
        self.bus: EventBus | None = None
        self.investigator = InvestigationAgent()
        self.analyzer = AttackAnalysisAgent()
        self.planner = ResponsePlanner()
        self.recovery = RecoveryAgent()
        self.verifier = VerificationAgent()
        self._callback: Callable[[dict[str, Any], AgentState], None] | None = None
        self._step_delay = 0.0

    def _load_scenarios(self) -> dict[str, dict[str, Any]]:
        loaded: dict[str, dict[str, Any]] = {}
        for path in sorted(self.scenario_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("id") and data.get("alert"):
                    loaded[str(data["id"])] = data
            except (OSError, json.JSONDecodeError):
                continue
        return loaded

    @property
    def ready(self) -> bool:
        return self.state is not None and bool(self.scenario)

    def reset(self, scenario_id: str = "credential_compromise") -> AgentState:
        self.scenario = copy.deepcopy(self.scenarios.get(scenario_id) or next(iter(self.scenarios.values())))
        self.state = AgentState.from_scenario(self.scenario)
        self.bus = EventBus(self.state, self.store)
        self.store.save(self.state)
        return self.state

    def _emit(self, phase: str, kind: str, title: str, detail: str, *, actor: str = "ORCHESTRATOR", evidence: list[str] | None = None) -> None:
        assert self.bus and self.state
        event = self.bus.emit(phase, kind, title, detail, actor=actor, evidence=evidence)
        if self._callback:
            self._callback(event, self.state)
        if self._step_delay:
            time.sleep(self._step_delay)

    def _call_tool(self, tool_name: str, *, evidence_key: str | None = None) -> dict[str, Any]:
        assert self.state
        functions: dict[str, ToolFunction] = {
            "NIDS Tool": nids_tool.fetch,
            "Packet Metadata Tool": packet_tool.fetch,
            "Asset Inventory Tool": asset_tool.fetch,
            "Vulnerability Tool": vulnerability_tool.fetch,
            "Server Log Tool": server_log_tool.fetch,
            "Identity Tool": identity_tool.fetch,
        }
        if tool_name == "Service Health Tool":
            result = service_health.check(self.state, self.scenario)
        else:
            function = functions.get(tool_name)
            result = function(self.scenario) if function else {"tool": tool_name, "status": "unavailable", "data": [], "summary": "Tool unavailable; agent will continue with available evidence."}
        key = evidence_key or tool_name
        self.state.evidence[key] = copy.deepcopy(result.get("data", []))
        self.state.investigation_history.append({"tool": tool_name, "status": result.get("status"), "evidence_key": key, "summary": result.get("summary")})
        self.state.tool_calls += 1
        self._emit("INVESTIGATE", "TOOL", tool_name, result.get("summary", "Local tool returned evidence."), actor="INVESTIGATION AGENT")
        self._emit("EVIDENCE", "EVIDENCE", "Evidence captured", f"{key}: {self._compact(result.get('data'))}", actor="LOCAL TOOL LAYER", evidence=[key])
        return result

    @staticmethod
    def _compact(data: Any) -> str:
        text = json.dumps(data, separators=(",", ":"), default=str)
        return text if len(text) <= 260 else text[:257] + "..."

    def _investigate(self, recheck: list[str] | None = None) -> None:
        assert self.state
        if recheck:
            for tool in recheck:
                key = f"{tool} (recheck)"
                self._emit("ADAPT", "DECISION", "Request new evidence", f"The recovery agent selected {tool} because the previous result left a control gap.", actor="RECOVERY AGENT")
                self._call_tool(tool, evidence_key=key)
            self.state.missing_evidence = []
            return
        while True:
            choice = self.investigator.choose_next_tool(self.state.evidence)
            self.state.missing_evidence = self.investigator.missing_evidence(self.state.evidence)
            if choice is None:
                break
            tool, reason = choice
            self._emit("INVESTIGATE", "DECISION", "Select next evidence source", f"{tool}: {reason}", actor="INVESTIGATION AGENT", evidence=[tool])
            self._call_tool(tool)
        self.state.missing_evidence = []

    def _analyze(self, adapted: bool = False) -> dict[str, Any]:
        assert self.state
        result = self.analyzer.analyze(self.state, self.scenario)
        phase = "REPLAN" if adapted else "ANALYZE"
        self._emit(phase, "ANALYSIS", "Attack-chain correlation updated", f"{result['attack_status']} · {result['root_cause']} · risk {result['risk_score']}/100 · confidence {result['confidence']}%", actor="ATTACK ANALYSIS AGENT", evidence=list(self.state.evidence))
        return result

    def _plan(self, override: str = "") -> dict[str, Any]:
        assert self.state
        result = self.planner.plan(self.state, self.scenario, override=override)
        simulation = ", ".join(f"{item['action']} {item['effectiveness']}%" for item in result["simulation"][:4])
        self._emit("DECIDE", "DECISION", "Counterfactual response simulation", f"Candidates: {simulation}. Selected {result['selected_action']} because {result['rationale']}", actor="RESPONSE PLANNER", evidence=["candidate_actions", "root_cause"])
        return result

    def _execute(self, action: str, *, human: bool = False) -> dict[str, Any]:
        assert self.state
        valid = {item["action"] for item in self.state.candidate_actions} | {"BLOCK_IP", "ISOLATE_HOST", "REVOKE_SESSION", "REVOKE_SESSION + BLOCK_IP", "MONITOR"}
        if action not in valid:
            result = {"status": "rejected", "action": action, "reason": "Action validation failed; no sandbox mutation was made."}
        else:
            result = execute_sandbox(self.state, self.scenario, action)
        self.state.response_attempts += 1
        if result.get("status") != "success":
            self.state.failed_actions += 1
        entry = {"iteration": self.state.iteration, "action": action, "status": result.get("status"), "reason": result.get("reason", ""), "human_override": human}
        self.state.action_history.append(entry)
        self.state.action_result = copy.deepcopy(result)
        self._emit("ACTION", "ACTION", "Sandbox response executed", f"{action} · {str(result.get('status', 'unknown')).upper()} · {result.get('reason', '')}", actor="HUMAN OVERRIDE" if human else "SANDBOX SIMULATOR", evidence=["action_result"])
        return result

    def _verify(self) -> list[dict[str, Any]]:
        assert self.state
        checks = self.verifier.verify(self.state, self.scenario)
        passed = sum(1 for item in checks if item["passed"])
        self._emit("VERIFY", "VERIFY", "Independent verification complete", f"{passed}/{len(checks)} checks passed · final status {self.state.final_status}", actor="VERIFICATION AGENT", evidence=[item["check"] for item in checks if item["passed"]])
        return checks

    def _recover(self, failed_result: dict[str, Any]) -> None:
        assert self.state
        self._emit("FAILURE", "RESULT", "Containment result requires adaptation", f"{failed_result.get('status', 'failure').upper()}: {failed_result.get('reason', '')}", actor="SANDBOX SIMULATOR")
        adaptation = self.recovery.adapt(self.state, self.scenario, failed_result)
        self._emit("ADAPT", "ADAPT", "Failure diagnosed; evidence request changed", adaptation["adaptation_reason"], actor="RECOVERY AGENT", evidence=adaptation["requested_evidence"])
        self._investigate(adaptation["requested_evidence"])
        self._analyze(adapted=True)
        self._plan()
        next_result = self._execute(self.state.selected_action)
        if next_result.get("status") != "success":
            self._emit("FAILURE", "RESULT", "Recovery action still needs review", str(next_result.get("reason", "Unknown recovery failure")), actor="SANDBOX SIMULATOR")
        if failed_result.get("status") == "service_failure" or (self.scenario.get("failure") or {}).get("type") == "service_failure":
            from tools.host_simulator import execute as host_execute

            restored = host_execute(self.state, self.scenario, "RESTORE_HOST")
            self.state.action_history.append({"iteration": self.state.iteration, "action": "RESTORE_HOST", "status": restored.get("status"), "reason": restored.get("reason", ""), "human_override": False})
            self._emit("RECOVERY", "ACTION", "Restore dependency health", str(restored.get("reason", "")), actor="RECOVERY AGENT", evidence=["Service Health Tool"])

    def run_demo(self, scenario_id: str = "credential_compromise", *, step_delay: float = 0.0, on_step: Callable[[dict[str, Any], AgentState], None] | None = None) -> AgentState:
        self.reset(scenario_id)
        self._callback = on_step
        assert self.state
        self._emit("GOAL", "GOAL", "Security alert received", f"Investigate {self.state.incident_id}: {self.state.alert.get('signature', 'unknown alert')}", actor="ORCHESTRATOR")
        self._step_delay = max(0.0, step_delay)
        self._investigate()
        self.state.iteration = 1
        self._analyze()
        self._plan()
        first_result = self._execute(self.state.selected_action)
        if first_result.get("status") != "success":
            self._recover(first_result)
        else:
            self._verify()
            if not all(item["passed"] for item in self.state.verification_results):
                failed = {"status": "verification_failure", "reason": "Independent verification found residual activity after the selected action."}
                self._recover(failed)
        self._verify()
        self.state.current_phase = "FINAL"
        self._emit("FINAL", "FINAL", "Incident outcome recorded", f"{self.state.final_status} · risk reduced to {self.state.risk_score}/100 · adaptation {'successful' if self.state.successful_recovery else 'not required'}", actor="ORCHESTRATOR")
        self.state.report_paths = generate_reports(self.state, self.base_dir / "reports")
        self.store.save(self.state)
        return self.state

    def run_with_override(self, action: str, *, scenario_id: str = "credential_compromise", step_delay: float = 0.0, on_step: Callable[[dict[str, Any], AgentState], None] | None = None) -> AgentState:
        self.reset(scenario_id)
        self._callback = on_step
        self._step_delay = max(0.0, step_delay)
        assert self.state
        self.state.human_override = action
        self._emit("GOAL", "GOAL", "Human override mode engaged", f"Analyst selected {action}; evidence gathering remains autonomous.", actor="ORCHESTRATOR")
        self._investigate()
        self.state.iteration = 1
        self._analyze()
        self._plan(override=action)
        first_result = self._execute(action, human=True)
        if first_result.get("status") != "success":
            self._recover(first_result)
        else:
            self._verify()
            if not all(item["passed"] for item in self.state.verification_results):
                failed = {"status": "verification_failure", "reason": "Human-selected response completed, but independent checks found residual activity."}
                self._recover(failed)
        self._verify()
        self.state.current_phase = "FINAL"
        self._emit("FINAL", "FINAL", "Human-guided outcome recorded", f"{self.state.final_status} after human action {action}", actor="ORCHESTRATOR")
        self.state.report_paths = generate_reports(self.state, self.base_dir / "reports")
        self.store.save(self.state)
        return self.state
