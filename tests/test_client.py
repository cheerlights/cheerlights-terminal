"""Unit tests for the async CheerLights API client and TTE intro builder."""

from __future__ import annotations

from datetime import UTC
from io import StringIO
from unittest.mock import patch

from rich.console import Console

from cheerlights_terminal.client import (
    decode_mqtt_payload,
    fetch_color_history,
    fetch_current_color,
    parse_timestamp,
)
from cheerlights_terminal.colors import ColorEvent
from cheerlights_terminal.intro import create_tte_effect, display_once


def test_parse_timestamp() -> None:
    dt = parse_timestamp("2026-11-22T15:30:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.tzinfo == UTC
    assert parse_timestamp("not-a-date") is None
    assert parse_timestamp(None) is None


async def test_fetch_current_color_mocked() -> None:
    with patch(
        "cheerlights_terminal.client.cheerlights_api.get_current_color",
        return_value={"color": "magenta", "hex": "#ff00ff"},
    ):
        event = await fetch_current_color()
    assert event.color == "magenta"
    assert event.hex_code == "#ff00ff"
    assert event.source == "api"


async def test_fetch_color_history_reversed_newest_first() -> None:
    fake_entries = [
        {"color": "red", "hex": "#ff0000", "timestamp": "2026-11-22T10:00:00Z"},
        {"color": "cyan", "hex": "#00ffff", "timestamp": "2026-11-22T10:05:00Z"},
    ]
    with patch(
        "cheerlights_terminal.client.cheerlights_api.get_color_history",
        return_value=fake_entries,
    ):
        events = await fetch_color_history(2)

    assert len(events) == 2
    assert events[0].color == "cyan"
    assert events[1].color == "red"
    assert events[0].timestamp is not None


def test_decode_mqtt_payload() -> None:
    ev_name = decode_mqtt_payload("cheerlights", b"purple")
    assert ev_name is not None
    assert ev_name.color == "purple"
    assert ev_name.hex_code == "#800080"
    assert ev_name.source == "mqtt"

    ev_hex = decode_mqtt_payload("cheerlightsRGB", b"#00FFFF")
    assert ev_hex is not None
    assert ev_hex.color == "cyan"
    assert ev_hex.hex_code == "#00ffff"

    assert decode_mqtt_payload("cheerlights", b"   ") is None


def test_tte_effect_factory_and_display_once() -> None:
    effect = create_tte_effect("CHEERLIGHTS", "#00ffff", effect_name="beams", fast=True)
    assert hasattr(effect, "terminal_output")

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, color_system="truecolor", width=100)
    ev = ColorEvent("cyan", "#00ffff")
    display_once(ev, history=[ev], effect_name="none", console=console)
    output = buf.getvalue()
    assert "CYAN" in output
    assert "#00FFFF" in output
    assert "cheerlights.com/discord" in output
