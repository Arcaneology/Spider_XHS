from collections import deque
import time
from typing import Deque, Optional


class RateLimiter:
    """Simple rate limiter to control API call frequency."""

    def __init__(self, max_per_window: Optional[int], window_seconds: int = 600, min_interval: float = 0.0) -> None:
        self.max_per_window = max_per_window if max_per_window and max_per_window > 0 else None
        self.window_seconds = max(window_seconds, 1)
        self.min_interval = max(min_interval, 0.0)
        self._call_times: Deque[float] = deque()
        self._last_call: float = 0.0

    def wait(self) -> None:
        now = time.time()
        # enforce minimum interval
        if self.min_interval > 0 and self._last_call > 0:
            delta = now - self._last_call
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
                now = time.time()

        # enforce max per window
        if self.max_per_window:
            self._trim(now)
            while len(self._call_times) >= self.max_per_window:
                oldest = self._call_times[0]
                sleep_for = max(self.window_seconds - (now - oldest), 0.1)
                time.sleep(sleep_for)
                now = time.time()
                self._trim(now)

        self._call_times.append(time.time())
        self._last_call = time.time()

    def _trim(self, now: float) -> None:
        while self._call_times and now - self._call_times[0] >= self.window_seconds:
            self._call_times.popleft()
