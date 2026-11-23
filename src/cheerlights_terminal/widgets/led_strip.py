"""Animated virtual NeoPixel LED strip widget with smooth color cross-fades."""

from __future__ import annotations

import colorsys
import math

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from ..colors import hex_to_rgb, lerp_rgb, rgb_to_hex, scale_brightness, tint_rgb

LED_EFFECTS: tuple[str, ...] = (
    "breathe",
    "chase",
    "twinkle",
    "wave",
    "rainbow",
    "solid",
)


class VirtualLEDStrip(Widget):
    """A string of virtual RGB LEDs that smoothly cross-fade and animate."""

    DEFAULT_CSS = """
    VirtualLEDStrip {
        height: 1;
        width: 100%;
        content-align: center middle;
    }
    """

    target_hex: reactive[str] = reactive("#00ffff")
    effect_mode: reactive[str] = reactive("breathe")

    def __init__(
        self,
        initial_hex: str = "#00ffff",
        effect_mode: str = "breathe",
        *,
        animate: bool = True,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._start_rgb: tuple[int, int, int] = hex_to_rgb(initial_hex)
        self._target_rgb: tuple[int, int, int] = self._start_rgb
        self._current_rgb: tuple[int, int, int] = self._start_rgb
        self._transition: float = 1.0
        self._ripple: float = 0.0
        self._phase: float = 0.0
        self._animate = animate
        self.target_hex = initial_hex
        self.effect_mode = effect_mode if effect_mode in LED_EFFECTS else "breathe"

    def on_mount(self) -> None:
        if self._animate:
            self.set_interval(1 / 18, self._tick)

    def watch_target_hex(self, new_hex: str) -> None:
        new_rgb = hex_to_rgb(new_hex)
        if new_rgb != self._target_rgb:
            self._start_rgb = self._current_rgb
            self._target_rgb = new_rgb
            self._transition = 0.0
            self._ripple = 1.0
            self.refresh()

    def watch_effect_mode(self, _mode: str) -> None:
        self.refresh()

    def trigger_ripple(self) -> None:
        """Trigger an outward light ripple across the LEDs."""
        self._ripple = 1.0
        self.refresh()

    def _tick(self) -> None:
        self._phase += 0.14
        if self._transition < 1.0:
            self._transition = min(1.0, self._transition + 0.07)
            self._current_rgb = lerp_rgb(self._start_rgb, self._target_rgb, self._transition)
        else:
            self._current_rgb = self._target_rgb

        if self._ripple > 0.0:
            self._ripple = max(0.0, self._ripple - 0.045)

        self.refresh()

    def _led_color(self, idx: int, count: int) -> tuple[str, str]:
        """Compute (glyph, hex_color) for LED `idx` out of `count`."""
        mode = self.effect_mode
        rgb = self._current_rgb
        norm = idx / max(1, count - 1)

        if mode == "breathe":
            pulse = 0.55 + 0.60 * (0.5 + 0.5 * math.sin(self._phase * 0.9))
            bulb_rgb = scale_brightness(rgb, pulse)
            glyph = "◉" if pulse > 0.92 else "●"
        elif mode == "chase":
            head = (self._phase * 2.2) % count
            dist = min(abs(idx - head), count - abs(idx - head))
            intensity = max(0.22, 1.35 - dist * 0.28)
            bulb_rgb = scale_brightness(rgb, intensity)
            glyph = "✦" if dist < 0.8 else ("◉" if dist < 2.2 else "●")
        elif mode == "twinkle":
            # Deterministic pseudo-random shimmer per bulb
            sparkle = math.sin(self._phase * (1.3 + (idx % 5) * 0.27) + idx * 2.13)
            intensity = 0.40 + 0.95 * max(0.0, sparkle)
            bulb_rgb = scale_brightness(rgb, intensity)
            glyph = "✦" if sparkle > 0.82 else ("◉" if sparkle > 0.3 else "·")
        elif mode == "wave":
            wave = 0.5 + 0.5 * math.sin(self._phase * 1.4 - norm * math.tau * 1.5)
            intensity = 0.35 + 0.95 * wave
            bulb_rgb = scale_brightness(rgb, intensity)
            glyph = "◉" if wave > 0.72 else "●"
        elif mode == "rainbow":
            hue = (norm + self._phase * 0.04) % 1.0
            r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, 0.92, 1.0)
            rainbow_rgb = (int(r_f * 255), int(g_f * 255), int(b_f * 255))
            # Gently blend with the active CheerLights color so it stays connected
            bulb_rgb = lerp_rgb(rainbow_rgb, rgb, 0.22)
            glyph = "◉" if (idx + int(self._phase * 2)) % 4 == 0 else "●"
        else:  # solid
            bulb_rgb = rgb
            glyph = "●"

        # Overlay outward ripple when a color transition occurs
        if self._ripple > 0.01:
            center_dist = abs(norm - 0.5) * 2.0
            wave_front = 1.0 - self._ripple
            band = max(0.0, 1.0 - abs(center_dist - wave_front) * 4.5)
            if band > 0.05:
                bulb_rgb = tint_rgb(bulb_rgb, band * 0.85)
                if band > 0.55:
                    glyph = "✦"

        return glyph, rgb_to_hex(bulb_rgb)

    def render(self) -> Text:
        width = max(12, self.size.width or 48)
        count = max(5, (width - 2) // 3)
        wire_hex = rgb_to_hex(scale_brightness(self._current_rgb, 0.28))

        line = Text(no_wrap=True, justify="center")
        for idx in range(count):
            if idx > 0:
                line.append("──", style=wire_hex)
            glyph, bulb_hex = self._led_color(idx, count)
            line.append(glyph, style=f"bold {bulb_hex}")
        return line
