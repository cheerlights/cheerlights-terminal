"""Color history timeline tape and community color statistics chart widgets."""

from __future__ import annotations

from collections import Counter

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.widget import Widget

from ..colors import OFFICIAL_COLORS, ColorEvent, format_relative_time


class ColorHistoryPanel(Widget):
    """Displays a chromatic recent-color tape and timestamped transition timeline."""

    DEFAULT_CSS = """
    ColorHistoryPanel {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._history: list[ColorEvent] = []

    def on_mount(self) -> None:
        self.set_interval(15.0, self.refresh)

    def set_history(self, events: list[ColorEvent]) -> None:
        self._history = list(events)
        self.refresh()

    def prepend_event(self, event: ColorEvent) -> None:
        """Insert a brand-new live color event at the front of the timeline."""
        if (
            self._history
            and self._history[0].color == event.color
            and self._history[0].hex_code == event.hex_code
        ):
            return
        self._history.insert(0, event)
        self._history = self._history[:100]
        self.refresh()

    def render(self) -> Group:
        if not self._history:
            return Group(Text("Loading global color history...", style="dim italic"))

        width = max(20, (self.size.width or 42) - 4)
        tape_slots = max(8, width // 2)

        shown = min(len(self._history), tape_slots)
        tape_label = Text(f"Recent Ribbon ({shown} changes)", style="dim")
        tape = Text(no_wrap=True)
        for item in self._history[:tape_slots]:
            tape.append("██", style=item.display_hex)

        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(width=2)
        table.add_column(ratio=2)
        table.add_column(ratio=2, style="dim")
        table.add_column(ratio=2, justify="right", style="dim")

        max_rows = max(5, min(14, (self.size.height or 12) - 4))
        for idx, item in enumerate(self._history[:max_rows]):
            dot = Text("●", style=f"bold {item.display_hex}")
            name_style = f"bold {item.display_hex}" if idx == 0 else "bright_white"
            name = Text(item.color.upper(), style=name_style)
            table.add_row(
                dot,
                name,
                item.hex_code.upper(),
                format_relative_time(item.timestamp),
            )

        return Group(tape_label, tape, Text(""), table)


class ColorStatsPanel(Widget):
    """Horizontal true-color bar chart showing top colors across recent global history."""

    DEFAULT_CSS = """
    ColorStatsPanel {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._history: list[ColorEvent] = []

    def set_history(self, events: list[ColorEvent]) -> None:
        self._history = list(events)
        self.refresh()

    def prepend_event(self, event: ColorEvent) -> None:
        if (
            self._history
            and self._history[0].color == event.color
            and self._history[0].hex_code == event.hex_code
        ):
            return
        self._history.insert(0, event)
        self._history = self._history[:100]
        self.refresh()

    def render(self) -> Group:
        if not self._history:
            return Group(Text("Waiting for history data...", style="dim italic"))

        total = len(self._history)
        counts = Counter(item.color for item in self._history)
        top_colors = counts.most_common(7)
        max_count = top_colors[0][1] if top_colors else 1

        width = max(24, (self.size.width or 38) - 4)
        bar_max = max(8, width - 22)

        subtitle = Text(f"Top Colors • Last {total} Global Changes", style="dim")

        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(width=10)
        table.add_column(ratio=1)
        table.add_column(width=9, justify="right", style="dim")

        for color_name, count in top_colors:
            raw_hex = OFFICIAL_COLORS.get(color_name, "#ffffff")
            display_hex = ColorEvent(color_name, raw_hex).display_hex
            pct = (count / total) * 100
            filled = max(1, int(round((count / max_count) * bar_max)))
            empty = max(0, bar_max - filled)

            bar = Text()
            bar.append("█" * filled, style=display_hex)
            if empty:
                bar.append("░" * empty, style="#2a2f3a")

            table.add_row(
                Text(color_name.upper(), style=f"bold {display_hex}"),
                bar,
                f"{count:>2} ({pct:>4.0f}%)",
            )

        return Group(subtitle, Text(""), table)
