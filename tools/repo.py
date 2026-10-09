"""Resolve the repository root independently of the current directory."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
