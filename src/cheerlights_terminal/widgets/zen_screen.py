"""Full-screen Zen / Ambient Lamp mode screen."""

from __future__ import annotations

import math

from rich.align import Align
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget

from ..ascii_art import render_glowing_ascii
from ..colors import (
    ColorEvent,
    contrasting_text_color,
    hex_to_rgb,
    lerp_rgb,
    rgb_to_hex,
    scale_brightness,
    shade_rgb,
)
from .led_strip import VirtualLEDStrip


class AmbientLampCanvas(Widget):
    """Fills the terminal with a smooth, breathing CheerLights ambient glow."""

    DEFAULT_CSS = """
    AmbientLampCanvas {
        width: 100%;
        height: 1fr;
    }
    """

    show_logo: reactive[bool] = reactive(True)

    def __init__(
        self,
        event: ColorEvent,
        *,
        animate: bool = True,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._event = event
        self._start_rgb = hex_to_rgb(event.display_hex)
        self._target_rgb = self._start_rgb
        self._current_rgb = self._start_rgb
        self._transition = 1.0
        self._phase = 0.0
        self._animate = animate

    def on_mount(self) -> None:
        if self._animate:
            self.set_interval(1 / 14, self._tick)

    def set_event(self, event: ColorEvent) -> None:
        self._event = event
        new_rgb = hex_to_rgb(event.display_hex)
        if new_rgb != self._target_rgb:
            self._start_rgb = self._current_rgb
            self._target_rgb = new_rgb
            self._transition = 0.0
        self.refresh()

    def _tick(self) -> None:
        self._phase += 0.10
        if self._transition < 1.0:
            self._transition = min(1.0, self._transition + 0.06)
            self._current_rgb = lerp_rgb(self._start_rgb, self._target_rgb, self._transition)
        else:
            self._current_rgb = self._target_rgb
        self.refresh()

    def render(self) -> Align:
        width = max(30, self.size.width or 80)
        height = max(12, self.size.height or 24)

        breathe = 0.72 + 0.28 * math.sin(self._phase * 0.7)
        glow_rgb = scale_brightness(self._current_rgb, breathe)
        bg_rgb = shade_rgb(glow_rgb, 0.78)
        bg_hex = rgb_to_hex(bg_rgb)
        self.styles.background = bg_hex

        if self.show_logo:
            art = render_glowing_ascii(
                glow_rgb,
                phase=self._phase,
                shimmer=self._animate,
            )
            accent_hex = rgb_to_hex(glow_rgb)
            fg = contrasting_text_color(accent_hex)
            caption = Text(justify="center")
            caption.append(
                f"  ✦ {self._event.color.upper()} • {self._event.hex_code.upper()} ✦  ",
                style=f"bold {fg} on {accent_hex}",
            )
            block = Text()
            block.append_text(art)
            block.append("\n\n")
            block.append_text(caption)
            return Align.center(block, vertical="middle", height=height)

        # Pure ambient gradient bands when logo is hidden
        canvas = Text(no_wrap=True)
        for row in range(height):
            dist_from_center = abs((row / max(1, height - 1)) - 0.5) * 2.0
            row_factor = max(0.18, (1.0 - dist_from_center * 0.65) * (0.85 + 0.20 * breathe))
            band_hex = rgb_to_hex(scale_brightness(self._current_rgb, row_factor))
            canvas.append(" " * width, style=f"on {band_hex}")
            if row < height - 1:
                canvas.append("\n")
        return Align.center(canvas, vertical="middle")


class ZenHintBar(Widget):
    """Minimal whisper bar at the bottom of Zen mode."""

    DEFAULT_CSS = """
    ZenHintBar {
        height: 1;
        width: 100%;
        content-align: center middle;
        background: #0b0e14;
    }
    """

    def render(self) -> Text:
        return Text(
            "ZEN LAMP MODE  •  [z / esc] exit  •  [a] logo  •  [e] LED effect",
            style="dim",
            justify="center",
        )


class ZenLampScreen(Screen[None]):
    """Full-screen ambient CheerLights desk lamp."""

    BINDINGS = [
        Binding("z", "exit_zen", "Exit Zen", show=False),
        Binding("escape", "exit_zen", "Exit Zen", show=False),
        Binding("a", "toggle_logo", "Toggle Logo", show=False),
        Binding("e", "cycle_effect", "Cycle LED Effect", show=False),
    ]

    DEFAULT_CSS = """
    ZenLampScreen {
        layout: vertical;
        background: #0b0e14;
    }
    """

    def __init__(
        self,
        event: ColorEvent,
        effect_mode: str = "breathe",
        *,
        animate: bool = True,
    ) -> None:
        super().__init__()
        self._event = event
        self._effect_mode = effect_mode
        self._animate = animate

    def compose(self) -> ComposeResult:
        yield VirtualLEDStrip(
            initial_hex=self._event.display_hex,
            effect_mode=self._effect_mode,
            animate=self._animate,
            id="zen-led-top",
        )
        yield AmbientLampCanvas(self._event, animate=self._animate, id="zen-canvas")
        yield VirtualLEDStrip(
            initial_hex=self._event.display_hex,
            effect_mode=self._effect_mode,
            animate=self._animate,
            id="zen-led-bottom",
        )
        yield ZenHintBar()

    def update_live_color(self, event: ColorEvent) -> None:
        self._event = event
        if not self.is_mounted:
            return
        self.query_one("#zen-canvas", AmbientLampCanvas).set_event(event)
        self.query_one("#zen-led-top", VirtualLEDStrip).target_hex = event.display_hex
        self.query_one("#zen-led-bottom", VirtualLEDStrip).target_hex = event.display_hex

    def update_effect(self, effect_mode: str) -> None:
        self._effect_mode = effect_mode
        if not self.is_mounted:
            return
        self.query_one("#zen-led-top", VirtualLEDStrip).effect_mode = effect_mode
        self.query_one("#zen-led-bottom", VirtualLEDStrip).effect_mode = effect_mode

    def action_exit_zen(self) -> None:
        self.dismiss(None)

    def action_toggle_logo(self) -> None:
        canvas = self.query_one("#zen-canvas", AmbientLampCanvas)
        canvas.show_logo = not canvas.show_logo

    def action_cycle_effect(self) -> None:
        if hasattr(self.app, "action_cycle_effect"):
            self.app.action_cycle_effect()  # type: ignore[attr-defined]
