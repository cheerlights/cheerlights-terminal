"""ASCII art assets and true-color Rich rendering helpers for CheerLights."""

from __future__ import annotations

import math

from rich.text import Text

from .colors import rgb_to_hex, scale_brightness, tint_rgb

CHEERLIGHTS_ASCII = """\
 ██████╗ ██╗  ██╗ ███████╗ ███████╗ ██████╗
██╔════╝ ██║  ██║ ██╔════╝ ██╔════╝ ██╔══██╗
██║      ███████║ █████╗   █████╗   ██████╔╝
██║      ██╔══██║ ██╔══╝   ██╔══╝   ██╔══██╗
╚██████╗ ██║  ██║ ███████╗ ███████╗ ██║  ██║
 ╚═════╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═╝

██╗     ██╗  ██████╗  ██╗  ██╗ ████████╗ ███████╗
██║     ██║ ██╔════╝  ██║  ██║ ╚══██╔══╝ ██╔════╝
██║     ██║ ██║  ███╗ ███████║    ██║    ███████╗
██║     ██║ ██║   ██║ ██╔══██║    ██║    ╚════██║
███████╗██║ ╚██████╔╝ ██║  ██║    ██║    ███████║
╚══════╝╚═╝  ╚═════╝  ╚═╝  ╚═╝    ╚═╝    ╚══════╝"""

CHEERLIGHTS_LINES: tuple[str, ...] = tuple(CHEERLIGHTS_ASCII.splitlines())


def render_glowing_ascii(
    rgb: tuple[int, int, int],
    phase: float = 0.0,
    shimmer: bool = True,
    flash: float = 0.0,
) -> Text:
    """Render CHEERLIGHTS_ASCII with a true-color vertical gradient and subtle shimmer."""
    text = Text(no_wrap=True)
    total_lines = len(CHEERLIGHTS_LINES)
    # Apply temporary white flash on color change transitions
    base_rgb = tint_rgb(rgb, min(0.85, flash)) if flash > 0.01 else rgb

    for row_idx, line in enumerate(CHEERLIGHTS_LINES):
        if not line.strip():
            text.append("\n")
            continue

        # Subtle vertical sheen across the two stacked words
        local_row = row_idx if row_idx < 6 else row_idx - 7
        vertical_curve = 1.18 - 0.14 * abs(local_row - 2.2)

        if shimmer:
            # Smooth horizontal wave traveling across the letters
            for col_idx, ch in enumerate(line):
                if ch == " ":
                    text.append(" ")
                    continue
                wave = math.sin(phase * 2.2 - col_idx * 0.14 - row_idx * 0.28)
                factor = vertical_curve + 0.22 * wave
                cell_hex = rgb_to_hex(scale_brightness(base_rgb, factor))
                style = f"bold {cell_hex}" if factor > 1.12 else cell_hex
                text.append(ch, style=style)
        else:
            row_hex = rgb_to_hex(scale_brightness(base_rgb, vertical_curve))
            text.append(line, style=f"bold {row_hex}")

        if row_idx < total_lines - 1:
            text.append("\n")

    return text
