"""Main Textual 8.x live dashboard application for CheerLights Terminal."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Container, Horizontal, Vertical
from textual.theme import Theme
from textual.widgets import Footer, Header, Static

from . import __version__
from .client import (
    DEFAULT_POLL_INTERVAL,
    fetch_color_history,
    fetch_current_color,
    stream_mqtt_events,
)
from .colors import COLOR_NAMES, OFFICIAL_COLORS, ColorEvent, normalize_color
from .widgets import (
    LED_EFFECTS,
    CheerLightsHero,
    ColorHistoryPanel,
    ColorInspector,
    ColorPaletteBar,
    ColorSelected,
    ColorStatsPanel,
    LiveModeRequested,
    VirtualLEDStrip,
    ZenLampScreen,
)


def _build_cheerlights_theme(name: str, accent_hex: str) -> Theme:
    """Create a dark Textual Theme tinted to a CheerLights accent color."""
    return Theme(
        name=f"cheerlights-{name}",
        primary=accent_hex,
        secondary=accent_hex,
        accent=accent_hex,
        background="#0b0e14",
        surface="#121722",
        panel="#243045",
        foreground="#e2e8f0",
        dark=True,
    )


class CheerLightsCommands(Provider):
    """Command Palette provider for LED effects, colors, Zen mode, and copy actions."""

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        app = self.app
        if not isinstance(app, CheerLightsApp):
            return

        commands: list[tuple[str, str, object]] = [
            (
                "Toggle Zen / Ambient Lamp Mode",
                "Full-screen glowing desk lamp",
                app.action_toggle_zen,
            ),
            (
                "Return to Live Global CheerLights",
                "Exit demo mode and sync live",
                app.action_live_mode,
            ),
            ("Refresh CheerLights Feed", "Fetch latest color & history", app.action_refresh),
            (
                "Copy Current HEX Color",
                f"Copy {app.active_event.hex_code.upper()}",
                app.action_copy_hex,
            ),
            ("Copy Current RGB Tuple", f"Copy rgb{app.active_event.rgb}", app.action_copy_rgb),
            (
                "Copy WLED JSON Payload",
                "Copy WLED HTTP API JSON for active color",
                app.action_copy_wled,
            ),
        ]

        for effect in LED_EFFECTS:
            commands.append(
                (
                    f"LED Effect: {effect.title()}",
                    f"Switch virtual LED strip to {effect} pattern",
                    lambda eff=effect: app.set_led_effect(eff),
                )
            )

        for name, hex_code in OFFICIAL_COLORS.items():
            commands.append(
                (
                    f"Demo Preview: {name.title()} ({hex_code.upper()})",
                    f"Locally preview CheerLights {name}",
                    lambda n=name, h=hex_code: app.enter_demo_color(n, h),
                )
            )

        for label, help_text, callback in commands:
            score = matcher.match(label)
            if score > 0:
                yield Hit(score, matcher.highlight(label), callback, help=help_text)


class CheerLightsApp(App[None]):
    """Interactive, real-time Textual 8.x TUI dashboard for CheerLights."""

    TITLE = "CheerLights Terminal"
    SUB_TITLE = f"v{__version__} • Global Synchronized IoT Lights"
    CSS_PATH = "styles.tcss"
    COMMANDS = App.COMMANDS | {CheerLightsCommands}

    BINDINGS = [
        Binding("e", "cycle_effect", "LED Effect"),
        Binding("z", "toggle_zen", "Zen Lamp"),
        Binding("d", "cycle_demo", "Demo Color"),
        Binding("l", "live_mode", "Live Sync"),
        Binding("c", "copy_hex", "Copy HEX"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *,
        initial_event: ColorEvent | None = None,
        initial_history: list[ColorEvent] | None = None,
        enable_mqtt: bool = True,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        led_effect: str = "breathe",
        start_zen: bool = False,
        demo_color: str | None = None,
        offline_mode: bool = False,
        animate: bool = True,
    ) -> None:
        super().__init__()
        self._enable_mqtt = enable_mqtt and not offline_mode
        self._poll_interval = poll_interval
        self._offline_mode = offline_mode
        self._start_zen = start_zen
        self._animate = animate

        default_event = initial_event or ColorEvent("cyan", "#00ffff", datetime.now(UTC), "init")
        self.live_event: ColorEvent = default_event
        self.active_event: ColorEvent = default_event
        self.history: list[ColorEvent] = list(initial_history or [])
        self.demo_mode: bool = demo_color is not None or offline_mode
        self.led_effect: str = led_effect if led_effect in LED_EFFECTS else "breathe"
        self.transport_status: str = "DEMO" if offline_mode else "CONNECTING"
        self._demo_index: int = 0
        self._zen_screen: ZenLampScreen | None = None

        if demo_color:
            name, hex_code = normalize_color(demo_color)
            self.active_event = ColorEvent(name, hex_code, datetime.now(UTC), "demo")
            if name in COLOR_NAMES:
                self._demo_index = COLOR_NAMES.index(name)

        # Pre-register dynamic themes for all official CheerLights colors
        for name, hex_code in OFFICIAL_COLORS.items():
            accent = ColorEvent(name, hex_code).display_hex
            self.register_theme(_build_cheerlights_theme(name, accent))

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VirtualLEDStrip(
            initial_hex=self.active_event.display_hex,
            effect_mode=self.led_effect,
            animate=self._animate,
            id="led-top",
        )
        with Vertical(id="main-body"):
            with Horizontal(id="top-row"):
                hero_card = Container(
                    CheerLightsHero(animate=self._animate, id="hero"),
                    id="hero-card",
                )
                hero_card.border_title = "✦ CHEERLIGHTS GLOBAL LIGHT ✦"
                yield hero_card

                inspector_card = Container(
                    ColorInspector(id="inspector"),
                    id="inspector-card",
                )
                inspector_card.border_title = "● COLOR TELEMETRY"
                yield inspector_card

            with Horizontal(id="bottom-row"):
                history_card = Container(
                    ColorHistoryPanel(id="history"),
                    id="history-card",
                )
                history_card.border_title = "◈ LIVE HISTORY TIMELINE"
                yield history_card

                stats_card = Container(
                    ColorStatsPanel(id="stats"),
                    id="stats-card",
                )
                stats_card.border_title = "▤ COMMUNITY COLOR STATS"
                yield stats_card

        palette_card = Container(
            ColorPaletteBar(id="palette"),
            id="palette-card",
        )
        palette_card.border_title = "Demo Palette Preview (click a swatch, or press d / l)"
        yield palette_card

        yield Static(
            Text.assemble(
                ("Join the CheerLights IoT Community  •  ", "dim"),
                ("Discord: ", "bold bright_white"),
                ("https://cheerlights.com/discord", "bold underline"),
                ("  •  ", "dim"),
                ("https://cheerlights.com", "underline"),
            ),
            id="community-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._apply_active_event(self.active_event, notify=False)
        if self.history:
            self._apply_history(self.history)

        if not self._offline_mode:
            self._load_initial_data()
            self._run_live_feed()

        if self._start_zen:
            self.call_after_refresh(self.action_toggle_zen)

    def _apply_theme_for(self, event: ColorEvent) -> None:
        theme_name = f"cheerlights-{event.color}"
        if theme_name not in self.available_themes:
            self.register_theme(_build_cheerlights_theme(event.color, event.display_hex))
        self.theme = theme_name

    def _apply_active_event(self, event: ColorEvent, *, notify: bool = False) -> None:
        self.active_event = event
        self._apply_theme_for(event)

        hero = self.query_one("#hero", CheerLightsHero)
        hero.status_badge = self.transport_status
        hero.set_color(
            event.color,
            event.hex_code,
            event.display_hex,
            demo_mode=self.demo_mode,
        )

        led = self.query_one("#led-top", VirtualLEDStrip)
        led.target_hex = event.display_hex
        led.effect_mode = self.led_effect

        inspector = self.query_one("#inspector", ColorInspector)
        inspector.transport_status = self.transport_status
        inspector.effect_mode = self.led_effect
        inspector.update_event(event, demo_mode=self.demo_mode)

        palette = self.query_one("#palette", ColorPaletteBar)
        palette.set_state(event.color, demo_mode=self.demo_mode)

        if self._zen_screen is not None and self._zen_screen.is_mounted:
            self._zen_screen.update_live_color(event)

        if notify:
            prefix = "Demo Preview" if self.demo_mode else "Global CheerLights"
            self.notify(
                f"{event.color.upper()} ({event.hex_code.upper()})",
                title=prefix,
                timeout=3.5,
            )

    def _set_transport_status(self, status: str) -> None:
        self.transport_status = status
        if not self.is_mounted:
            return
        self.query_one("#hero", CheerLightsHero).status_badge = status
        self.query_one("#inspector", ColorInspector).transport_status = status

    def _apply_history(self, events: list[ColorEvent]) -> None:
        self.history = list(events)
        if not self.is_mounted:
            return
        self.query_one("#history", ColorHistoryPanel).set_history(events)
        self.query_one("#stats", ColorStatsPanel).set_history(events)

    def _handle_incoming_live_event(self, event: ColorEvent, *, announce: bool = True) -> None:
        changed = event.color != self.live_event.color or event.hex_code != self.live_event.hex_code
        self.live_event = event

        if changed:
            self.history.insert(0, event)
            self.history = self.history[:100]
            if self.is_mounted:
                self.query_one("#history", ColorHistoryPanel).prepend_event(event)
                self.query_one("#stats", ColorStatsPanel).prepend_event(event)

        if not self.demo_mode:
            self._apply_active_event(event, notify=announce and changed)
        elif announce and changed:
            self.notify(
                f"Global light changed to {event.color.upper()} — press [L] for Live",
                title="Live Update (Demo Active)",
                timeout=4.0,
            )

    @work(exclusive=True, group="initial-load")
    async def _load_initial_data(self) -> None:
        try:
            history = await fetch_color_history(100)
            if history:
                self._apply_history(history)
                self._handle_incoming_live_event(history[0], announce=False)
                return
        except Exception:
            pass

        try:
            current = await fetch_current_color()
            self._handle_incoming_live_event(current, announce=False)
        except Exception as exc:
            self._set_transport_status("OFFLINE")
            self.notify(f"Could not reach CheerLights API: {exc}", severity="warning", timeout=5.0)

    @work(exclusive=True, group="live-feed")
    async def _run_live_feed(self) -> None:
        """Maintain real-time MQTT subscription with automatic HTTP polling fallback."""
        mqtt_backoff = 5.0

        def _on_mqtt_state(is_connected: bool) -> None:
            if is_connected:
                self._set_transport_status("MQTT LIVE")
            elif self.transport_status == "MQTT LIVE":
                self._set_transport_status("CONNECTING")

        while True:
            if self._enable_mqtt:
                try:
                    self._set_transport_status("CONNECTING")
                    async for event in stream_mqtt_events(on_connected=_on_mqtt_state):
                        mqtt_backoff = 5.0
                        self._handle_incoming_live_event(event, announce=True)
                except asyncio.CancelledError:
                    return
                except Exception:
                    # Seamless fallback to HTTP polling while backing off MQTT reconnects
                    self._set_transport_status("HTTP POLL")
                    await self._poll_for_duration(mqtt_backoff)
                    mqtt_backoff = min(60.0, mqtt_backoff * 1.8)
            else:
                self._set_transport_status("HTTP POLL")
                await self._poll_once()
                await asyncio.sleep(self._poll_interval)

    async def _poll_for_duration(self, duration: float) -> None:
        elapsed = 0.0
        step = min(self._poll_interval, max(3.0, duration))
        while elapsed < duration:
            await self._poll_once()
            sleep_for = min(step, duration - elapsed)
            await asyncio.sleep(sleep_for)
            elapsed += sleep_for

    async def _poll_once(self) -> None:
        try:
            event = await fetch_current_color()
            self._handle_incoming_live_event(event, announce=True)
        except asyncio.CancelledError:
            raise
        except Exception:
            self._set_transport_status("OFFLINE")

    # ── Interactive Actions & Messages ────────────────────────────────────────

    def on_color_selected(self, message: ColorSelected) -> None:
        self.enter_demo_color(message.color_name, message.hex_code)

    def on_live_mode_requested(self, _message: LiveModeRequested) -> None:
        self.action_live_mode()

    def enter_demo_color(self, color_name: str, hex_code: str | None = None) -> None:
        """Preview any CheerLights color locally without affecting the global network."""
        name, resolved_hex = normalize_color(color_name, hex_code)
        self.demo_mode = True
        if name in COLOR_NAMES:
            self._demo_index = COLOR_NAMES.index(name)
        event = ColorEvent(name, resolved_hex, datetime.now(UTC), "demo")
        self._apply_active_event(event, notify=True)

    def set_led_effect(self, effect_name: str) -> None:
        if effect_name not in LED_EFFECTS:
            return
        self.led_effect = effect_name
        self.query_one("#led-top", VirtualLEDStrip).effect_mode = effect_name
        self.query_one("#inspector", ColorInspector).effect_mode = effect_name
        if self._zen_screen is not None and self._zen_screen.is_mounted:
            self._zen_screen.update_effect(effect_name)
        self.notify(f"LED pattern → {effect_name.upper()}", title="Virtual LEDs", timeout=2.5)

    def action_cycle_effect(self) -> None:
        next_idx = (LED_EFFECTS.index(self.led_effect) + 1) % len(LED_EFFECTS)
        self.set_led_effect(LED_EFFECTS[next_idx])

    def action_cycle_demo(self) -> None:
        if self.demo_mode:
            self._demo_index = (self._demo_index + 1) % len(COLOR_NAMES)
        else:
            current_idx = (
                COLOR_NAMES.index(self.active_event.color)
                if self.active_event.color in COLOR_NAMES
                else 0
            )
            self._demo_index = (current_idx + 1) % len(COLOR_NAMES)
        next_color = COLOR_NAMES[self._demo_index]
        self.enter_demo_color(next_color, OFFICIAL_COLORS[next_color])

    def action_live_mode(self) -> None:
        if self._offline_mode:
            self.notify("Running in offline demo mode", title="Offline", timeout=2.5)
            return
        self.demo_mode = False
        self._apply_active_event(self.live_event, notify=False)
        self.query_one("#led-top", VirtualLEDStrip).trigger_ripple()
        live_name = self.live_event.color.upper()
        live_hex = self.live_event.hex_code.upper()
        self.notify(
            f"Synced to global {live_name} ({live_hex})",
            title="Live Mode",
            timeout=3.0,
        )

    def action_toggle_zen(self) -> None:
        if isinstance(self.screen, ZenLampScreen):
            self.pop_screen()
            self._zen_screen = None
            return
        self._zen_screen = ZenLampScreen(
            self.active_event,
            effect_mode=self.led_effect,
            animate=self._animate,
        )
        self.push_screen(self._zen_screen, self._on_zen_dismissed)

    def _on_zen_dismissed(self, _result: None) -> None:
        self._zen_screen = None

    def action_refresh(self) -> None:
        if self._offline_mode:
            self.notify("Offline demo mode — live refresh disabled", timeout=2.5)
            return
        self.notify("Refreshing CheerLights feed...", timeout=2.0)
        self._load_initial_data()

    def action_copy_hex(self) -> None:
        value = self.active_event.hex_code.upper()
        self.copy_to_clipboard(value)
        self.notify(f"Copied {value} to clipboard", title="Clipboard", timeout=2.5)

    def action_copy_rgb(self) -> None:
        r, g, b = self.active_event.rgb
        value = f"rgb({r}, {g}, {b})"
        self.copy_to_clipboard(value)
        self.notify(f"Copied {value} to clipboard", title="Clipboard", timeout=2.5)

    def action_copy_wled(self) -> None:
        r, g, b = self.active_event.rgb
        payload = json.dumps({"on": True, "seg": [{"col": [[r, g, b]]}]})
        self.copy_to_clipboard(payload)
        self.notify(f"Copied WLED JSON: {payload}", title="Clipboard", timeout=3.5)
