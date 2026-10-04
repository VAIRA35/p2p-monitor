import asyncio
from datetime import datetime, timezone

from app.exchanges.base import ExchangeAdapter
from app.http import request_json
from app.models import Advertisement


class OKXAdapter(ExchangeAdapter):
    """Public P2P endpoint used by okx.com (no API key needed)."""

    name = "OKX"
    URL = "https://www.okx.com/v3/c2c/tradingOrders/books"

    async def _fetch_side(self, asset: str, fiat: str, merchant_side: str) -> list[Advertisement]:
        # OKX `side` is the merchant's side: side=sell -> merchant sells, we buy.
        side = merchant_side.lower()
        params = {
            "quoteCurrency": fiat.lower(), "baseCurrency": asset.lower(), "side": side,
            "paymentMethod": "all", "userType": "all", "showTrade": "false",
            "showFollow": "false", "showAlreadyTraded": "false",
            "isAbleFilter": "false", "receivingAds": "false",
        }
        data = await request_json(self.session, "GET", self.URL, params=params)
        if str(data.get("code")) != "0":
            raise RuntimeError(f"OKX error {data.get('code')}: {data.get('msg')}")

        result = []
        for item in ((data.get("data") or {}).get(side) or [])[:self.rows]:
            result.append(Advertisement(
                exchange=self.name,
                ad_id=str(item.get("id", "")),
                asset=str(item.get("baseCurrency", asset)).upper(),
                fiat=str(item.get("quoteCurrency", fiat)).upper(),
                side=str(item.get("side", side)).upper(),
                price=float(item.get("price", 0) or 0),
                available=float(item.get("availableAmount", 0) or 0),
                min_amount=float(item.get("quoteMinAmountPerOrder", 0) or 0),
                max_amount=float(item.get("quoteMaxAmountPerOrder", 0) or 0),
                merchant=item.get("nickName", ""),
                user_type=item.get("creatorType", ""),
                payment_methods=list(item.get("paymentMethods") or []),
                month_order_count=int(item.get("completedOrderQuantity", 0) or 0),
                month_finish_rate=float(item.get("completedRate", 0) or 0),
                pay_time_limit=int(item.get("paymentTimeoutMinutes", 0) or 0),
                updated_at=datetime.now(timezone.utc),
            ))
        return result

    async def get_ads(self, asset="USDT", fiat="UAH", side=None):
        if side:
            return await self._fetch_side(asset, fiat, side.upper())
        sell_ads, buy_ads = await asyncio.gather(
            self._fetch_side(asset, fiat, "SELL"),
            self._fetch_side(asset, fiat, "BUY"),
        )
        return sell_ads + buy_ads
