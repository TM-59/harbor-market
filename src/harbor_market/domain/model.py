"""Trading Session: coins, cargo and quotes, the session aggregate and its events.

Standard library only. No real money, no fractions, no debt.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

STARTING_COINS = 20
CAPACITY = 8


class Good(Enum):
    GRAIN = "grain"
    SALT = "salt"


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class SessionClosed(Exception):
    """A settled session accepts no further action."""


class InvalidTrade(ValueError):
    """The quantity is not a positive whole number, or coins, capacity or cargo do not allow it."""


@dataclass(frozen=True, slots=True)
class Coins:
    """A non-negative whole number of coins."""

    amount: int

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount < 0:
            raise ValueError("coins are a non-negative whole number")


@dataclass(frozen=True, slots=True)
class Cargo:
    """Units held of each good; every unit takes one of eight slots."""

    grain: int = 0
    salt: int = 0

    def __post_init__(self) -> None:
        for units in (self.grain, self.salt):
            if type(units) is not int or units < 0:
                raise ValueError("cargo quantities are non-negative whole numbers")
        if self.total > CAPACITY:
            raise ValueError("cargo holds at most eight units")

    @property
    def total(self) -> int:
        return self.grain + self.salt

    def held(self, good: Good) -> int:
        return self.grain if good is Good.GRAIN else self.salt

    def changed(self, good: Good, units: int) -> Cargo:
        """A new cargo with `units` more (or, when negative, fewer) of one good."""
        if good is Good.GRAIN:
            return Cargo(self.grain + units, self.salt)
        return Cargo(self.grain, self.salt + units)


@dataclass(frozen=True, slots=True)
class Quote:
    """The price per unit of one good on one day; buying and selling share it."""

    good: Good
    price: int

    def __post_init__(self) -> None:
        if not isinstance(self.good, Good):
            raise TypeError("a quote names a good")
        if type(self.price) is not int or self.price < 1:
            raise ValueError("a price is a positive whole number")


Quotes = Mapping[Good, Quote]


def _day(grain: int, salt: int) -> Quotes:
    return MappingProxyType(
        {Good.GRAIN: Quote(Good.GRAIN, grain), Good.SALT: Quote(Good.SALT, salt)}
    )


# The six market days, the same for every session: (grain, salt) price per unit.
MARKET: tuple[Quotes, ...] = (
    _day(3, 5),
    _day(4, 4),
    _day(2, 6),
    _day(5, 3),
    _day(3, 7),
    _day(6, 5),
)
DAYS = len(MARKET)


class CargoValuation:
    """Pure domain service: what the cargo is worth at the given quotes."""

    @staticmethod
    def value(cargo: Cargo, quotes: Quotes) -> Coins:
        return Coins(sum(cargo.held(good) * quotes[good].price for good in Good))


@dataclass(frozen=True, slots=True)
class TradeExecuted:
    session_id: str
    day: int
    side: Side
    good: Good
    quantity: int
    price: int
    coins: Coins
    cargo: Cargo


@dataclass(frozen=True, slots=True)
class DayAdvanced:
    session_id: str
    day: int
    quotes: Quotes


@dataclass(frozen=True, slots=True)
class SessionSettled:
    session_id: str
    coins: Coins


Event = TradeExecuted | DayAdvanced | SessionSettled


@dataclass(slots=True)
class TradingSession:
    """Aggregate: identity, the day, coins, cargo, and whether the session is settled."""

    session_id: str
    day: int = 1
    coins: Coins = Coins(STARTING_COINS)
    cargo: Cargo = Cargo()
    settled: bool = False

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("a session needs an identity")
        if type(self.day) is not int or not 1 <= self.day <= DAYS:
            raise ValueError("the day lies between one and six")
        if not isinstance(self.coins, Coins) or not isinstance(self.cargo, Cargo):
            raise TypeError("a session holds coins and cargo")

    @property
    def quotes(self) -> Quotes:
        return MARKET[self.day - 1]

    def _check(self, good: Good, quantity: int) -> int:
        if self.settled:
            raise SessionClosed("the session is settled")
        if not isinstance(good, Good):
            raise InvalidTrade("grain or salt is required")
        if type(quantity) is not int or quantity < 1:
            raise InvalidTrade("a quantity is a positive whole number")
        return self.quotes[good].price

    def buy(self, good: Good, quantity: int) -> TradeExecuted:
        """Exchange coins for cargo at today's quote. Nothing changes when the trade is invalid."""
        price = self._check(good, quantity)
        cost = price * quantity
        if cost > self.coins.amount:
            raise InvalidTrade("not enough coins")
        if self.cargo.total + quantity > CAPACITY:
            raise InvalidTrade("not enough cargo space")
        self.coins = Coins(self.coins.amount - cost)
        self.cargo = self.cargo.changed(good, quantity)
        return self._trade(Side.BUY, good, quantity, price)

    def sell(self, good: Good, quantity: int) -> TradeExecuted:
        """Exchange cargo for coins at today's quote. Nothing changes when the trade is invalid."""
        price = self._check(good, quantity)
        if quantity > self.cargo.held(good):
            raise InvalidTrade("not enough cargo of that good")
        self.coins = Coins(self.coins.amount + price * quantity)
        self.cargo = self.cargo.changed(good, -quantity)
        return self._trade(Side.SELL, good, quantity, price)

    def _trade(self, side: Side, good: Good, quantity: int, price: int) -> TradeExecuted:
        return TradeExecuted(
            self.session_id, self.day, side, good, quantity, price, self.coins, self.cargo
        )

    def advance(self) -> DayAdvanced | SessionSettled:
        """Go to the next day; from day six, sell what is left at day-six quotes and settle."""
        if self.settled:
            raise SessionClosed("the session is settled")
        if self.day < DAYS:
            self.day += 1
            return DayAdvanced(self.session_id, self.day, self.quotes)
        final = self.coins.amount + CargoValuation.value(self.cargo, self.quotes).amount
        self.coins = Coins(final)
        self.cargo = Cargo()
        self.settled = True
        return SessionSettled(self.session_id, self.coins)
