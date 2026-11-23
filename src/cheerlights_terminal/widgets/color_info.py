"""Color telemetry inspector card displaying HEX, RGB, HSL, status, and effect."""

from __future__ import annotations

from datetime import datetime

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from ..colors import (
    ColorEvent,
    contrasting_text_color,
    format_relative_time,
)


class ColorInspector(Widget):
    """Displays detailed live telemetry for the active CheerLights color."""

    DEFAULT_CSS = """
    ColorInspector {
        height: auto;
        padding: 1 2;
    }
    """

    color_name: reactive[str] = reactive("cyan")
    hex_code: reactive[str] = reactive("#00ffff")
    display_hex: reactive[str] = reactive("#00ffff")
    transport_status: reactive[str] = reactive("CONNECTING")
    effect_mode: reactive[str] = reactive("breathe")
    demo_mode: reactive[bool] = reactive(False)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._event = ColorEvent("cyan", "#00ffff")
        self._updated_at: datetime | None = None

    def on_mount(self) -> None:
        # Refresh relative timestamps every 10 seconds
        self.set_interval(10.0, self.refresh)

    def update_event(self, event: ColorEvent, *, demo_mode: bool = False) -> None:
        self._event = event
        self._updated_at = event.timestamp
        self.color_name = event.color
        self.hex_code = event.hex_code
        self.display_hex = event.display_hex
        self.demo_mode = demo_mode
        self.refresh()

    def render(self) -> Group:
        event = self._event
        accent = event.display_hex
        fg = contrasting_text_color(accent)
        r, g, b = event.rgb
        h, s, l_val = event.hsl

        width = max(18, (self.size.width or 28) - 4)
        label = f" {event.color.upper()} • {event.hex_code.upper()} "
        swatch = Text(label.center(width), style=f"bold {fg} on {accent}")

        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(style="dim", ratio=2)
        grid.add_column(style="bold bright_white", ratio=3, justify="right")

        grid.add_row("HEX", Text(event.hex_code.upper(), style=f"bold {accent}"))
        grid.add_row("RGB", f"{r}, {g}, {b}")
        grid.add_row("HSL", f"{h}°, {s}%, {l_val}%")
        grid.add_row("Updated", format_relative_time(self._updated_at))
        grid.add_row("LED Effect", Text(self.effect_mode.upper(), style=f"bold {accent}"))

        if self.demo_mode:
            source_text = Text("★ DEMO (local)", style="bold bright_yellow")
        elif self.transport_status == "MQTT LIVE":
            source_text = Text("● MQTT LIVE", style="bold #22c55e")
        elif self.transport_status == "HTTP POLL":
            source_text = Text("◐ HTTP POLL", style="bold #38bdf8")
        else:
            source_text = Text(f"○ {self.transport_status}", style="dim")
        grid.add_row("Feed", source_text)

        hint = Text.assemble(
            ("[c]", f"bold {accent}"),
            (" copy hex  ", "dim"),
            ("[e]", f"bold {accent}"),
            (" effect  ", "dim"),
            ("[z]", f"bold {accent}"),
            (" zen", "dim"),
        )

        return Group(swatch, Text(""), grid, Text(""), hint)
