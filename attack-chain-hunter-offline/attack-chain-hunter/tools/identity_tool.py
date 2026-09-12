from __future__ import annotations

from typing import Any

from tools.common import ok


def fetch(scenario: dict[str, Any]) -> dict[str, Any]:
    return ok("Identity Tool", scenario.get("identities", []), "Identity and session state retrieved")
