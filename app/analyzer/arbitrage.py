from dataclasses import dataclass, field

from app.models import Advertisement
from app.payments import normalize_payments


@dataclass(slots=True)
class ArbitrageOpportunity:
    buy: Advertisement   # merchant SELL ad: we buy USDT here
    sell: Advertisement  # merchant BUY ad: we sell USDT here
    amount: float        # fiat we spend on the buy leg
    usdt_amount: float   # USDT bought
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
    cross_exchange: bool = False
    transfer_fee_usdt: float = 0.0
    buy_payment_methods: list[str] = field(default_factory=list)   # how we pay
    sell_payment_methods: list[str] = field(default_factory=list)  # how we get paid

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.buy.exchange, self.buy.ad_id, self.sell.exchange, self.sell.ad_id)

    @property
    def lockup_minutes(self) -> int:
        """Worst-case time the capital is stuck: both legs hit their pay time limits."""
        return self.buy.pay_time_limit + self.sell.pay_time_limit


def _speed_score(buy: Advertisement, sell: Advertisement) -> float:
    # Long pay time = capital locked longer and more room for price moves / disputes.
    limits = [x for x in (buy.pay_time_limit, sell.pay_time_limit) if x > 0]
    if not limits:
        return 5.0
    worst = max(limits)
    return round(max(0.0, min(10.0, 10 * (90 - worst) / 75)), 1)


def _score(buy, sell, profit_pct, amount):
    profit = min(max(profit_pct, 0) / 3 * 35, 35)
    finish = (buy.month_finish_rate + sell.month_finish_rate) / 2 * 25
    liquidity = min(amount / 100000 * 15, 15)
    orders = (buy.month_order_count + sell.month_order_count) / 2
    history = min(orders / 1000 * 15, 15)
    return round(min(profit + finish + liquidity + history + _speed_score(buy, sell), 100), 1)


def passes_filters(a: Advertisement, min_finish_rate=0.90, min_order_count=50,
                   max_pay_time_minutes=0, my_payment_methods=None) -> bool:
    """Ad quality filter; with my_payment_methods also requires one of our banks."""
    mine = normalize_payments(my_payment_methods or [])
    return (a.price > 0
            and a.month_finish_rate >= min_finish_rate
            and a.month_order_count >= min_order_count
            and (not max_pay_time_minutes or a.pay_time_limit <= max_pay_time_minutes)
            and (not mine or bool(a.payment_keys & mine)))


def find_opportunities(
    ads, min_spread_percent=0.5, buy_fee_percent=0.0,
    sell_fee_percent=0.0, min_net_profit_percent=0.5,
    max_opportunities=10, min_finish_rate=0.90,
    min_order_count=50, safety_buffer_percent=0.50,
    my_payment_methods=None, same_exchange=True, cross_exchange=True,
    transfer_fee_usdt=0.0, max_pay_time_minutes=0, unique_ads=True,
):
    """Pair buy and sell ads into opportunities.

    my_payment_methods: banks we actually have. If set, each leg must support one of them;
    otherwise both ads must share a common method (old behaviour).
    transfer_fee_usdt: USDT lost moving funds between exchanges (cross-exchange pairs only).
    max_pay_time_minutes: skip ads with a longer pay time limit (0 = no limit).
    unique_ads: each ad is used in at most one opportunity (one merchant can't fill five deals).
    """
    mine = normalize_payments(my_payment_methods or [])

    def eligible(a: Advertisement) -> bool:
        return passes_filters(a, min_finish_rate, min_order_count, max_pay_time_minutes)

    # Merchant SELL = we buy USDT; merchant BUY = we sell USDT.
    buy_ads = [a for a in ads if a.is_sell() and eligible(a)]
    sell_ads = [a for a in ads if a.is_buy() and eligible(a)]

    result = []
    for buy in buy_ads:
        for sell in sell_ads:
            cross = buy.exchange != sell.exchange
            if (cross and not cross_exchange) or (not cross and not same_exchange):
                continue
            if buy.price >= sell.price:
                continue

            buy_keys, sell_keys = buy.payment_keys, sell.payment_keys
            if mine:
                buy_via, sell_via = buy_keys & mine, sell_keys & mine
                if not buy_via or not sell_via:
                    continue
            else:
                buy_via = sell_via = buy_keys & sell_keys
                if not buy_via:
                    continue

            fee_usdt = transfer_fee_usdt if cross else 0.0
            # USDT we can buy, limited by both ads (the sell leg receives usdt - fee).
            usdt = min(
                buy.available, buy.max_amount / buy.price,
                sell.available + fee_usdt, sell.max_amount / sell.price + fee_usdt,
            )
            usdt_to_sell = usdt - fee_usdt
            if usdt_to_sell <= 0:
                continue
            amount = usdt * buy.price
            revenue = usdt_to_sell * sell.price
            # Small tolerance for float rounding on fixed-amount ads.
            if amount < buy.min_amount - 0.01 or revenue < sell.min_amount - 0.01:
                continue

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
                payment_methods=sorted(buy_via | sell_via),
                score=_score(buy, sell, realistic_pct, amount),
                cross_exchange=cross,
                transfer_fee_usdt=fee_usdt,
                buy_payment_methods=sorted(buy_via),
                sell_payment_methods=sorted(sell_via),
            ))

    result.sort(key=lambda x: (x.score, x.realistic_profit), reverse=True)
    unique, seen, used_ads = [], set(), set()
    for item in result:
        buy_ad, sell_ad = item.key[:2], item.key[2:]
        if item.key in seen or (unique_ads and (buy_ad in used_ads or sell_ad in used_ads)):
            continue
        seen.add(item.key)
        used_ads.update((buy_ad, sell_ad))
        unique.append(item)
        if len(unique) >= max_opportunities:
            break
    return unique
