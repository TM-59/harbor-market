"""Persistence ports used by the application layer."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from harbor_market.domain import Event, TradingSession


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """A stored session with its ordered events and the revision it was read at."""

    session: TradingSession
    events: tuple[Event, ...]
    revision: int


class SessionRepository(Protocol):
    """Port for storing sessions; `save` succeeds only for the revision that was read."""

    def add(self, session: TradingSession) -> None:
        """Store a new session at revision 0 with no events."""

    def get(self, session_id: str) -> SessionRecord | None:
        """Return the session, its events and revision, or None when it does not exist."""

    def save(
        self, session: TradingSession, events: tuple[Event, ...], expected_revision: int
    ) -> bool:
        """Write the session and append `events` if the revision is unchanged."""
