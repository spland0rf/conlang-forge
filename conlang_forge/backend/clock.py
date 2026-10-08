"""Time as a dependency, so quotas, token expiry and lockouts can be tested without sleeping."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

DAY_MS = 86_400_000
HOUR_MS = 3_600_000
MINUTE_MS = 60_000


class Clock:
    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class FakeClock(Clock):
    def __init__(self, start_ms: int = 1_790_000_000_000):
        self.t = start_ms
        self.slept: list = []

    def now_ms(self) -> int:
        return self.t

    def advance(self, ms: int) -> None:
        self.t += ms

    def sleep(self, seconds: float) -> None:      # sleeping just moves the clock
        self.slept.append(seconds)
        self.t += int(seconds * 1000)


def new_id() -> str:
    return uuid.uuid4().hex


def day_key(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def month_key(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m")


def next_day_start(ms: int) -> int:
    return (ms // DAY_MS + 1) * DAY_MS


def next_month_start(ms: int) -> int:
    d = datetime.fromtimestamp(ms / 1000, timezone.utc)
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp() * 1000)
