"""CLI entry point for CheerLights Terminal."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from rich.console import Console

from . import __version__
from .app import CheerLightsApp
from .cheerlights import get_color_history, get_current_color
from .client import parse_timestamp
from .colors import COLOR_NAMES, ColorEvent, normalize_color
from .intro import AVAILABLE_EFFECTS, display_once, play_tte_animation
from .widgets.led_strip import LED_EFFECTS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cheerlights",
        description="CheerLights Terminal: live Textual TUI for global CheerLights IoT lights.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"cheerlights-terminal {__version__}",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print a one-shot snapshot (TTE animation + color card) and exit.",
    )
    parser.add_argument(
        "--intro",
        action="store_true",
        help="Play a TerminalTextEffects intro animation before launching the dashboard.",
    )
    parser.add_argument(
        "--effect",
        choices=[*AVAILABLE_EFFECTS, "random", "none"],
        default="beams",
        help="TerminalTextEffects animation for --intro or --once (default: beams).",
    )
    parser.add_argument(
        "--led-effect",
        choices=list(LED_EFFECTS),
        default="breathe",
        help="Initial virtual LED strip animation pattern (default: breathe).",
    )
    parser.add_argument(
        "--zen",
        action="store_true",
        help="Start directly in full-screen Zen / Ambient Lamp mode.",
    )
    parser.add_argument(
        "--demo",
        nargs="?",
        const="cyan",
        metavar="COLOR",
        help=f"Start in offline Demo preview mode ({', '.join(COLOR_NAMES)}).",
    )
    parser.add_argument(
        "--no-mqtt",
        action="store_true",
        help="Disable real-time MQTT streaming and use HTTP polling only.",
    )
    return parser


def _fetch_sync_snapshot(demo_color: str | None) -> tuple[ColorEvent, list[ColorEvent]]:
    """Fetch initial color + short history synchronously for --once or --intro."""
    if demo_color:
        name, hex_code = normalize_color(demo_color)
        event = ColorEvent(name, hex_code, datetime.now(UTC), "demo")
        return event, [event]

    console = Console(stderr=True)
    with console.status("Fetching current CheerLights color...", spinner="dots"):
        raw_history = get_color_history(25)
        if raw_history:
            events = [
                ColorEvent(
                    *normalize_color(item.get("color"), item.get("hex")),
                    timestamp=parse_timestamp(item.get("timestamp")),
                    source="history",
                )
                for item in reversed(raw_history)
            ]
            return events[0], events

        name, hex_code = get_current_color()
        event = ColorEvent(name, hex_code, datetime.now(UTC), "api")
        return event, [event]


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the `cheerlights` command."""
    args = build_parser().parse_args(argv)

    try:
        if args.once:
            event, history = _fetch_sync_snapshot(args.demo)
            display_once(event, history=history, effect_name=args.effect)
            return 0

        initial_event: ColorEvent | None = None
        initial_history: list[ColorEvent] | None = None

        if args.intro and args.effect != "none":
            initial_event, initial_history = _fetch_sync_snapshot(args.demo)
            play_tte_animation(
                initial_event.display_hex,
                effect_name=args.effect,
                fast=True,
            )

        app = CheerLightsApp(
            initial_event=initial_event,
            initial_history=initial_history,
            enable_mqtt=not args.no_mqtt,
            led_effect=args.led_effect,
            start_zen=args.zen,
            demo_color=args.demo,
            offline_mode=args.demo is not None,
        )
        app.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        Console(stderr=True).print(f"[red]Error:[/red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
