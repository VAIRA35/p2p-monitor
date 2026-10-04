import time
from abc import ABC, abstractmethod

import aiohttp

from app.models import Advertisement


class RateLimited(Exception):
    """Exchange is in back-off after HTTP 429."""


class ExchangeAdapter(ABC):
    name: str

    def __init__(self, session: aiohttp.ClientSession, rows: int = 20, min_interval: float = 1.0):
        self.session = session
        self.rows = rows
        # Don't hit the exchange more often than this; return cached ads instead.
        self.min_interval = min_interval
        self._cache: list[Advertisement] = []
        self._last_fetch = 0.0
        self._cooldown_until = 0.0

    RATE_LIMIT_COOLDOWN = 30.0  # seconds to back off after HTTP 429

    @property
    def cooling_down(self) -> bool:
        return time.monotonic() < self._cooldown_until

    @abstractmethod
    async def get_ads(self, asset: str, fiat: str, side: str | None = None) -> list[Advertisement]:
        """Return ads; `side` is the merchant's side (BUY/SELL), None = both."""
        raise NotImplementedError

    async def fetch(self, asset: str, fiat: str) -> list[Advertisement]:
        now = time.monotonic()
        if self._cache and now - self._last_fetch < self.min_interval:
            return self._cache
        if now < self._cooldown_until:
            raise RateLimited(f"{self.name} rate limited, retry in {self._cooldown_until - now:.0f}s")
        try:
            ads = await self.get_ads(asset, fiat)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 429:
                self._cooldown_until = now + self.RATE_LIMIT_COOLDOWN
            raise
        self._cache, self._last_fetch = ads, now
        return ads

    async def health_check(self) -> bool:
        try:
            return isinstance(await self.get_ads("USDT", "UAH", "SELL"), list)
        except Exception:
            return False
