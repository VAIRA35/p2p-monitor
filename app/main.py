import asyncio
from datetime import datetime
from pathlib import Path
import yaml
from app.exchanges.binance import BinanceAdapter
from app.analyzer import find_opportunities
from app.terminal import render_ads, render_opportunities

async def main():
    with Path("config.yaml").open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    pair = config.get("pair", {})
    asset, fiat = pair.get("asset", "USDT"), pair.get("fiat", "UAH")
    interval = float(config.get("update_interval", 1.0))
    display = config.get("display", {})
    arb = config.get("arbitrage", {})
    filters = config.get("arbitrage_filters", {})
    realistic = config.get("realistic", {})
    signals = config.get("signals", {})
    exchange = BinanceAdapter()

    while True:
        started = datetime.now()
        try:
            ads = await exchange.get_ads(asset=asset, fiat=fiat)
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
            )
            signals_found = [
                x for x in opportunities
                if x.score >= float(signals.get("min_score", 80))
                and x.realistic_profit_percent >= float(signals.get("min_net_profit_percent", 2.0))
                and x.amount >= float(signals.get("min_volume_uah", 10000))
            ]
            render_opportunities(signals_found, fiat)
            elapsed = (datetime.now() - started).total_seconds()
            print(f"\nUpdated: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            print(f"Request time: {elapsed:.3f}s")
            print("Press Ctrl+C to stop.")
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
        await asyncio.sleep(max(0.0, interval))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
