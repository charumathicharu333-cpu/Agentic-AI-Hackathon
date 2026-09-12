from __future__ import annotations

from typing import Any

from tools.common import ok


def fetch(scenario: dict[str, Any]) -> dict[str, Any]:
    return ok("Server Log Tool", scenario.get("server_logs", []), "Application events correlated")
