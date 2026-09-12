from __future__ import annotations

from typing import Any

from engine.state import AgentState
from tools.common import ok


def check(state: AgentState, scenario: dict[str, Any]) -> dict[str, Any]:
    return ok("Service Health Tool", state.environment.get("service_health", scenario.get("service_health", [])), "Required service dependencies checked")
