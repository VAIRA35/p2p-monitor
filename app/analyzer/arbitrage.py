from dataclasses import dataclass
from app.models import Advertisement

@dataclass(slots=True)
class ArbitrageOpportunity:
    buy: Advertisement
    sell: Advertisement
    amount: float
    usdt_amount: float
    spread_percent: float
    gross_profit: float
    buy_fee: float
    sell_fee: float
    net_profit: float
    net_profit_percent: float
    safety_buffer: float
    realistic_profit: float
    realistic_profit_percent: float
    payment_methods: list[str]
    score: float = 0.0

def _payments(ad):
    return {x.strip().lower() for x in ad.payment_methods if x and x.strip()}

def _score(buy, sell, profit_pct, amount, payments):
    profit = min(max(profit_pct, 0) / 3 * 35, 35)
    finish = (buy.month_finish_rate + sell.month_finish_rate) / 2 * 25
    liquidity = min(amount / 100000 * 15, 15)
    orders = (buy.month_order_count + sell.month_order_count) / 2
    history = min(orders / 1000 * 15, 15)
    payment = 10 if payments else 0
    return round(min(profit + finish + liquidity + history + payment, 100), 1)

def find_opportunities(
    ads, min_spread_percent=0.5, buy_fee_percent=0.0,
    sell_fee_percent=0.0, min_net_profit_percent=0.5,
    max_opportunities=10, min_finish_rate=0.90,
    min_order_count=50, safety_buffer_percent=0.50,
):
    # Merchant SELL = we buy USDT.
    buy_ads = [a for a in ads if a.side.upper() == "SELL" and a.price > 0
               and a.month_finish_rate >= min_finish_rate
               and a.month_order_count >= min_order_count]
    # Merchant BUY = we sell USDT.
    sell_ads = [a for a in ads if a.side.upper() == "BUY" and a.price > 0
                and a.month_finish_rate >= min_finish_rate
                and a.month_order_count >= min_order_count]

    result = []
    for buy in buy_ads:
        for sell in sell_ads:
            if buy.price >= sell.price:
                continue
            payments = _payments(buy) & _payments(sell)
            if not payments:
                continue

            amount = min(
                buy.available * buy.price, buy.max_amount,
                sell.available * sell.price, sell.max_amount,
            )
            if amount < max(buy.min_amount, sell.min_amount):
                continue

            usdt = amount / buy.price
            revenue = usdt * sell.price
            spread = (sell.price - buy.price) / buy.price * 100
            if spread < min_spread_percent:
                continue

            gross = revenue - amount
            buy_fee = amount * buy_fee_percent / 100
            sell_fee = revenue * sell_fee_percent / 100
            net = gross - buy_fee - sell_fee
            net_pct = net / amount * 100
            if net_pct < min_net_profit_percent:
                continue

            buffer = amount * safety_buffer_percent / 100
            realistic = net - buffer
            realistic_pct = realistic / amount * 100

            result.append(ArbitrageOpportunity(
                buy=buy, sell=sell, amount=amount, usdt_amount=usdt,
                spread_percent=spread, gross_profit=gross,
                buy_fee=buy_fee, sell_fee=sell_fee, net_profit=net,
                net_profit_percent=net_pct, safety_buffer=buffer,
                realistic_profit=realistic,
                realistic_profit_percent=realistic_pct,
                payment_methods=sorted(payments),
                score=_score(buy, sell, realistic_pct, amount, payments),
            ))

    result.sort(key=lambda x: (x.score, x.realistic_profit), reverse=True)
    unique, seen = [], set()
    for item in result:
        key = (item.buy.ad_id, item.sell.ad_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= max_opportunities:
            break
    return unique
