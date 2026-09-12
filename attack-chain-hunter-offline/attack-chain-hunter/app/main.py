"""Streamlit entry point.

Run from this directory with `streamlit run app/main.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dashboard import render_app


if __name__ == "__main__":
    render_app()
