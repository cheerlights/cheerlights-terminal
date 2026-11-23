"""Headless Textual Pilot integration tests for CheerLightsApp."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cheerlights_terminal.app import CheerLightsApp
from cheerlights_terminal.colors import ColorEvent
from cheerlights_terminal.widgets import (
    CheerLightsHero,
    ColorHistoryPanel,
    ColorInspector,
    ColorStatsPanel,
    VirtualLEDStrip,
    ZenLampScreen,
)


def _sample_history() -> list[ColorEvent]:
    now = datetime.now(UTC)
    return [
        ColorEvent("cyan", "#00ffff", now - timedelta(minutes=1), "history"),
        ColorEvent("magenta", "#ff00ff", now - timedelta(minutes=5), "history"),
        ColorEvent("cyan", "#00ffff", now - timedelta(minutes=12), "history"),
        ColorEvent("orange", "#ffa500", now - timedelta(minutes=30), "history"),
    ]


async def test_dashboard_mount_and_widgets() -> None:
    history = _sample_history()
    app = CheerLightsApp(
        initial_event=history[0],
        initial_history=history,
        offline_mode=True,
        animate=False,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.active_event.color == "cyan"
        assert app.theme == "cheerlights-cyan"
        assert app.query_one("#hero", CheerLightsHero).color_name == "cyan"
        assert app.query_one("#led-top", VirtualLEDStrip).effect_mode == "breathe"
        assert app.query_one("#inspector", ColorInspector).hex_code == "#00ffff"
        assert app.query_one("#history", ColorHistoryPanel) is not None
        assert app.query_one("#stats", ColorStatsPanel) is not None


async def test_cycle_led_effect_and_demo_palette() -> None:
    history = _sample_history()
    app = CheerLightsApp(
        initial_event=history[0],
        initial_history=history,
        offline_mode=True,
        animate=False,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Cycle LED effect with 'e'
        await pilot.press("e")
        assert app.led_effect == "chase"
        assert app.query_one("#led-top", VirtualLEDStrip).effect_mode == "chase"

        # Click a palette swatch to preview pink
        await pilot.click("#swatch-pink")
        await pilot.pause()
        assert app.demo_mode is True
        assert app.active_event.color == "pink"
        assert app.theme == "cheerlights-pink"


async def test_zen_lamp_mode_push_and_exit() -> None:
    history = _sample_history()
    app = CheerLightsApp(
        initial_event=history[0],
        initial_history=history,
        offline_mode=True,
        animate=False,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert not isinstance(app.screen, ZenLampScreen)

        await pilot.press("z")
        await pilot.pause()
        assert isinstance(app.screen, ZenLampScreen)

        # Toggle logo inside Zen mode and cycle LED effect
        await pilot.press("a")
        await pilot.press("e")
        await pilot.pause()
        assert app.led_effect == "chase"

        # Exit Zen mode via Escape
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, ZenLampScreen)


async def test_live_mqtt_event_updates_dashboard_and_demo_isolation() -> None:
    history = _sample_history()
    app = CheerLightsApp(
        initial_event=history[0],
        initial_history=history,
        offline_mode=True,
        animate=False,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Simulate live mode receiving an incoming MQTT update
        app._offline_mode = False
        app.demo_mode = False

        incoming = ColorEvent("purple", "#800080", datetime.now(UTC), "mqtt")
        app._handle_incoming_live_event(incoming, announce=True)
        await pilot.pause()

        assert app.active_event.color == "purple"
        assert app.theme == "cheerlights-purple"
        assert app.history[0].color == "purple"

        # Enter demo mode, ensure live update does not overwrite preview until 'l'
        app.enter_demo_color("yellow")
        await pilot.pause()
        assert app.active_event.color == "yellow"

        next_live = ColorEvent("red", "#ff0000", datetime.now(UTC), "mqtt")
        app._handle_incoming_live_event(next_live, announce=True)
        await pilot.pause()
        assert app.active_event.color == "yellow"
        assert app.live_event.color == "red"

        # Return to Live mode with 'l'
        await pilot.press("l")
        await pilot.pause()
        assert app.demo_mode is False
        assert app.active_event.color == "red"
        assert app.theme == "cheerlights-red"
