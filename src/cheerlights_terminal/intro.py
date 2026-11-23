"""TerminalTextEffects (TTE) intro and one-shot CLI rendering."""

from __future__ import annotations

import random
import sys
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from terminaltexteffects.effects.effect_beams import Beams
from terminaltexteffects.effects.effect_expand import Expand
from terminaltexteffects.effects.effect_fireworks import Fireworks
from terminaltexteffects.effects.effect_rain import Rain
from terminaltexteffects.effects.effect_slide import Slide
from terminaltexteffects.effects.effect_spotlights import Spotlights
from terminaltexteffects.utils.graphics import Color as TTEColor

from .ascii_art import CHEERLIGHTS_ASCII, render_glowing_ascii
from .colors import (
    ColorEvent,
    build_gradient_stops,
    contrasting_text_color,
    format_relative_time,
)

EFFECT_REGISTRY: dict[str, type[Any]] = {
    "beams": Beams,
    "fireworks": Fireworks,
    "slide": Slide,
    "expand": Expand,
    "rain": Rain,
    "spotlights": Spotlights,
}

AVAILABLE_EFFECTS: tuple[str, ...] = tuple(EFFECT_REGISTRY.keys())


def create_tte_effect(
    text: str,
    hex_code: str,
    effect_name: str = "beams",
    fast: bool = True,
) -> Any:
    """Instantiate a TerminalTextEffects animation tinted to the CheerLights color."""
    chosen = effect_name.lower()
    if chosen == "random":
        chosen = random.choice(AVAILABLE_EFFECTS)
    effect_cls = EFFECT_REGISTRY.get(chosen, Beams)
    effect = effect_cls(text)

    deep, base, bright = build_gradient_stops(hex_code)
    stops = (TTEColor(deep), TTEColor(base), TTEColor(bright))
    if hasattr(effect.effect_config, "final_gradient_stops"):
        effect.effect_config.final_gradient_stops = stops
    if hasattr(effect.effect_config, "beam_gradient_stops"):
        effect.effect_config.beam_gradient_stops = (TTEColor(bright), TTEColor(base))
    if hasattr(effect.effect_config, "firework_colors"):
        effect.effect_config.firework_colors = stops

    if fast:
        # Keep startup/intro animations snappy and punchy
        effect.terminal_config.frame_rate = 120
        if hasattr(effect.effect_config, "beam_delay"):
            effect.effect_config.beam_delay = 3
        if hasattr(effect.effect_config, "beam_row_speed_range"):
            effect.effect_config.beam_row_speed_range = (30, 60)
        if hasattr(effect.effect_config, "beam_column_speed_range"):
            effect.effect_config.beam_column_speed_range = (15, 25)
        if hasattr(effect.effect_config, "final_wipe_speed"):
            effect.effect_config.final_wipe_speed = 4

    return effect


def play_tte_animation(
    hex_code: str,
    effect_name: str = "beams",
    fast: bool = True,
) -> bool:
    """Play a TTE animation of the CheerLights ASCII banner on stdout.

    Returns True if the animation ran, False if stdout is not an interactive TTY.
    """
    if not sys.stdout.isatty():
        return False

    try:
        effect = create_tte_effect(
            CHEERLIGHTS_ASCII,
            hex_code=hex_code,
            effect_name=effect_name,
            fast=fast,
        )
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)
        return True
    except KeyboardInterrupt:
        return True
    except Exception:
        return False


def display_once(
    event: ColorEvent,
    history: list[ColorEvent] | None = None,
    effect_name: str | None = "beams",
    console: Console | None = None,
) -> None:
    """Render a one-shot CheerLights view (optional TTE animation + Rich color card)."""
    out = console or Console()
    accent = event.display_hex
    fg = contrasting_text_color(accent)

    animated = False
    if effect_name and effect_name != "none":
        animated = play_tte_animation(accent, effect_name=effect_name, fast=True)

    if not animated:
        art = render_glowing_ascii(event.rgb, shimmer=False)
        out.print()
        out.print(
            Panel(
                Align.center(art),
                title=f"[bold {fg} on {accent}]  ✦ CHEERLIGHTS TERMINAL ✦  [/]",
                border_style=f"bold {accent}",
                padding=(1, 3),
                expand=False,
            )
        )

    r, g, b = event.rgb
    h, s, l_val = event.hsl

    info_table = Table.grid(padding=(0, 2))
    info_table.add_column(style="bold bright_white")
    info_table.add_column()
    info_table.add_row(
        "Current Color",
        Text.assemble(
            ("████ ", f"bold {accent}"),
            (event.color.upper(), f"bold {accent}"),
            (f"  ({event.hex_code.upper()})", "dim"),
        ),
    )
    info_table.add_row("RGB / HSL", f"rgb({r}, {g}, {b})   •   hsl({h}°, {s}%, {l_val}%)")
    info_table.add_row("Updated", format_relative_time(event.timestamp))

    if history:
        tape = Text()
        for item in history[:20]:
            tape.append("██", style=item.display_hex)
        info_table.add_row("Recent Tape", tape)

    info_table.add_row(
        "Community",
        Text.assemble(
            ("Discord ", "bright_white"),
            ("https://cheerlights.com/discord", f"bold {accent} underline"),
        ),
    )

    out.print()
    out.print(
        Panel(
            info_table,
            title=f"[bold {fg} on {accent}]  ● LIVE TELEMETRY  [/]",
            border_style=accent,
            padding=(1, 2),
            expand=False,
        )
    )
