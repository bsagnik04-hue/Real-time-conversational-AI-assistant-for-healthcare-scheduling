"""Appointment event bus for the dashboard API."""
import asyncio
import json
import logging
import os

import httpx

_subscribers: list[asyncio.Queue[str]] = []
logger = logging.getLogger(__name__)


async def broadcast(event_type: str, data: dict) -> None:
    payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    for queue in list(_subscribers):
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            _subscribers.remove(queue)


def subscribe() -> asyncio.Queue[str]:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=50)
    _subscribers.append(queue)
    return queue


def unsubscribe(queue: asyncio.Queue[str]) -> None:
    if queue in _subscribers:
        _subscribers.remove(queue)


async def publish_voice_event(event_type: str, data: dict) -> None:
    """Forward worker events to the API process, which owns dashboard SSE clients."""
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.post(f"{base_url}/api/internal/events", json={"type": event_type, "data": data})
            response.raise_for_status()
    except httpx.HTTPError:
        # The appointment is already committed; a dashboard notification must
        # never turn a successful booking into a failed voice tool call.
        logger.exception("Could not forward appointment event to API process")
