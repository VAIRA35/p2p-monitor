from app.exchanges.base import ExchangeAdapter
from app.models import Advertisement

class BybitAdapter(ExchangeAdapter):
    name = "BYBIT"

    async def get_ads(self, asset, fiat, side=None) -> list[Advertisement]:
        raise RuntimeError(
            "Bybit P2P endpoint tested in this project requires an API key "
            "and appropriate P2P advertiser permissions."
        )

    async def health_check(self) -> bool:
        return False
