from app.exchanges.base import ExchangeAdapter
from app.models import Advertisement

class OKXAdapter(ExchangeAdapter):
    name = "OKX"

    async def get_ads(self, asset, fiat, side=None) -> list[Advertisement]:
        raise RuntimeError("OKX P2P adapter is not implemented yet.")

    async def health_check(self) -> bool:
        return False
