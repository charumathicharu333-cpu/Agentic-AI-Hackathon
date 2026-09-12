"""Auditable event stream used by every important state transition."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.state import AgentState, StateStore


class EventBus:
    def __init__(self, state: AgentState, store: StateStore | None = None) -> None:
        self.state = state
        self.store = store

    def emit(self, phase: str, kind: str, title: str, detail: str, *, actor: str = "ORCHESTRATOR", evidence: list[str] | None = None) -> dict[str, Any]:
        stamp = datetime.now(timezone.utc)
        event = {
            "timestamp": stamp.isoformat(timespec="seconds"),
            "display_time": stamp.strftime("%H:%M:%S"),
            "phase": phase,
            "kind": kind,
            "title": title,
            "detail": detail,
            "actor": actor,
            "evidence": evidence or [],
        }
        self.state.current_phase = phase
        self.state.timeline.append(event)
        if self.store:
            self.store.save(self.state)
        return event
