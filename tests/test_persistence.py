import pytest
from django.db import IntegrityError, connection, connections

from harbor_market.application.use_cases import SessionNotFound
from harbor_market.composition.use_cases import build_use_cases
from harbor_market.domain import Coins, Event, Good, InvalidTrade, SessionSettled, TradingSession
from harbor_market.infrastructure.repository import DjangoSessionRepository

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def test_REQ_PERSISTENCE_session_and_events_survive_connection_reopen() -> None:
    use_cases = build_use_cases()
    session = use_cases.start.execute()
    events: list[Event] = [use_cases.buy.execute(session.session_id, Good.GRAIN, 2)]
    for _ in range(5):
        events.append(use_cases.advance.execute(session.session_id))
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
    assert reopened.revision == len(events) == 7


def test_REQ_REVISION_stale_snapshot_cannot_overwrite_a_committed_trade() -> None:
    repository = DjangoSessionRepository()
    session = TradingSession("session-stale")
    repository.add(session)
    first = repository.get(session.session_id)
    stale = repository.get(session.session_id)
    assert first is not None and stale is not None

    first_event = first.session.buy(Good.GRAIN, 1)
    assert repository.save(first.session, (first_event,), first.revision)
    stale_event = stale.session.buy(Good.GRAIN, 2)
    assert not repository.save(stale.session, (stale_event,), stale.revision)

    stored = repository.get(session.session_id)
    assert stored is not None
    assert stored.session.coins == Coins(17)
    assert stored.revision == 1 and stored.events == (first_event,)


def test_REQ_ATOMIC_failed_event_insert_rolls_back_session_update() -> None:
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
    assert record.events == () and record.revision == 0


def test_REQ_PERSISTENCE_unknown_and_invalid_actions_are_no_ops() -> None:
    use_cases = build_use_cases()
    session = use_cases.start.execute()
    before = use_cases.read.execute(session.session_id)

    with pytest.raises(SessionNotFound):
        use_cases.read.execute("missing")
    with pytest.raises(SessionNotFound):
        use_cases.sell.execute("missing", Good.GRAIN, 1)
    with pytest.raises(InvalidTrade):
        use_cases.buy.execute(session.session_id, Good.GRAIN, 9)

    assert use_cases.read.execute(session.session_id) == before
