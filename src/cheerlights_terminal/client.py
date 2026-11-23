"""Async CheerLights API client with cross-platform MQTT streaming and HTTP fallback."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Any

import cheerlights_api
import paho.mqtt.client as mqtt

from .colors import ColorEvent, normalize_color

MQTT_BROKER = "mqtt.cheerlights.com"
MQTT_PORT = 1883
MQTT_TOPIC_COLOR = "cheerlights"
MQTT_TOPIC_HEX = "cheerlightsRGB"
DEFAULT_POLL_INTERVAL = 15.0
MQTT_TIMEOUT = 10.0


def parse_timestamp(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 UTC timestamp returned by ThingSpeak."""
    if not raw:
        return None
    try:
        cleaned = raw.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


async def fetch_current_color() -> ColorEvent:
    """Fetch the latest CheerLights color asynchronously via cheerlights-api."""
    data = await asyncio.to_thread(cheerlights_api.get_current_color)
    name, hex_code = normalize_color(data.get("color"), data.get("hex"))
    return ColorEvent(
        color=name,
        hex_code=hex_code,
        timestamp=datetime.now(UTC),
        source="api",
    )


async def fetch_color_history(count: int = 100) -> list[ColorEvent]:
    """Fetch recent CheerLights color history (returned newest-first)."""
    safe_count = max(1, min(8000, count))
    entries = await asyncio.to_thread(cheerlights_api.get_color_history, safe_count)
    events: list[ColorEvent] = []
    for entry in reversed(entries):
        name, hex_code = normalize_color(entry.get("color"), entry.get("hex"))
        events.append(
            ColorEvent(
                color=name,
                hex_code=hex_code,
                timestamp=parse_timestamp(entry.get("timestamp")),
                source="history",
            )
        )
    return events


def decode_mqtt_payload(topic: str, payload: bytes | bytearray | str) -> ColorEvent | None:
    """Decode an MQTT CheerLights message into a normalized ColorEvent."""
    text = (
        payload.decode("utf-8", errors="ignore").strip()
        if isinstance(payload, (bytes, bytearray))
        else str(payload).strip()
    )
    if not text:
        return None

    if topic == MQTT_TOPIC_HEX:
        name, hex_code = normalize_color(hex_code=text)
    else:
        name, hex_code = normalize_color(color_name=text)

    return ColorEvent(
        color=name,
        hex_code=hex_code,
        timestamp=datetime.now(UTC),
        source="mqtt",
    )


async def stream_mqtt_events(
    broker: str = MQTT_BROKER,
    port: int = MQTT_PORT,
    timeout: float = MQTT_TIMEOUT,
    on_connected: Callable[[bool], None] | None = None,
) -> AsyncIterator[ColorEvent]:
    """Yield live CheerLights ColorEvents via paho-mqtt (works on all event loops/OSes)."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[ColorEvent | Exception | None] = asyncio.Queue()
    connected = asyncio.Event()
    connect_error: list[Exception] = []

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def _on_connect(
        mqtt_client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if getattr(reason_code, "is_failure", False):
            connect_error.append(ConnectionError(f"MQTT connect failed: {reason_code}"))
            loop.call_soon_threadsafe(connected.set)
            return

        mqtt_client.subscribe([(MQTT_TOPIC_COLOR, 0), (MQTT_TOPIC_HEX, 0)])
        loop.call_soon_threadsafe(connected.set)
        if on_connected is not None:
            loop.call_soon_threadsafe(on_connected, True)

    def _on_disconnect(
        _mqtt_client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if on_connected is not None:
            loop.call_soon_threadsafe(on_connected, False)
        # If unexpected disconnect after connecting, signal the stream to reconnect
        if connected.is_set() and getattr(reason_code, "is_failure", False):
            loop.call_soon_threadsafe(
                queue.put_nowait,
                ConnectionError(f"MQTT disconnected: {reason_code}"),
            )

    def _on_message(
        _mqtt_client: mqtt.Client,
        _userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        event = decode_mqtt_payload(str(message.topic), message.payload)
        if event is not None:
            loop.call_soon_threadsafe(queue.put_nowait, event)

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message

    try:
        await asyncio.to_thread(client.connect, broker, port, 60)
        client.loop_start()

        await asyncio.wait_for(connected.wait(), timeout=timeout)
        if connect_error:
            raise connect_error[0]

        last_emitted: tuple[str, str] | None = None
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item

            key = (item.color, item.hex_code)
            if key == last_emitted:
                continue
            last_emitted = key
            yield item
    finally:
        if on_connected is not None:
            on_connected(False)
        with contextlib.suppress(Exception):
            client.disconnect()
        with contextlib.suppress(Exception):
            await asyncio.to_thread(client.loop_stop)
