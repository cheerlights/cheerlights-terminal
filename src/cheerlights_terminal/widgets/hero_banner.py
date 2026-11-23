"""Glowing, cross-fading CheerLights ASCII hero banner widget."""

from __future__ import annotations

from rich.align import Align
from rich.console import Group
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from ..ascii_art import render_glowing_ascii
from ..colors import contrasting_text_color, hex_to_rgb, lerp_rgb, rgb_to_hex


class CheerLightsHero(Widget):
    """Animated true-color CheerLights ASCII art with smooth RGB transitions."""

    DEFAULT_CSS = """
    CheerLightsHero {
        height: auto;
        min-height: 16;
        padding: 1 2;
        content-align: center middle;
    }
    """

    color_name: reactive[str] = reactive("cyan")
    hex_code: reactive[str] = reactive("#00ffff")
    display_hex: reactive[str] = reactive("#00ffff")
    status_badge: reactive[str] = reactive("CONNECTING")
    demo_mode: reactive[bool] = reactive(False)

    def __init__(
        self,
        *,
        animate: bool = True,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._start_rgb: tuple[int, int, int] = hex_to_rgb("#00ffff")
        self._target_rgb: tuple[int, int, int] = self._start_rgb
        self._current_rgb: tuple[int, int, int] = self._start_rgb
        self._transition: float = 1.0
        self._flash: float = 0.0
        self._phase: float = 0.0
        self._animate = animate

    def on_mount(self) -> None:
        if self._animate:
            self.set_interval(1 / 16, self._tick)

    def set_color(
        self,
        color_name: str,
        hex_code: str,
        display_hex: str,
        *,
        demo_mode: bool = False,
    ) -> None:
        """Update the hero banner color with a smooth RGB cross-fade."""
        new_rgb = hex_to_rgb(display_hex)
        if new_rgb != self._target_rgb:
            self._start_rgb = self._current_rgb
            self._target_rgb = new_rgb
            self._transition = 0.0
            self._flash = 0.55
        self.color_name = color_name
        self.hex_code = hex_code
        self.display_hex = display_hex
        self.demo_mode = demo_mode
        self.refresh()

    def _tick(self) -> None:
        self._phase += 0.11
        if self._transition < 1.0:
            self._transition = min(1.0, self._transition + 0.08)
            self._current_rgb = lerp_rgb(self._start_rgb, self._target_rgb, self._transition)
        else:
            self._current_rgb = self._target_rgb

        if self._flash > 0.0:
            self._flash = max(0.0, self._flash - 0.06)

        self.refresh()

    def render(self) -> Group:
        art = render_glowing_ascii(
            self._current_rgb,
            phase=self._phase,
            shimmer=self._animate,
            flash=self._flash,
        )

        active_hex = rgb_to_hex(self._current_rgb)
        fg = contrasting_text_color(active_hex)

        pill = Text(justify="center")
        if self.demo_mode:
            pill.append(" ★ DEMO PREVIEW ", style=f"bold {fg} on {active_hex}")
        else:
            pill.append(f" ● {self.status_badge} ", style=f"bold {fg} on {active_hex}")

        pill.append("   ")
        pill.append(self.color_name.upper(), style=f"bold {active_hex}")
        pill.append("  •  ", style="dim")
        pill.append(self.hex_code.upper(), style="bold bright_white")

        return Group(
            Align.center(art),
            Text(""),
            Align.center(pill),
        )
