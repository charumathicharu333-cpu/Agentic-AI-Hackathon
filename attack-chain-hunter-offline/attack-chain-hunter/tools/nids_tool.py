from __future__ import annotations

from typing import Any

from tools.common import ok


def fetch(scenario: dict[str, Any]) -> dict[str, Any]:
    return ok("NIDS Tool", scenario.get("alert", {}), "Synthetic NIDS alert confirmed")
