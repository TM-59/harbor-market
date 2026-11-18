# Copyright 2026 TM-59
"""Framework-independent trading use cases."""

from typing import TYPE_CHECKING
from uuid import uuid4

from harbor_market.domain import (
    DayAdvanced,
    Event,
    Good,
    SessionSettled,
    TradeExecuted,
    TradingSession,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from harbor_market.application.ports import SessionRecord, SessionRepository


class SessionNotFoundError(LookupError):
    """No trading session exists with the requested identity."""


class SessionConflictError(RuntimeError):
    """The session changed after it was read."""


def _load(repository: SessionRepository, session_id: str) -> SessionRecord:
    record = repository.get(session_id)
    if record is None:
        raise SessionNotFoundError(session_id)
    return record


def _save(repository: SessionRepository, record: SessionRecord, events: tuple[Event, ...]) -> None:
    if not repository.save(record.session, events, record.revision):
        raise SessionConflictError(record.session.session_id)


class StartSession:
    """Create a new session and store it."""

    def __init__(
        self, repository: SessionRepository, id_factory: Callable[[], str] | None = None
    ) -> None:
        """Use `repository` for storage and `id_factory` for new identities."""
        self._repository = repository
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def execute(self) -> TradingSession:
        """Start a session on day one and return it."""
        session = TradingSession(self._id_factory())
        self._repository.add(session)
        return session


class ReadSession:
    """Read a stored session and its event history."""

    def __init__(self, repository: SessionRepository) -> None:
        """Use `repository` to read sessions."""
        self._repository = repository

    def execute(self, session_id: str) -> SessionRecord:
        """Return the stored session with identity `session_id`."""
        return _load(self._repository, session_id)


class BuyGoods:
    """Buy goods at today's quote in a stored session."""

    def __init__(self, repository: SessionRepository) -> None:
        """Use `repository` to read and save sessions."""
        self._repository = repository

    def execute(self, session_id: str, good: Good, quantity: int) -> TradeExecuted:
        """Buy `quantity` of `good`, save, and return the trade event."""
        record = _load(self._repository, session_id)
        event = record.session.buy(good, quantity)
        _save(self._repository, record, (event,))
        return event


class SellGoods:
    """Sell goods at today's quote in a stored session."""

    def __init__(self, repository: SessionRepository) -> None:
        """Use `repository` to read and save sessions."""
        self._repository = repository

    def execute(self, session_id: str, good: Good, quantity: int) -> TradeExecuted:
        """Sell `quantity` of `good`, save, and return the trade event."""
        record = _load(self._repository, session_id)
        event = record.session.sell(good, quantity)
        _save(self._repository, record, (event,))
        return event


class AdvanceSession:
    """Move a stored session to the next day, or settle it after day six."""

    def __init__(self, repository: SessionRepository) -> None:
        """Use `repository` to read and save sessions."""
        self._repository = repository

    def execute(self, session_id: str) -> DayAdvanced | SessionSettled:
        """Advance the session, save, and return the day or settlement event."""
        record = _load(self._repository, session_id)
        event = record.session.advance()
        _save(self._repository, record, (event,))
        return event
