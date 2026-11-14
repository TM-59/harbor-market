from dataclasses import dataclass
from typing import Protocol

from harbor_market.domain import Event, TradingSession


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session: TradingSession
    events: tuple[Event, ...]
    revision: int


class SessionRepository(Protocol):
    def add(self, session: TradingSession) -> None: ...

    def get(self, session_id: str) -> SessionRecord | None: ...

    def save(
        self, session: TradingSession, events: tuple[Event, ...], expected_revision: int
    ) -> bool: ...
