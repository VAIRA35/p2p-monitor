from app.models import Advertisement
from app.analyzer.arbitrage import ArbitrageOpportunity


def _ad_line(a: Advertisement) -> str:
    fixed = "F" if a.is_fixed_amount else " "
    return (f"{a.exchange:8} {a.price:10.2f} {a.available:10.2f} "
            f"{a.min_amount:8.0f}-{a.max_amount:8.0f}{fixed} "
            f"{a.merchant[:18]:18} {a.finish_rate_percent:5.1f}% "
            f"{a.month_order_count:5} ord {a.pay_time_limit:3}m")


def render_status(statuses: dict[str, str]) -> None:
    print("  ".join(f"{name}: {state}" for name, state in statuses.items()))


def render_ads(ads: list[Advertisement], asset: str, fiat: str, ads_per_side: int = 10):
    sell = sorted([a for a in ads if a.is_sell()], key=lambda a: a.price)[:ads_per_side]
    buy = sorted([a for a in ads if a.is_buy()], key=lambda a: a.price, reverse=True)[:ads_per_side]
    print(f"Advertisements: {len(ads)}   (F = fixed amount, m = pay time limit)\n")
    print("SELL ADS (merchant sells -> we buy)")
    for a in sell:
        print(_ad_line(a))
    print("\nBUY ADS (merchant buys -> we sell)")
    for a in buy:
        print(_ad_line(a))


def render_header(asset: str, fiat: str) -> None:
    print("\033[2J\033[H", end="")
    print(f"=== P2P MONITOR {asset}/{fiat} ===")


def render_opportunities(items: list[ArbitrageOpportunity], fiat: str):
    print("\n=== ARBITRAGE SIGNALS ===")
    if not items:
        print("No suitable opportunities.")
        return
    for i, x in enumerate(items, 1):
        route = f"{x.buy.exchange} -> {x.sell.exchange}" if x.cross_exchange else x.buy.exchange
        print(f"#{i} SCORE {x.score:.1f} | {route} | REALISTIC PROFIT "
              f"{x.realistic_profit:,.2f} {fiat} ({x.realistic_profit_percent:.2f}%)")
        print(f"    BUY {x.buy.price:.2f} -> SELL {x.sell.price:.2f} | "
              f"SPREAD {x.spread_percent:.2f}% | VOLUME {x.amount:,.0f} {fiat} | "
              f"LOCK-UP <= {x.lockup_minutes}m")
        extra = f" | TRANSFER FEE {x.transfer_fee_usdt} USDT" if x.cross_exchange else ""
        print(f"    PAY: {', '.join(x.buy_payment_methods)} -> "
              f"RECEIVE: {', '.join(x.sell_payment_methods)}{extra}")
