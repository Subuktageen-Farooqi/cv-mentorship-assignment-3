from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from app.models import StreamState


class StreamManager:
    def __init__(self) -> None:
        self._state = StreamState(connected=False)

    def attach(self, url: str) -> StreamState:
        parsed = urlparse(url)
        if parsed.scheme not in {"rtsp", "rtsps", "http", "https"}:
            self._state = StreamState(connected=False, url=url, last_error="Unsupported stream protocol")
            return self._state
        if not parsed.netloc:
            self._state = StreamState(connected=False, url=url, last_error="Invalid stream URL")
            return self._state

        self._state = StreamState(connected=True, url=url, connected_at=datetime.utcnow(), last_error=None)
        return self._state

    def state(self) -> StreamState:
        return self._state
