"""Interactive official CheerLights color palette bar for Demo preview mode."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button

from ..colors import OFFICIAL_COLORS, ColorEvent, contrasting_text_color


class ColorSelected(Message):
    """Posted when the user clicks a swatch to preview a color in Demo mode."""

    def __init__(self, color_name: str, hex_code: str) -> None:
        super().__init__()
        self.color_name = color_name
        self.hex_code = hex_code


class LiveModeRequested(Message):
    """Posted when the user clicks the LIVE button to return to global sync."""


class ColorPaletteBar(Widget):
    """Horizontal interactive swatch bar for all 11 official CheerLights colors."""

    DEFAULT_CSS = """
    ColorPaletteBar {
        height: 3;
        width: 100%;
        padding: 0 1;
    }
    ColorPaletteBar Horizontal {
        height: 3;
        width: 100%;
        align: center middle;
    }
    ColorPaletteBar Button {
        min-width: 6;
        height: 3;
        margin: 0 0;
        padding: 0 1;
        border: none;
    }
    ColorPaletteBar Button.live-btn {
        min-width: 9;
        margin-right: 1;
        text-style: bold;
    }
    ColorPaletteBar Button.active-swatch {
        text-style: bold underline;
    }
    """

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._active_color: str = ""
        self._demo_mode: bool = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("● LIVE", id="palette-live", classes="live-btn", variant="success")
            for name, hex_code in OFFICIAL_COLORS.items():
                display_hex = ColorEvent(name, hex_code).display_hex
                fg = contrasting_text_color(display_hex)
                btn = Button(
                    name[:3].upper(),
                    id=f"swatch-{name}",
                    tooltip=f"Preview {name.title()} ({hex_code.upper()})",
                )
                btn.styles.background = display_hex
                btn.styles.color = fg
                yield btn

    def set_state(self, active_color: str, *, demo_mode: bool) -> None:
        self._active_color = active_color
        self._demo_mode = demo_mode
        if not self.is_mounted:
            return

        live_btn = self.query_one("#palette-live", Button)
        if demo_mode:
            live_btn.label = "↩ LIVE"
            live_btn.variant = "warning"
        else:
            live_btn.label = "● LIVE"
            live_btn.variant = "success"

        for name in OFFICIAL_COLORS:
            btn = self.query_one(f"#swatch-{name}", Button)
            if name == active_color:
                btn.add_class("active-swatch")
            else:
                btn.remove_class("active-swatch")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "palette-live":
            self.post_message(LiveModeRequested())
        elif button_id.startswith("swatch-"):
            color_name = button_id.removeprefix("swatch-")
            hex_code = OFFICIAL_COLORS.get(color_name, "#ffffff")
            self.post_message(ColorSelected(color_name, hex_code))
