# Copyright 2026 TM-59
"""The Django repository against SQLite: persistence, revisions and atomic saves."""

import pytest
from django.db import IntegrityError, connection, connections

from harbor_market.application.use_cases import SessionNotFoundError
from harbor_market.composition.use_cases import build_use_cases
from harbor_market.domain import (
    DAYS,
    Coins,
    Event,
    Good,
    InvalidTradeError,
    SessionSettled,
    TradingSession,
)
from harbor_market.infrastructure.repository import DjangoSessionRepository

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def test_req_persistence_session_and_events_survive_connection_reopen() -> None:
    """REQ-PERSISTENCE: the session and its events survive closing every connection."""
    use_cases = build_use_cases()
    session = use_cases.start.execute()
    events: list[Event] = [use_cases.buy.execute(session.session_id, Good.GRAIN, 2)]
    events.extend(use_cases.advance.execute(session.session_id) for _ in range(5))
    events.append(use_cases.advance.execute(session.session_id))
    assert events[-1] == SessionSettled(session.session_id, Coins(26))

    connections.close_all()
    reopened = build_use_cases().read.execute(session.session_id)
    assert reopened.session == TradingSession(
        session.session_id,
        day=6,
        coins=Coins(26),
        settled=True,
    )
    assert reopened.events == tuple(events)
    assert reopened.revision == len(events)
    assert len(events) == 1 + DAYS  # one buy, five advances, the settlement


def test_req_revision_stale_snapshot_cannot_overwrite_a_committed_trade() -> None:
    """REQ-REVISION: a stale snapshot cannot overwrite a committed trade."""
    repository = DjangoSessionRepository()
    session = TradingSession("session-stale")
    repository.add(session)
    first = repository.get(session.session_id)
    stale = repository.get(session.session_id)
    assert first is not None
    assert stale is not None

    first_event = first.session.buy(Good.GRAIN, 1)
    assert repository.save(first.session, (first_event,), first.revision)
    stale_event = stale.session.buy(Good.GRAIN, 2)
    assert not repository.save(stale.session, (stale_event,), stale.revision)

    stored = repository.get(session.session_id)
    assert stored is not None
    assert stored.session.coins == Coins(17)
    assert stored.revision == 1
    assert stored.events == (first_event,)


def test_req_atomic_failed_event_insert_rolls_back_session_update() -> None:
    """REQ-ATOMIC: a failed event insert rolls back the session update."""
    use_cases = build_use_cases()
    session = use_cases.start.execute()
    with connection.cursor() as cursor:
        cursor.execute(
            """CREATE TRIGGER reject_trade_event BEFORE INSERT ON harbor_market_session_event
               WHEN NEW.event_type = 'trade_executed'
               BEGIN SELECT RAISE(ABORT, 'event rejected'); END"""
        )

    with pytest.raises(IntegrityError, match="event rejected"):
        use_cases.buy.execute(session.session_id, Good.GRAIN, 1)

    record = build_use_cases().read.execute(session.session_id)
    assert record.session.coins == Coins(20)
    assert record.session.cargo.total == 0
    assert record.events == ()
    assert record.revision == 0


def test_req_persistence_unknown_and_invalid_actions_are_no_ops() -> None:
    """REQ-PERSISTENCE: unknown sessions and invalid trades write nothing."""
    use_cases = build_use_cases()
    session = use_cases.start.execute()
    before = use_cases.read.execute(session.session_id)

    with pytest.raises(SessionNotFoundError):
        use_cases.read.execute("missing")
    with pytest.raises(SessionNotFoundError):
        use_cases.sell.execute("missing", Good.GRAIN, 1)
    with pytest.raises(InvalidTradeError):
        use_cases.buy.execute(session.session_id, Good.GRAIN, 9)

    assert use_cases.read.execute(session.session_id) == before
