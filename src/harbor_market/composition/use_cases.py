from harbor_market.application.ports import SessionRepository
from harbor_market.application.use_cases import (
    AdvanceSession,
    BuyGoods,
    ReadSession,
    SellGoods,
    StartSession,
)
from harbor_market.infrastructure.repository import DjangoSessionRepository


class TradingUseCases:
    def __init__(self, repository: SessionRepository) -> None:
        self.start = StartSession(repository)
        self.read = ReadSession(repository)
        self.buy = BuyGoods(repository)
        self.sell = SellGoods(repository)
        self.advance = AdvanceSession(repository)


def build_use_cases() -> TradingUseCases:
    return TradingUseCases(DjangoSessionRepository())
