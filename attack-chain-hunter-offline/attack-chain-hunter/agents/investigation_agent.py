"""Evidence-driven tool selection; it deliberately avoids calling every tool at once."""
from __future__ import annotations

from typing import Any


class InvestigationAgent:
    TOOL_ORDER = [
        ("NIDS Tool", "The alert must be normalized before correlation."),
        ("Identity Tool", "Authentication risk requires session, privilege, and MFA evidence."),
        ("Server Log Tool", "Authentication evidence needs a timeline of successful actions."),
        ("Packet Metadata Tool", "Traffic volume and anomaly score distinguish probing from impact."),
        ("Asset Inventory Tool", "The affected service and criticality are needed to size blast radius."),
        ("Vulnerability Tool", "Exposure evidence links the observed behavior to a plausible root cause."),
    ]

    def choose_next_tool(self, evidence: dict[str, Any]) -> tuple[str, str] | None:
        for tool, reason in self.TOOL_ORDER:
            if tool not in evidence:
                return tool, reason
        return None

    def missing_evidence(self, evidence: dict[str, Any]) -> list[str]:
        return [tool for tool, _ in self.TOOL_ORDER if tool not in evidence]
