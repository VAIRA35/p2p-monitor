from abc import ABC, abstractmethod
from app.models import Advertisement

class ExchangeAdapter(ABC):
    name: str

    @abstractmethod
    async def get_ads(self, asset: str, fiat: str, side: str | None = None) -> list[Advertisement]:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError
