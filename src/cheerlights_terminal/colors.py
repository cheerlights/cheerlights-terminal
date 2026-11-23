"""Color utilities, official CheerLights palette, and smooth RGB interpolation."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from datetime import UTC, datetime

import cheerlights_api

# Display order for the palette bar, sourced from cheerlights_api.COLORS
_DISPLAY_ORDER: tuple[str, ...] = (
    "red",
    "orange",
    "yellow",
    "green",
    "cyan",
    "blue",
    "purple",
    "magenta",
    "pink",
    "oldlace",
    "white",
)

OFFICIAL_COLORS: dict[str, str] = {
    name: cheerlights_api.COLORS[name] for name in _DISPLAY_ORDER if name in cheerlights_api.COLORS
} | {
    name: hex_val for name, hex_val in cheerlights_api.COLORS.items() if name not in _DISPLAY_ORDER
}

COLOR_NAMES: tuple[str, ...] = tuple(OFFICIAL_COLORS.keys())

ALIASES: dict[str, str] = dict(cheerlights_api.ALIASES)

# Reverse lookup for matching hex codes back to canonical names
_HEX_TO_NAME: dict[str, str] = {hex_val.lower(): name for name, hex_val in OFFICIAL_COLORS.items()}

# Some CheerLights colors (like pure green #008000 or purple #800080) look richer in
# dark terminals when given a slightly brighter display accent for thin borders/glows.
DISPLAY_BOOST: dict[str, str] = {
    "green": "#22c55e",
    "blue": "#3b82f6",
    "purple": "#a855f7",
}


@dataclass(frozen=True, slots=True)
class ColorEvent:
    """A single CheerLights color state or historical change."""

    color: str
    hex_code: str
    timestamp: datetime | None = None
    source: str = "live"

    @property
    def rgb(self) -> tuple[int, int, int]:
        return hex_to_rgb(self.hex_code)

    @property
    def hsl(self) -> tuple[int, int, int]:
        return rgb_to_hsl(self.rgb)

    @property
    def display_hex(self) -> str:
        """A brighter hex value for dark-terminal borders and accents."""
        return DISPLAY_BOOST.get(self.color, self.hex_code)


def normalize_color(
    color_name: str | None = None,
    hex_code: str | None = None,
) -> tuple[str, str]:
    """Normalize a color name and/or hex code into a valid (name, '#rrggbb') pair."""
    raw_name = (color_name or "").strip()
    key = raw_name.lower().replace(" ", "")
    canonical = ALIASES.get(key, key)

    clean_hex = ""
    if hex_code:
        candidate = hex_code.strip().lower()
        if not candidate.startswith("#"):
            candidate = f"#{candidate}"
        try:
            cheerlights_api.hex_to_rgb(candidate)
            clean_hex = candidate
        except ValueError:
            clean_hex = ""

    if raw_name and cheerlights_api.is_valid_color(raw_name):
        resolved_hex = clean_hex or cheerlights_api.color_name_to_hex(raw_name) or "#ffffff"
        return canonical, resolved_hex

    if clean_hex:
        resolved_name = _HEX_TO_NAME.get(clean_hex, canonical or "custom")
        return resolved_name, clean_hex

    return "white", cheerlights_api.COLORS["white"]


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' (or 'rrggbb') to an (r, g, b) tuple."""
    try:
        return cheerlights_api.hex_to_rgb(hex_code)
    except ValueError:
        return (255, 255, 255)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert an (r, g, b) tuple to '#rrggbb'."""
    r = max(0, min(255, int(round(rgb[0]))))
    g = max(0, min(255, int(round(rgb[1]))))
    b = max(0, min(255, int(round(rgb[2]))))
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_hsl(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Convert (r, g, b) 0..255 to (hue 0..360, sat 0..100, light 0..100)."""
    r, g, b = (channel / 255.0 for channel in rgb)
    h, l_val, s = colorsys.rgb_to_hls(r, g, b)
    return int(round(h * 360)) % 360, int(round(s * 100)), int(round(l_val * 100))


def lerp_rgb(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linearly interpolate between two RGB colors for t in [0.0, 1.0]."""
    clamped = max(0.0, min(1.0, t))
    return (
        int(round(start[0] + (end[0] - start[0]) * clamped)),
        int(round(start[1] + (end[1] - start[1]) * clamped)),
        int(round(start[2] + (end[2] - start[2]) * clamped)),
    )


def shade_rgb(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Darken an RGB color toward black by `amount` (0.0 = unchanged, 1.0 = black)."""
    return lerp_rgb(rgb, (0, 0, 0), amount)


def tint_rgb(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Lighten an RGB color toward white by `amount` (0.0 = unchanged, 1.0 = white)."""
    return lerp_rgb(rgb, (255, 255, 255), amount)


def scale_brightness(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Scale brightness: <1.0 darkens toward black, >1.0 glows toward white."""
    if factor <= 1.0:
        return shade_rgb(rgb, 1.0 - max(0.0, factor))
    return tint_rgb(rgb, min(1.0, (factor - 1.0) * 0.6))


def relative_luminance(hex_code: str) -> float:
    """Compute WCAG 2.1 relative luminance in [0.0, 1.0]."""
    r, g, b = hex_to_rgb(hex_code)

    def _linear(channel: int) -> float:
        srgb = channel / 255.0
        return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrasting_text_color(hex_code: str) -> str:
    """Return dark or light foreground hex for readable contrast over `hex_code`."""
    return "#0b0e14" if relative_luminance(hex_code) > 0.42 else "#f8fafc"


def build_gradient_stops(hex_code: str) -> tuple[str, str, str]:
    """Return a 3-stop (deep, base, bright) hex tuple without '#' for effects/gradients."""
    rgb = hex_to_rgb(hex_code)
    deep = rgb_to_hex(shade_rgb(rgb, 0.35)).lstrip("#")
    base = rgb_to_hex(rgb).lstrip("#")
    bright = rgb_to_hex(tint_rgb(rgb, 0.55)).lstrip("#")
    return (deep, base, bright)


def format_relative_time(
    timestamp: datetime | None,
    now: datetime | None = None,
) -> str:
    """Format a UTC timestamp as a concise relative duration ('just now', '5m ago')."""
    if timestamp is None:
        return "live"
    current = now or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    seconds = max(0, int((current - timestamp).total_seconds()))
    if seconds < 10:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"
