"""Pure rules of the Trading Session. No Django object is touched here."""

import copy
from functools import cache

import pytest

from harbor_market.domain import (
    CAPACITY,
    DAYS,
    MARKET,
    STARTING_COINS,
    Cargo,
    CargoValuation,
    Coins,
    DayAdvanced,
    Good,
    InvalidTrade,
    Quote,
    SessionClosed,
    SessionSettled,
    Side,
    TradeExecuted,
    TradingSession,
)

GRAIN, SALT = Good.GRAIN, Good.SALT
# (grain, salt) per day, written by hand: the committed six-day table
PRICES = [(3, 5), (4, 4), (2, 6), (5, 3), (3, 7), (6, 5)]


def test_REQ_VALUE_coins_and_quotes_are_whole_and_bounded() -> None:
    assert Coins(0).amount == 0
    for bad in (-1, 1.5, "3", None, True):
        with pytest.raises(ValueError):
            Coins(bad)  # type: ignore[arg-type]
    for bad in (0, -2, 1.0, "4"):
        with pytest.raises(ValueError):
            Quote(GRAIN, bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Quote("grain", 3)  # type: ignore[arg-type]
    with pytest.raises(AttributeError):
        Coins(3).amount = 4  # type: ignore[misc]


def test_REQ_VALUE_cargo_is_immutable_and_holds_eight() -> None:
    cargo = Cargo(3, 5)
    assert (cargo.total, cargo.held(GRAIN), cargo.held(SALT)) == (8, 3, 5)
    assert cargo.changed(GRAIN, -2) == Cargo(1, 5) and cargo == Cargo(3, 5)
    for bad in ((9, 0), (5, 4), (-1, 0), (0, -1), (1.0, 0), ("1", 0)):
        with pytest.raises(ValueError):
            Cargo(*bad)
    with pytest.raises(ValueError):
        cargo.changed(SALT, 1)


def test_REQ_VALUE_market_table_and_valuation() -> None:
    assert DAYS == 6 and (STARTING_COINS, CAPACITY) == (20, 8)
    assert [(q[GRAIN].price, q[SALT].price) for q in MARKET] == PRICES
    assert CargoValuation.value(Cargo(2, 3), MARKET[0]) == Coins(2 * 3 + 3 * 5)
    assert CargoValuation.value(Cargo(), MARKET[5]) == Coins(0)
    with pytest.raises(TypeError):
        MARKET[0][GRAIN] = Quote(GRAIN, 1)  # type: ignore[index]


def test_REQ_TRADE_exact_balances_of_the_documented_shape() -> None:
    session = TradingSession("s1")
    assert (session.day, session.coins, session.cargo, session.settled) == (
        1,
        Coins(20),
        Cargo(),
        False,
    )
    bought = session.buy(GRAIN, 4)  # day one: grain at three
    assert bought == TradeExecuted("s1", 1, Side.BUY, GRAIN, 4, 3, Coins(8), Cargo(4, 0))
    assert session.advance() == DayAdvanced("s1", 2, MARKET[1])
    sold = session.sell(GRAIN, 2)  # day two: grain at four
    assert sold == TradeExecuted("s1", 2, Side.SELL, GRAIN, 2, 4, Coins(16), Cargo(2, 0))
    assert (session.coins, session.cargo) == (Coins(16), Cargo(2, 0))


def test_REQ_TRADE_several_trades_a_day_and_both_goods() -> None:
    session = TradingSession("s2")
    session.buy(GRAIN, 2)
    session.buy(SALT, 2)
    session.sell(GRAIN, 1)
    assert (session.coins, session.cargo, session.day) == (Coins(20 - 6 - 10 + 3), Cargo(1, 2), 1)
    # buying and selling at the same quote on the same day returns to the start
    again = TradingSession("s2b")
    again.buy(SALT, 4)
    again.sell(SALT, 4)
    assert (again.coins, again.cargo) == (Coins(20), Cargo())


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2", None, True])
def test_REQ_TRADE_quantities_are_positive_whole_numbers(quantity: object) -> None:
    session = TradingSession("s3")
    session.buy(GRAIN, 1)
    before = copy.deepcopy(session)
    for action in (session.buy, session.sell):
        with pytest.raises(InvalidTrade):
            action(GRAIN, quantity)  # type: ignore[arg-type]
    assert session == before


def test_REQ_TRADE_no_overspending_no_overloading_no_short_selling() -> None:
    session = TradingSession("s4")
    before = copy.deepcopy(session)
    with pytest.raises(InvalidTrade, match="coins"):
        session.buy(SALT, 5)  # 25 coins needed, 20 held
    with pytest.raises(InvalidTrade, match="coins"):
        session.buy(GRAIN, 9)  # nine units: over the coins, and always over capacity
    with pytest.raises(InvalidTrade, match="cargo"):
        session.sell(GRAIN, 1)  # nothing held
    with pytest.raises(InvalidTrade):
        session.buy("grain", 1)  # type: ignore[arg-type]
    assert session == before
    session.buy(GRAIN, 6)  # 18 coins, six slots
    with pytest.raises(InvalidTrade, match="coins"):
        session.buy(GRAIN, 1)  # two coins left
    rich = TradingSession("s5", coins=Coins(100))
    rich.buy(GRAIN, 8)
    snapshot = copy.deepcopy(rich)
    with pytest.raises(InvalidTrade, match="space"):
        rich.buy(SALT, 1)  # coins allow it, the hold does not
    with pytest.raises(InvalidTrade, match="cargo"):
        rich.sell(GRAIN, 9)
    assert rich == snapshot
    assert rich.sell(GRAIN, 8).cargo == Cargo()  # exactly what is held can be sold


def test_REQ_DAY_six_days_then_settlement() -> None:
    session = TradingSession("s6")
    events = [session.advance() for _ in range(5)]
    assert [event.day for event in events if isinstance(event, DayAdvanced)] == [2, 3, 4, 5, 6]
    assert all(
        event.quotes is MARKET[event.day - 1] for event in events if isinstance(event, DayAdvanced)
    )
    assert session.day == 6 and not session.settled
    session.buy(GRAIN, 3)  # day six: grain at six
    assert session.advance() == SessionSettled("s6", Coins(20))  # sold back at the same quote
    assert (session.settled, session.cargo, session.day) == (True, Cargo(), 6)


def test_REQ_DAY_final_liquidation_uses_day_six_quotes() -> None:
    session = TradingSession("s7", day=5, coins=Coins(4), cargo=Cargo(2, 3))
    session.advance()
    settled = session.advance()
    assert settled == SessionSettled("s7", Coins(4 + 2 * 6 + 3 * 5))
    assert session.coins == Coins(31) and session.cargo == Cargo()


def test_REQ_DAY_settled_sessions_reject_every_action() -> None:
    session = TradingSession("s8", day=6)
    session.advance()
    before = copy.deepcopy(session)
    for action in (lambda: session.buy(GRAIN, 1), lambda: session.sell(GRAIN, 1), session.advance):
        with pytest.raises(SessionClosed):
            action()
    assert session == before


def test_REQ_DAY_session_creation_is_validated() -> None:
    with pytest.raises(ValueError):
        TradingSession("")
    for day in (0, 7, 1.0, "1"):
        with pytest.raises(ValueError):
            TradingSession("s", day=day)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        TradingSession("s", coins=20)  # type: ignore[arg-type]
    a, b = TradingSession("a"), TradingSession("b")
    a.buy(GRAIN, 1)
    assert b.coins == Coins(20) and b.cargo == Cargo()  # sessions do not share state


def best_possible() -> int:
    """Largest settled coins, by dynamic programming over (day, coins, grain, salt).

    Written independently of the domain: buying and selling share a quote, so within a day only
    the day's wealth and the cargo carried out of it matter.
    """

    @cache
    def best(day: int, wealth: int) -> int:
        if day == len(PRICES) - 1:
            return wealth
        grain_price, salt_price = PRICES[day]
        next_grain, next_salt = PRICES[day + 1]
        top = 0
        for grain in range(CAPACITY + 1):
            for salt in range(CAPACITY + 1 - grain):
                cost = grain * grain_price + salt * salt_price
                if cost <= wealth:
                    carried = wealth - cost + grain * next_grain + salt * next_salt
                    top = max(top, best(day + 1, carried))
        return top

    return best(0, STARTING_COINS)


def test_REQ_DAY_best_plan_reaches_the_computed_optimum_through_the_domain() -> None:
    assert best_possible() == 118
    # one plan that reaches it, played through the aggregate
    session = TradingSession("best")
    session.buy(GRAIN, 6)  # day 1: 6 grain at 3 -> 2 coins
    session.advance()
    session.sell(GRAIN, 6)  # day 2: at 4 -> 26 coins
    session.buy(SALT, 6)  # salt at 4 -> 2 coins
    session.advance()
    session.sell(SALT, 6)  # day 3: at 6 -> 38 coins
    session.buy(GRAIN, 8)  # grain at 2 -> 22 coins
    session.advance()
    session.sell(GRAIN, 8)  # day 4: at 5 -> 62 coins
    session.buy(SALT, 8)  # salt at 3 -> 38 coins
    session.advance()
    session.sell(SALT, 8)  # day 5: at 7 -> 94 coins
    session.buy(GRAIN, 8)  # grain at 3 -> 70 coins
    session.advance()
    settled = session.advance()  # day 6: grain at 6 -> 118 coins
    assert settled == SessionSettled("best", Coins(118))
    idle = TradingSession("idle")
    for _ in range(5):
        idle.advance()
    assert idle.advance() == SessionSettled("idle", Coins(20))  # doing nothing keeps the start


def test_REQ_DAY_same_actions_give_the_same_session() -> None:
    runs = []
    for _ in range(2):
        session = TradingSession("replay")
        session.buy(SALT, 2)
        session.advance()
        session.sell(SALT, 1)
        session.buy(GRAIN, 3)
        runs.append((session.day, session.coins, session.cargo, session.settled))
    assert runs[0] == runs[1] == (2, Coins(2), Cargo(3, 1), False)
