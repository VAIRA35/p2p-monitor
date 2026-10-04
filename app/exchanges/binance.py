import asyncio
from datetime import datetime, timezone

from app.exchanges.base import ExchangeAdapter
from app.http import request_json
from app.models import Advertisement


class BinanceAdapter(ExchangeAdapter):
    name = "BINANCE"
    URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    # Request tradeType is the USER's side: tradeType=BUY returns merchant SELL ads.
    REQUEST_TYPE = {"SELL": "BUY", "BUY": "SELL"}

    async def _fetch_side(self, asset: str, fiat: str, merchant_side: str) -> list[Advertisement]:
        payload = {
            "asset": asset, "fiat": fiat, "page": 1, "rows": self.rows,
            "tradeType": self.REQUEST_TYPE[merchant_side], "transAmount": "",
            "payTypes": [], "publisherType": None,
        }
        data = await request_json(self.session, "POST", self.URL, json=payload)

        result = []
        for item in data.get("data") or []:
            adv = item.get("adv", {})
            advertiser = item.get("advertiser", {})
            payments = []
            for method in adv.get("tradeMethods", []):
                name = (method.get("tradeMethodName")
                        or method.get("tradeMethodShortName")
                        or method.get("identifier"))
                if name:
                    payments.append(name)

            result.append(Advertisement(
                exchange=self.name,
                ad_id=str(adv.get("advNo", "")),
                asset=adv.get("asset", asset),
                fiat=adv.get("fiatUnit", fiat),
                side=str(adv.get("tradeType", merchant_side)).upper(),
                price=float(adv.get("price", 0) or 0),
                available=float(adv.get("tradableQuantity", 0) or 0),
                min_amount=float(adv.get("minSingleTransAmount", 0) or 0),
                max_amount=float(adv.get(
                    "dynamicMaxSingleTransAmount",
                    adv.get("maxSingleTransAmount", 0),
                ) or 0),
                merchant=advertiser.get("nickName", ""),
                user_type=advertiser.get("userType", ""),
                payment_methods=payments,
                month_order_count=int(advertiser.get("monthOrderCount", 0) or 0),
                month_finish_rate=float(advertiser.get("monthFinishRate", 0) or 0),
                positive_rate=float(advertiser.get("positiveRate", 0) or 0),
                pay_time_limit=int(adv.get("payTimeLimit", 0) or 0),
                remark=adv.get("remarks") or "",
                updated_at=datetime.now(timezone.utc),
            ))
        return result

    async def get_ads(self, asset="USDT", fiat="UAH", side=None):
        if side:
            requested = side.upper()
            ads = await self._fetch_side(asset, fiat, requested)
            return [ad for ad in ads if ad.side == requested]
        sell_ads, buy_ads = await asyncio.gather(
            self._fetch_side(asset, fiat, "SELL"),
            self._fetch_side(asset, fiat, "BUY"),
        )
        return sell_ads + buy_ads
