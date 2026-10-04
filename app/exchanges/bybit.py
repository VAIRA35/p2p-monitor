import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from app.exchanges.base import ExchangeAdapter
from app.http import request_json
from app.models import Advertisement

log = logging.getLogger(__name__)


class BybitAdapter(ExchangeAdapter):
    """Public P2P endpoint used by bybit.com (no API key needed)."""

    name = "BYBIT"
    URL = "https://api2.bybit.com/fiat/otc/item/online"
    PAYMENTS_URL = "https://api2.bybit.com/fiat/otc/configuration/queryAllPaymentList"
    # Request/item side: "1" = merchant sells (we buy), "0" = merchant buys (we sell).
    REQUEST_SIDE = {"SELL": "1", "BUY": "0"}
    ITEM_SIDE = {1: "SELL", 0: "BUY"}
    # The payment list is ~11 s to download, so keep it on disk for a day.
    PAYMENTS_CACHE = Path("cache/bybit_payments.json")
    PAYMENTS_CACHE_TTL = 24 * 3600

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._payment_names: dict[str, str] | None = None
        self._payment_lock = asyncio.Lock()

    async def _load_payment_names(self) -> dict[str, str]:
        async with self._payment_lock:  # both sides start at once; load the list only once
            if self._payment_names is not None:
                return self._payment_names
            cache = self.PAYMENTS_CACHE
            if cache.exists() and time.time() - cache.stat().st_mtime < self.PAYMENTS_CACHE_TTL:
                try:
                    self._payment_names = json.loads(cache.read_text(encoding="utf-8"))
                    return self._payment_names
                except (OSError, ValueError) as exc:
                    log.warning("Bybit payment cache unreadable: %r", exc)
            try:
                data = await request_json(
                    self.session, "POST", self.PAYMENTS_URL, json={}, timeout=30.0
                )
                items = (data.get("result") or {}).get("paymentConfigVo") or []
                self._payment_names = {
                    str(x.get("paymentType")): x.get("paymentName", "") for x in items
                }
                cache.parent.mkdir(exist_ok=True)
                cache.write_text(json.dumps(self._payment_names, ensure_ascii=False),
                                 encoding="utf-8")
            except Exception as exc:
                # Retry on the next fetch; show raw ids meanwhile.
                log.warning("Bybit payment list failed: %r", exc)
                return {}
            return self._payment_names

    async def _fetch_side(self, asset: str, fiat: str, merchant_side: str) -> list[Advertisement]:
        payload = {
            "userId": "", "tokenId": asset, "currencyId": fiat, "payment": [],
            "side": self.REQUEST_SIDE[merchant_side], "size": str(self.rows), "page": "1",
            "amount": "", "authMaker": False, "canTrade": False,
        }
        data, names = await asyncio.gather(
            request_json(self.session, "POST", self.URL, json=payload),
            self._load_payment_names(),
        )
        if data.get("ret_code") != 0:
            raise RuntimeError(f"Bybit error {data.get('ret_code')}: {data.get('ret_msg')}")

        result = []
        for item in (data.get("result") or {}).get("items") or []:
            payments = [names.get(str(p), f"bybit:{p}") for p in item.get("payments") or []]
            result.append(Advertisement(
                exchange=self.name,
                ad_id=str(item.get("id", "")),
                asset=item.get("tokenId", asset),
                fiat=item.get("currencyId", fiat),
                side=self.ITEM_SIDE.get(item.get("side"), merchant_side),
                price=float(item.get("price", 0) or 0),
                available=float(item.get("lastQuantity", 0) or 0),
                min_amount=float(item.get("minAmount", 0) or 0),
                max_amount=float(item.get("maxAmount", 0) or 0),
                merchant=item.get("nickName", ""),
                user_type=item.get("userType", ""),
                payment_methods=payments,
                month_order_count=int(item.get("recentOrderNum", 0) or 0),
                month_finish_rate=float(item.get("recentExecuteRate", 0) or 0) / 100,
                pay_time_limit=int(item.get("paymentPeriod", 0) or 0),
                remark=item.get("remark") or "",
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
