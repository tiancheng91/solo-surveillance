from __future__ import annotations

from abc import ABC, abstractmethod


class Notifier(ABC):
    """Base class for event notification mechanisms.

    Implementations must be non-blocking (fire-and-forget, e.g. daemon thread).
    """

    @abstractmethod
    def fire(self, event_type: str, data: dict) -> None: ...
