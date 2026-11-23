"""Unit tests for CheerLights color palette, interpolation, and time formatting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cheerlights_terminal.colors import (
    OFFICIAL_COLORS,
    ColorEvent,
    build_gradient_stops,
    contrasting_text_color,
    format_relative_time,
    hex_to_rgb,
    lerp_rgb,
    normalize_color,
    rgb_to_hex,
    rgb_to_hsl,
    scale_brightness,
)


def test_official_colors_count_and_normalization() -> None:
    assert len(OFFICIAL_COLORS) == 11
    assert normalize_color("RED") == ("red", "#ff0000")
    assert normalize_color("Warm White") == ("oldlace", "#fdf5e6")
    assert normalize_color("warmwhite") == ("oldlace", "#fdf5e6")
    assert normalize_color(hex_code="#00FFFF") == ("cyan", "#00ffff")
    assert normalize_color(hex_code="ffa500") == ("orange", "#ffa500")
    assert normalize_color("unknown", "#123456") == ("unknown", "#123456")
    assert normalize_color("invalid", "not-hex") == ("white", "#ffffff")


def test_rgb_hsl_and_interpolation() -> None:
    assert hex_to_rgb("#ff0000") == (255, 0, 0)
    assert rgb_to_hex((0, 255, 128)) == "#00ff80"
    assert rgb_to_hsl((0, 255, 255)) == (180, 100, 50)
    assert lerp_rgb((0, 0, 0), (100, 200, 50), 0.5) == (50, 100, 25)
    assert lerp_rgb((10, 20, 30), (100, 200, 250), 0.0) == (10, 20, 30)
    assert lerp_rgb((10, 20, 30), (100, 200, 250), 1.0) == (100, 200, 250)


def test_brightness_contrast_and_gradient_stops() -> None:
    assert contrasting_text_color("#ffff00") == "#0b0e14"
    assert contrasting_text_color("#0000ff") == "#f8fafc"
    assert scale_brightness((100, 100, 100), 0.5) == (50, 50, 50)
    deep, base, bright = build_gradient_stops("#00ffff")
    assert len(deep) == 6 and len(base) == 6 and len(bright) == 6
    assert base == "00ffff"


def test_color_event_properties_and_relative_time() -> None:
    now = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)
    ev = ColorEvent("blue", "#0000ff", timestamp=now)
    assert ev.rgb == (0, 0, 255)
    assert ev.hsl == (240, 100, 50)
    assert ev.display_hex == "#3b82f6"

    assert format_relative_time(None, now=now) == "live"
    assert format_relative_time(now - timedelta(seconds=3), now=now) == "just now"
    assert format_relative_time(now - timedelta(seconds=42), now=now) == "42s ago"
    assert format_relative_time(now - timedelta(minutes=7), now=now) == "7m ago"
    assert format_relative_time(now - timedelta(hours=3), now=now) == "3h ago"
    assert format_relative_time(now - timedelta(days=2), now=now) == "2d ago"
