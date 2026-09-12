from __future__ import annotations

import json
from pathlib import Path

from agents.attack_analysis_agent import AttackAnalysisAgent
from agents.investigation_agent import InvestigationAgent
from agents.response_planner import ResponsePlanner
from engine.orchestrator import AgentController
from engine.reporting import build_report
from engine.state import AgentState


ROOT = Path(__file__).resolve().parents[1]


def controller(tmp_path: Path) -> AgentController:
    return AgentController(base_dir=ROOT, db_path=tmp_path / "soc.db")


def test_alert_ingestion_and_initial_state(tmp_path: Path) -> None:
    agent = controller(tmp_path)
    state = agent.reset("credential_compromise")
    assert state.incident_id == "INC-2026-001"
    assert state.alert["source_ip"] == "185.91.72.14"
    assert state.current_phase == "READY"
    assert state.risk_score == 94


def test_investigation_selects_missing_tools_only() -> None:
    investigator = InvestigationAgent()
    tool, reason = investigator.choose_next_tool({})
    assert tool == "NIDS Tool"
    assert "normalized" in reason
    tool, _ = investigator.choose_next_tool({"NIDS Tool": {}})
    assert tool == "Identity Tool"
    assert "NIDS Tool" not in investigator.missing_evidence({"NIDS Tool": {}})


def test_evidence_retrieval_and_analysis(tmp_path: Path) -> None:
    agent = controller(tmp_path)
    state = agent.run_demo()
    assert {"NIDS Tool", "Identity Tool", "Server Log Tool", "Packet Metadata Tool", "Asset Inventory Tool", "Vulnerability Tool"}.issubset(state.evidence)
    assert state.root_cause.startswith("Compromised privileged session")
    assert state.confidence == 94
    assert state.attack_path[-1]["state"] == "verified"


def test_attack_analysis_risk_and_confidence() -> None:
    scenario = json.loads((ROOT / "data/scenarios/credential_compromise.json").read_text(encoding="utf-8"))
    state = AgentState.from_scenario(scenario)
    state.evidence = {
        "Identity Tool": scenario["identities"],
        "Server Log Tool": scenario["server_logs"],
        "Packet Metadata Tool": scenario["packet_metadata"],
        "Vulnerability Tool": scenario["vulnerabilities"],
        "Asset Inventory Tool": scenario["assets"],
    }
    result = AttackAnalysisAgent().analyze(state, scenario)
    assert result["attack_status"] == "SUCCESSFUL"
    assert state.risk_score == 94
    assert state.confidence == 94


def test_response_planner_counterfactuals(tmp_path: Path) -> None:
    agent = controller(tmp_path)
    state = agent.reset("credential_compromise")
    state.root_cause = "Compromised privileged session"
    state.risk_score = 94
    state.iteration = 1
    result = ResponsePlanner().plan(state, agent.scenario)
    assert len(result["simulation"]) >= 4
    assert result["selected_action"] == "BLOCK_IP"
    state.failure_reason = "active session remains"
    state.iteration = 2
    assert ResponsePlanner().plan(state, agent.scenario)["selected_action"] == "REVOKE_SESSION + BLOCK_IP"


def test_required_failure_adaptation_replan_and_verify(tmp_path: Path) -> None:
    state = controller(tmp_path).run_demo("credential_compromise")
    assert state.action_history[0]["action"] == "BLOCK_IP"
    assert state.action_history[0]["status"] == "partial_failure"
    assert state.action_history[1]["action"] == "REVOKE_SESSION + BLOCK_IP"
    assert state.action_history[1]["status"] == "success"
    assert state.iteration == 2
    assert state.successful_recovery is True
    assert state.final_status == "CONTAINED & VERIFIED"
    assert all(item["passed"] for item in state.verification_results)


def test_all_scenarios_are_offline_and_contained(tmp_path: Path) -> None:
    agent = controller(tmp_path)
    for scenario_id in agent.scenarios:
        state = agent.run_demo(scenario_id)
        assert state.final_status == "CONTAINED & VERIFIED", scenario_id
        assert state.environment["malicious_traffic"] is False
        assert all(not item.get("active_session") for item in state.environment["identities"])
    assert "service_dependency_failure" in agent.scenarios


def test_dependency_failure_restores_service(tmp_path: Path) -> None:
    state = controller(tmp_path).run_demo("service_dependency_failure")
    assert state.action_history[0]["status"] == "service_failure"
    assert any(item["action"] == "RESTORE_HOST" for item in state.action_history)
    assert state.environment["service_health"][0]["dependency_status"] == "healthy"
    assert state.final_status == "CONTAINED & VERIFIED"


def test_human_override_continues_verification_and_recovery(tmp_path: Path) -> None:
    state = controller(tmp_path).run_with_override("ISOLATE_HOST")
    assert state.human_override == "ISOLATE_HOST"
    assert state.action_history[0]["human_override"] is True
    assert state.final_status == "CONTAINED & VERIFIED"
    assert state.successful_recovery is True


def test_state_persistence(tmp_path: Path) -> None:
    agent = controller(tmp_path)
    state = agent.run_demo()
    loaded = agent.store.load(state.incident_id)
    assert loaded is not None
    assert loaded.final_status == state.final_status
    assert len(loaded.timeline) == len(state.timeline)


def test_reports_include_audit_sections(tmp_path: Path) -> None:
    state = controller(tmp_path).run_demo()
    report = build_report(state)
    assert set(["incident_summary", "evidence", "attack_path", "risk", "adaptation", "verification", "timeline"]).issubset(report)
    assert report["risk"]["final"] == 8
    assert state.report_paths["json"].endswith(".json")
    assert state.report_paths["html"].endswith(".html")


def test_invalid_action_is_rejected_without_mutation(tmp_path: Path) -> None:
    agent = controller(tmp_path)
    agent.reset("credential_compromise")
    agent.state.candidate_actions = []
    result = agent._execute("RUN_REAL_FIREWALL")
    assert result["status"] == "rejected"
    assert agent.state.environment["blocked_ips"] == []
