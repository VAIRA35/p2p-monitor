from app.models import Advertisement
from app.analyzer.arbitrage import ArbitrageOpportunity

def render_ads(ads: list[Advertisement], asset: str, fiat: str, ads_per_side: int = 10):
    sell = sorted([a for a in ads if a.side.upper() == "SELL"], key=lambda a: a.price)[:ads_per_side]
    buy = sorted([a for a in ads if a.side.upper() == "BUY"], key=lambda a: a.price, reverse=True)[:ads_per_side]
    print("\033[2J\033[H", end="")
    print(f"=== P2P MONITOR {asset}/{fiat} ===")
    print(f"Advertisements: {len(ads)}\n")
    print("SELL ADS (merchant sells -> we buy)")
    for a in sell:
        print(f"{a.exchange:8} {a.price:10.2f} {a.available:10.2f} "
              f"{a.min_amount:8.0f}-{a.max_amount:8.0f} "
              f"{a.merchant[:18]:18} {a.finish_rate_percent:5.1f}% "
              f"{a.month_order_count:5} orders")
    print("\nBUY ADS (merchant buys -> we sell)")
    for a in buy:
        print(f"{a.exchange:8} {a.price:10.2f} {a.available:10.2f} "
              f"{a.min_amount:8.0f}-{a.max_amount:8.0f} "
              f"{a.merchant[:18]:18} {a.finish_rate_percent:5.1f}% "
              f"{a.month_order_count:5} orders")

def render_opportunities(items: list[ArbitrageOpportunity], fiat: str):
    print("\n=== ARBITRAGE SIGNALS ===")
    if not items:
        print("No suitable opportunities.")
        return
    for i, x in enumerate(items, 1):
        print(f"#{i} SCORE {x.score:.1f} | REALISTIC PROFIT {x.realistic_profit:,.2f} {fiat}")
        print(f"    BUY {x.buy.price:.2f} -> SELL {x.sell.price:.2f} | "
              f"SPREAD {x.spread_percent:.2f}% | VOLUME {x.amount:,.0f} {fiat}")
        print(f"    PAYMENT: {', '.join(x.payment_methods)}")
