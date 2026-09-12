"""Shared result shape for synthetic local tools."""
from __future__ import annotations

from typing import Any


def ok(tool: str, data: Any, summary: str = "Evidence retrieved") -> dict[str, Any]:
    return {"tool": tool, "status": "ok", "data": data, "summary": summary}


def unavailable(tool: str, reason: str) -> dict[str, Any]:
    return {"tool": tool, "status": "unavailable", "data": [], "summary": reason}
