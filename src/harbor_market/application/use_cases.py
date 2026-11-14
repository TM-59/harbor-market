from collections.abc import Callable
from uuid import uuid4

from harbor_market.application.ports import SessionRecord, SessionRepository
from harbor_market.domain import (
    DayAdvanced,
    Event,
    Good,
    SessionSettled,
    TradeExecuted,
    TradingSession,
)


class SessionNotFound(LookupError):
    """No trading session exists with the requested identity."""


class SessionConflict(RuntimeError):
    """The session changed after it was read."""


def _load(repository: SessionRepository, session_id: str) -> SessionRecord:
    record = repository.get(session_id)
    if record is None:
        raise SessionNotFound(session_id)
    return record


def _save(repository: SessionRepository, record: SessionRecord, events: tuple[Event, ...]) -> None:
    if not repository.save(record.session, events, record.revision):
        raise SessionConflict(record.session.session_id)


class StartSession:
    def __init__(
        self, repository: SessionRepository, id_factory: Callable[[], str] | None = None
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def execute(self) -> TradingSession:
        session = TradingSession(self._id_factory())
        self._repository.add(session)
        return session


class ReadSession:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def execute(self, session_id: str) -> SessionRecord:
        return _load(self._repository, session_id)


class BuyGoods:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def execute(self, session_id: str, good: Good, quantity: int) -> TradeExecuted:
        record = _load(self._repository, session_id)
        event = record.session.buy(good, quantity)
        _save(self._repository, record, (event,))
        return event


class SellGoods:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def execute(self, session_id: str, good: Good, quantity: int) -> TradeExecuted:
        record = _load(self._repository, session_id)
        event = record.session.sell(good, quantity)
        _save(self._repository, record, (event,))
        return event


class AdvanceSession:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def execute(self, session_id: str) -> DayAdvanced | SessionSettled:
        record = _load(self._repository, session_id)
        event = record.session.advance()
        _save(self._repository, record, (event,))
        return event
