import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import aiohttp
import yaml

from app.alerts import TelegramNotifier
from app.analyzer import find_opportunities
from app.env import load_dotenv
from app.exchanges import ADAPTERS
from app.http import DEFAULT_HEADERS
from app.models import Advertisement
from app.storage import Storage
from app.terminal import render_ads, render_header, render_opportunities, render_status

log = logging.getLogger("p2p")


def setup_logging(path: str) -> None:
    logging.basicConfig(
        filename=path, level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def fetch_all(adapters, asset: str, fiat: str) -> tuple[list[Advertisement], dict[str, str]]:
    """Fetch every exchange concurrently; one failing exchange doesn't stop the others."""
    results = await asyncio.gather(
        *(a.fetch(asset, fiat) for a in adapters), return_exceptions=True
    )
    ads, statuses = [], {}
    for adapter, result in zip(adapters, results):
        if isinstance(result, BaseException):
            statuses[adapter.name] = "OFFLINE"
            log.error("%s fetch failed: %r", adapter.name, result)
        else:
            statuses[adapter.name] = f"LIVE ({len(result)})"
            ads.extend(result)
    return ads, statuses


async def main(once: bool = False):
    with Path("config.yaml").open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    load_dotenv()
    setup_logging(config.get("log_file", "p2p-monitor.log"))

    pair = config.get("pair", {})
    asset, fiat = pair.get("asset", "USDT"), pair.get("fiat", "UAH")
    interval = float(config.get("update_interval", 1.0))
    display = config.get("display", {})
    arb = config.get("arbitrage", {})
    filters = config.get("arbitrage_filters", {})
    realistic = config.get("realistic", {})
    signals = config.get("signals", {})
    exchanges_cfg = config.get("exchanges", {})
    storage_cfg = config.get("storage", {})
    alerts_cfg = config.get("alerts", {})

    storage = Storage(storage_cfg.get("path", "p2p.db")) if storage_cfg.get("enabled") else None
    snapshot_every = float(storage_cfg.get("snapshot_interval", 60))
    last_snapshot = 0.0

    async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session:
        adapters = [
            cls(session, rows=int(exchanges_cfg.get("rows", 20)),
                min_interval=float(exchanges_cfg.get("min_interval", 1.0)))
            for key, cls in ADAPTERS.items() if exchanges_cfg.get(key, False)
        ]
        if not adapters:
            print("No exchanges enabled in config.yaml (exchanges: binance/bybit/okx).")
            return

        notifier = None
        if alerts_cfg.get("telegram"):
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
            if token and chat_id:
                notifier = TelegramNotifier(
                    session, token, chat_id,
                    cooldown_seconds=float(alerts_cfg.get("cooldown_seconds", 300)),
                )
            else:
                print("Telegram alerts enabled but TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set.")
                log.warning("Telegram alerts enabled but credentials missing")

        try:
            while True:
                started = time.monotonic()
                try:
                    ads, statuses = await fetch_all(adapters, asset, fiat)
                    render_header(asset, fiat)
                    render_status(statuses)
                    render_ads(ads, asset, fiat, int(display.get("ads_per_side", 10)))
                    opportunities = find_opportunities(
                        ads,
                        min_spread_percent=float(arb.get("min_spread_percent", 0.5)),
                        buy_fee_percent=float(arb.get("buy_fee_percent", 0.0)),
                        sell_fee_percent=float(arb.get("sell_fee_percent", 0.0)),
                        min_net_profit_percent=float(arb.get("min_net_profit_percent", 0.5)),
                        max_opportunities=int(arb.get("max_opportunities", 10)),
                        min_finish_rate=float(filters.get("min_finish_rate", 0.90)),
                        min_order_count=int(filters.get("min_order_count", 50)),
                        safety_buffer_percent=float(realistic.get("safety_buffer_percent", 0.50)),
                        my_payment_methods=config.get("my_payment_methods") or [],
                        same_exchange=bool(arb.get("same_exchange", True)),
                        cross_exchange=bool(arb.get("cross_exchange", True)),
                        transfer_fee_usdt=float(arb.get("transfer_fee_usdt", 0.0)),
                        max_pay_time_minutes=int(filters.get("max_pay_time_minutes", 0)),
                    )
                    signals_found = [
                        x for x in opportunities
                        if x.score >= float(signals.get("min_score", 80))
                        and x.realistic_profit_percent >= float(signals.get("min_net_profit_percent", 2.0))
                        and x.amount >= float(signals.get("min_volume_uah", 10000))
                    ]
                    render_opportunities(signals_found, fiat)

                    if storage:
                        new = storage.save_signals(signals_found)
                        for x in new:
                            log.info("NEW SIGNAL %s %.2f%% %.0f %s", x.key,
                                     x.realistic_profit_percent, x.amount, fiat)
                        if time.monotonic() - last_snapshot >= snapshot_every:
                            storage.save_best_prices(ads)
                            last_snapshot = time.monotonic()
                    if notifier and signals_found:
                        await notifier.notify(signals_found, fiat)

                    elapsed = time.monotonic() - started
                    print(f"\nUpdated: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
                    print(f"Request time: {elapsed:.3f}s")
                    print("Press Ctrl+C to stop.")
                except Exception as exc:
                    log.exception("update failed")
                    print(f"ERROR: {type(exc).__name__}: {exc}")
                if once:
                    break
                await asyncio.sleep(max(0.0, interval - (time.monotonic() - started)))
        finally:
            if storage:
                storage.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
