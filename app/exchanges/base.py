import time
from abc import ABC, abstractmethod

import aiohttp

from app.models import Advertisement


class ExchangeAdapter(ABC):
    name: str

    def __init__(self, session: aiohttp.ClientSession, rows: int = 20, min_interval: float = 1.0):
        self.session = session
        self.rows = rows
        # Don't hit the exchange more often than this; return cached ads instead.
        self.min_interval = min_interval
        self._cache: list[Advertisement] = []
        self._last_fetch = 0.0

    @abstractmethod
    async def get_ads(self, asset: str, fiat: str, side: str | None = None) -> list[Advertisement]:
        """Return ads; `side` is the merchant's side (BUY/SELL), None = both."""
        raise NotImplementedError

    async def fetch(self, asset: str, fiat: str) -> list[Advertisement]:
        now = time.monotonic()
        if self._cache and now - self._last_fetch < self.min_interval:
            return self._cache
        ads = await self.get_ads(asset, fiat)
        self._cache, self._last_fetch = ads, now
        return ads

    async def health_check(self) -> bool:
        try:
            return isinstance(await self.get_ads("USDT", "UAH", "SELL"), list)
        except Exception:
            return False
