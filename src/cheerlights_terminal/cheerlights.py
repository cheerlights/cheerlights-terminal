"""Synchronous CheerLights helper wrappers (compatible with cheerlights-api 0.2.0)."""

from __future__ import annotations

import sys

import cheerlights_api

from .colors import normalize_color


def get_current_color() -> tuple[str, str]:
    """Fetch the current CheerLights (color_name, hex_code) pair."""
    try:
        color_data = cheerlights_api.get_current_color()
        return normalize_color(color_data.get("color"), color_data.get("hex"))
    except Exception as exc:
        print(f"Error fetching CheerLights color: {exc}", file=sys.stderr)
        return "white", "#ffffff"


def get_current_color_name() -> str:
    """Fetch just the current CheerLights color name."""
    name, _ = get_current_color()
    return name


def get_current_hex() -> str:
    """Fetch just the current CheerLights hex color."""
    _, hex_code = get_current_color()
    return hex_code


def get_color_history(count: int = 20) -> list[dict[str, str]]:
    """Fetch recent CheerLights color history entries."""
    try:
        return list(cheerlights_api.get_color_history(count))
    except Exception as exc:
        print(f"Error fetching CheerLights history: {exc}", file=sys.stderr)
        return []
