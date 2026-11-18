"""Django ORM adapter for the application session repository port."""

from types import MappingProxyType
from typing import cast

from django.db import transaction
from django.db.models import F, Max

from harbor_market.application.ports import SessionRecord
from harbor_market.domain import (
    Cargo,
    Coins,
    DayAdvanced,
    Event,
    Good,
    Quote,
    SessionSettled,
    Side,
    TradeExecuted,
    TradingSession,
)
from harbor_market.infrastructure.models import SessionEventRecord, TradingSessionRecord


class DjangoSessionRepository:
    """Session repository on the Django ORM, with revisions and an event log."""

    def add(self, session: TradingSession) -> None:
        """Insert the session as a new record at revision 0."""
        TradingSessionRecord.objects.create(
            session_id=session.session_id,
            day=session.day,
            coins=session.coins.amount,
            grain=session.cargo.grain,
            salt=session.cargo.salt,
            settled=session.settled,
        )

    def get(self, session_id: str) -> SessionRecord | None:
        """Return the stored session, its events and revision, or None."""
        with transaction.atomic():
            row = TradingSessionRecord.objects.filter(session_id=session_id).first()
            if row is None:
                return None
            session = TradingSession(
                row.session_id,
                day=row.day,
                coins=Coins(row.coins),
                cargo=Cargo(row.grain, row.salt),
                settled=row.settled,
            )
            events = tuple(
                _decode_event(event.event_type, event.payload)
                for event in SessionEventRecord.objects.filter(session=row).order_by("sequence")
            )
            return SessionRecord(session, events, row.revision)

    def save(
        self, session: TradingSession, events: tuple[Event, ...], expected_revision: int
    ) -> bool:
        """Update the record and append events atomically if the revision is unchanged."""
        with transaction.atomic():
            changed = TradingSessionRecord.objects.filter(
                session_id=session.session_id, revision=expected_revision
            ).update(
                day=session.day,
                coins=session.coins.amount,
                grain=session.cargo.grain,
                salt=session.cargo.salt,
                settled=session.settled,
                revision=F("revision") + 1,
            )
            if changed == 0:
                return False
            last_sequence = SessionEventRecord.objects.filter(
                session_id=session.session_id
            ).aggregate(sequence=Max("sequence"))["sequence"]
            next_sequence = (last_sequence or 0) + 1
            event_rows = []
            for offset, event in enumerate(events):
                event_type, payload = _encode_event(event)
                event_rows.append(
                    SessionEventRecord(
                        session_id=session.session_id,
                        sequence=next_sequence + offset,
                        event_type=event_type,
                        payload=payload,
                    )
                )
            SessionEventRecord.objects.bulk_create(event_rows)
        return True


UNKNOWN_EVENT_TYPE = "database contains unknown event type: {}"
INVALID_PAYLOAD = "database contains an invalid event payload"
FIELD_NOT_TEXT = "database event field {} must be text"
FIELD_NOT_INTEGER = "database event field {} must be an integer"


class StoredEventError(TypeError, ValueError):
    """A stored event does not have the shape the repository wrote.

    It is a ValueError (the stored value is wrong) and a TypeError (the value has the
    wrong type), so callers that caught ValueError keep working.
    """


def _encode_event(event: Event) -> tuple[str, dict[str, object]]:
    if isinstance(event, TradeExecuted):
        return "trade_executed", {
            "session_id": event.session_id,
            "day": event.day,
            "side": event.side.value,
            "good": event.good.value,
            "quantity": event.quantity,
            "price": event.price,
            "coins": event.coins.amount,
            "grain": event.cargo.grain,
            "salt": event.cargo.salt,
        }
    if isinstance(event, DayAdvanced):
        return "day_advanced", {
            "session_id": event.session_id,
            "day": event.day,
            "quotes": {good.value: quote.price for good, quote in event.quotes.items()},
        }
    return "session_settled", {
        "session_id": event.session_id,
        "coins": event.coins.amount,
    }


def _decode_event(event_type: str, payload: object) -> Event:
    data = _dict(payload)
    if event_type == "trade_executed":
        return TradeExecuted(
            _str(data, "session_id"),
            _int(data, "day"),
            Side(_str(data, "side")),
            Good(_str(data, "good")),
            _int(data, "quantity"),
            _int(data, "price"),
            Coins(_int(data, "coins")),
            Cargo(_int(data, "grain"), _int(data, "salt")),
        )
    if event_type == "day_advanced":
        prices = _dict(data["quotes"])
        quotes = {good: Quote(good, _int(prices, good.value)) for good in Good}
        return DayAdvanced(
            _str(data, "session_id"),
            _int(data, "day"),
            MappingProxyType(quotes),
        )
    if event_type == "session_settled":
        return SessionSettled(_str(data, "session_id"), Coins(_int(data, "coins")))
    raise StoredEventError(UNKNOWN_EVENT_TYPE.format(event_type))


def _dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise StoredEventError(INVALID_PAYLOAD)
    return cast("dict[str, object]", value)


def _str(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise StoredEventError(FIELD_NOT_TEXT.format(key))
    return value


def _int(data: dict[str, object], key: str) -> int:
    value = data[key]
    if type(value) is not int:
        raise StoredEventError(FIELD_NOT_INTEGER.format(key))
    return value
