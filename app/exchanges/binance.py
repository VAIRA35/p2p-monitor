import asyncio
from datetime import datetime, timezone
import aiohttp
from app.exchanges.base import ExchangeAdapter
from app.models import Advertisement

class BinanceAdapter(ExchangeAdapter):
    name = "BINANCE"
    URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    HEADERS = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/139 Safari/537.36",
        "Accept": "application/json",
    }

    async def _fetch_side(self, session, asset, fiat, trade_type):
        payload = {
            "asset": asset, "fiat": fiat, "page": 1, "rows": 20,
            "tradeType": trade_type, "transAmount": "", "payTypes": [],
            "publisherType": None,
        }
        async with session.post(self.URL, json=payload,
                                timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            data = await response.json()

        result = []
        for item in data.get("data", []):
            adv = item.get("adv", {})
            advertiser = item.get("advertiser", {})
            side = str(adv.get("tradeType", trade_type)).upper()
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
                side=side,
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
                updated_at=datetime.now(timezone.utc),
            ))
        return result

    async def get_ads(self, asset="USDT", fiat="UAH", side=None):
        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            if side:
                requested = side.upper()
                ads = await self._fetch_side(session, asset, fiat, requested)
                return [ad for ad in ads if ad.side.upper() == requested]
            buy_task = self._fetch_side(session, asset, fiat, "BUY")
            sell_task = self._fetch_side(session, asset, fiat, "SELL")
            buy_ads, sell_ads = await asyncio.gather(buy_task, sell_task)
        return buy_ads + sell_ads

    async def health_check(self):
        try:
            return isinstance(await self.get_ads("USDT", "UAH", "BUY"), list)
        except Exception:
            return False
