from __future__ import annotations

from typing import Any

from tools.common import ok


def fetch(scenario: dict[str, Any]) -> dict[str, Any]:
    return ok("Packet Metadata Tool", scenario.get("packet_metadata", {}), "Traffic volume and anomaly metadata retrieved")
