from __future__ import annotations

from typing import Any

from tools.common import ok


def fetch(scenario: dict[str, Any]) -> dict[str, Any]:
    return ok("Asset Inventory Tool", scenario.get("assets", []), "Affected assets mapped to owners and services")
