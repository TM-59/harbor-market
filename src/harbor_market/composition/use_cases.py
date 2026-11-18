# Copyright 2026 TM-59
"""Wire the trading use cases to the Django repository."""

from typing import TYPE_CHECKING

from harbor_market.application.use_cases import (
    AdvanceSession,
    BuyGoods,
    ReadSession,
    SellGoods,
    StartSession,
)
from harbor_market.infrastructure.repository import DjangoSessionRepository

if TYPE_CHECKING:
    from harbor_market.application.ports import SessionRepository


class TradingUseCases:
    """The five trading use cases sharing one repository."""

    def __init__(self, repository: SessionRepository) -> None:
        """Build every use case on `repository`."""
        self.start = StartSession(repository)
        self.read = ReadSession(repository)
        self.buy = BuyGoods(repository)
        self.sell = SellGoods(repository)
        self.advance = AdvanceSession(repository)


def build_use_cases() -> TradingUseCases:
    """Wire the use cases to the Django repository."""
    return TradingUseCases(DjangoSessionRepository())
