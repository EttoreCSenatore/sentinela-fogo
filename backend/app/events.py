"""In-process event bus feeding the Server-Sent Events stream (/api/stream).

Single-process by design (matches the self-hosted stack). With several backend workers, swap this for
Redis pub/sub or Postgres LISTEN/NOTIFY.
"""

import asyncio
import json
import logging

log = logging.getLogger(__name__)
QUEUE_SIZE = 100
MAX_SUBSCRIBERS = 500  # the dashboard is public; bound memory and file descriptors


class EventBus:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        if len(self._subs) >= MAX_SUBSCRIBERS:
            raise RuntimeError("too many subscribers")
        q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def publish(self, event: str, data: dict) -> None:
        msg = f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
        for q in list(self._subs):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                # A slow client loses events rather than slowing everyone down. It reloads on the next refresh event.
                log.debug("dropping event for slow subscriber")

    @property
    def subscribers(self) -> int:
        return len(self._subs)


bus = EventBus()
