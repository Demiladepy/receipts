"""A clock that only moves when a simulated read or action succeeds."""

from datetime import datetime, timedelta


def isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.isoformat(timespec="seconds")


class Clock:
    def __init__(self, start: datetime):
        if start.tzinfo is None:
            raise ValueError("clock start must be timezone-aware")
        self._current = start

    def peek(self) -> str:
        return isoformat(self._current)

    def now(self) -> str:
        self._current += timedelta(seconds=1)
        return isoformat(self._current)
