"""Persistent incident state for the local SOC simulation."""
from __future__ import annotations

import copy
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class AgentState:
    incident_id: str
    current_phase: str = "READY"
    alert: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    missing_evidence: list[str] = field(default_factory=list)
    investigation_history: list[dict[str, Any]] = field(default_factory=list)
    attack_path: list[dict[str, Any]] = field(default_factory=list)
    root_cause: str = "Pending evidence"
    risk_score: int = 0
    initial_risk_score: int = 0
    confidence: int = 0
    candidate_actions: list[dict[str, Any]] = field(default_factory=list)
    selected_action: str = ""
    action_history: list[dict[str, Any]] = field(default_factory=list)
    action_result: dict[str, Any] = field(default_factory=dict)
    failure_reason: str = ""
    adaptation_reason: str = ""
    iteration: int = 0
    human_override: str = ""
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    final_status: str = "NOT STARTED"
    timeline: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    response_attempts: int = 0
    failed_actions: int = 0
    successful_recovery: bool = False
    environment: dict[str, Any] = field(default_factory=dict)
    scenario_id: str = ""
    scenario_name: str = ""
    report_paths: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_scenario(cls, scenario: dict[str, Any]) -> "AgentState":
        alert = copy.deepcopy(scenario.get("alert", {}))
        severity_risk = {"LOW": 28, "MEDIUM": 52, "HIGH": 78, "CRITICAL": 94}
        initial = severity_risk.get(str(alert.get("severity", "MEDIUM")).upper(), 52)
        environment = {
            "blocked_ips": list(scenario.get("network_state", {}).get("blocked_ips", [])),
            "suspicious_ips": list(scenario.get("network_state", {}).get("suspicious_ips", [])),
            "malicious_traffic": bool(scenario.get("network_state", {}).get("malicious_traffic", True)),
            "identities": copy.deepcopy(scenario.get("identities", [])),
            "isolated_hosts": [],
            "service_health": copy.deepcopy(scenario.get("service_health", [])),
        }
        return cls(
            incident_id=str(scenario.get("incident_id", "INC-LOCAL")),
            alert=alert,
            attack_path=copy.deepcopy(scenario.get("attack_path", [])),
            risk_score=initial,
            initial_risk_score=initial,
            scenario_id=str(scenario.get("id", "unknown")),
            scenario_name=str(scenario.get("name", "Local scenario")),
            environment=environment,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentState":
        fields = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in fields})

    @property
    def evidence_sources(self) -> int:
        return len(self.evidence)

    @property
    def risk_reduction(self) -> float:
        if not self.initial_risk_score:
            return 0.0
        return round((self.initial_risk_score - self.risk_score) / self.initial_risk_score * 100, 1)


class StateStore:
    """Small SQLite snapshot store; no external database is used."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path(__file__).resolve().parents[1] / "database" / "soc.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_only = False
        self._memory: dict[str, str] = {}
        try:
            with sqlite3.connect(self.path, timeout=2.0) as db:
                db.execute("pragma busy_timeout=2000")
                db.execute("create table if not exists incident_state (incident_id text primary key, payload text not null, updated_at text not null)")
        except sqlite3.OperationalError:
            self.memory_only = True

    def save(self, state: AgentState) -> None:
        payload = json.dumps(state.to_dict())
        if self.memory_only:
            self._memory[state.incident_id] = payload
            return
        try:
            with sqlite3.connect(self.path, timeout=2.0) as db:
                db.execute("pragma busy_timeout=2000")
                db.execute(
                    "insert into incident_state(incident_id,payload,updated_at) values(?,?,?) on conflict(incident_id) do update set payload=excluded.payload, updated_at=excluded.updated_at",
                    (state.incident_id, payload, utc_now()),
                )
        except sqlite3.OperationalError:
            self.memory_only = True
            self._memory[state.incident_id] = payload

    def load(self, incident_id: str) -> AgentState | None:
        if self.memory_only:
            payload = self._memory.get(incident_id)
            return AgentState.from_dict(json.loads(payload)) if payload else None
        try:
            with sqlite3.connect(self.path, timeout=2.0) as db:
                db.execute("pragma busy_timeout=2000")
                row = db.execute("select payload from incident_state where incident_id=?", (incident_id,)).fetchone()
            return AgentState.from_dict(json.loads(row[0])) if row else None
        except sqlite3.OperationalError:
            self.memory_only = True
            payload = self._memory.get(incident_id)
            return AgentState.from_dict(json.loads(payload)) if payload else None
