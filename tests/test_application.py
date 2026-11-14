from copy import deepcopy

import pytest

from harbor_market.application.ports import SessionRecord, SessionRepository
from harbor_market.application.use_cases import (
    AdvanceSession,
    BuyGoods,
    ReadSession,
    SellGoods,
    SessionConflict,
    SessionNotFound,
    StartSession,
)
from harbor_market.domain import (
    Coins,
    Event,
    Good,
    InvalidTrade,
    SessionSettled,
    TradingSession,
)


class MemorySessionRepository:
    def __init__(self) -> None:
        self.records: dict[str, SessionRecord] = {}
        self.reject_save = False

    def add(self, session: TradingSession) -> None:
        self.records[session.session_id] = SessionRecord(deepcopy(session), (), 0)

    def get(self, session_id: str) -> SessionRecord | None:
        record = self.records.get(session_id)
        if record is None:
            return None
        return SessionRecord(deepcopy(record.session), record.events, record.revision)

    def save(
        self, session: TradingSession, events: tuple[Event, ...], expected_revision: int
    ) -> bool:
        record = self.records[session.session_id]
        if self.reject_save or record.revision != expected_revision:
            return False
        self.records[session.session_id] = SessionRecord(
            deepcopy(session), (*record.events, *events), record.revision + 1
        )
        return True


def test_REQ_USECASE_start_trade_advance_and_read_keep_event_history() -> None:
    repository: SessionRepository = MemorySessionRepository()
    session = StartSession(repository, lambda: "session-1").execute()
    buy = BuyGoods(repository).execute(session.session_id, Good.GRAIN, 2)
    sell = SellGoods(repository).execute(session.session_id, Good.GRAIN, 1)
    advance = AdvanceSession(repository)
    events: list[Event] = [buy, sell]
    for _ in range(5):
        events.append(advance.execute(session.session_id))
    settled = advance.execute(session.session_id)
    events.append(settled)

    record = ReadSession(repository).execute(session.session_id)
    assert settled == SessionSettled("session-1", Coins(23))
    assert record.session.settled and record.session.cargo.total == 0
    assert record.events == tuple(events)
    assert record.revision == len(events) == 8


def test_REQ_USECASE_unknown_and_invalid_actions_leave_session_unchanged() -> None:
    repository = MemorySessionRepository()
    session = StartSession(repository, lambda: "session-1").execute()
    before = ReadSession(repository).execute(session.session_id)

    with pytest.raises(SessionNotFound):
        ReadSession(repository).execute("missing")
    with pytest.raises(SessionNotFound):
        BuyGoods(repository).execute("missing", Good.GRAIN, 1)
    with pytest.raises(InvalidTrade):
        BuyGoods(repository).execute(session.session_id, Good.GRAIN, 9)

    assert ReadSession(repository).execute(session.session_id) == before


def test_REQ_USECASE_stale_revision_is_reported_as_a_conflict() -> None:
    repository = MemorySessionRepository()
    session = StartSession(repository, lambda: "session-1").execute()
    repository.reject_save = True

    with pytest.raises(SessionConflict):
        BuyGoods(repository).execute(session.session_id, Good.GRAIN, 1)

    record = ReadSession(repository).execute(session.session_id)
    assert record.session.coins == Coins(20)
    assert record.events == () and record.revision == 0
