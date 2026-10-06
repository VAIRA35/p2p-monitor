import pytest

from app.models import Advertisement
from app.analyzer.arbitrage import find_opportunities


def make(side, price, name, payments, exchange="TEST", available=1000, min_amount=100,
         max_amount=50000, pay_time=15):
    return Advertisement(exchange, name, "USDT", "UAH", side, price, available, min_amount,
                         max_amount, merchant=name, payment_methods=payments,
                         month_order_count=1000, month_finish_rate=0.99,
                         pay_time_limit=pay_time)


def test_payment_match_required():
    assert not find_opportunities([
        make("SELL", 44, "s", ["Monobank"]),
        make("BUY", 45, "b", ["PrivatBank"]),
    ])


def test_matching_payment():
    result = find_opportunities([
        make("SELL", 44, "s", ["Monobank"]),
        make("BUY", 45, "b", ["Monobank"]),
    ])
    assert result


def test_payment_names_normalized_across_exchanges():
    result = find_opportunities([
        make("SELL", 44, "s", ["Monobank (Card)"], exchange="OKX"),
        make("BUY", 45, "b", ["Monobank"], exchange="BINANCE"),
    ])
    assert result and result[0].payment_methods == ["monobank"]


def test_my_payment_methods_allow_different_banks_per_leg():
    ads = [
        make("SELL", 44, "s", ["Monobank"]),
        make("BUY", 45, "b", ["PrivatBank"]),
    ]
    result = find_opportunities(ads, my_payment_methods=["monobank", "privatbank"])
    assert result
    assert result[0].buy_payment_methods == ["monobank"]
    assert result[0].sell_payment_methods == ["privatbank"]
    assert not find_opportunities(ads, my_payment_methods=["monobank"])


def test_cross_exchange_transfer_fee():
    ads = [
        make("SELL", 44, "s", ["Monobank"], exchange="BYBIT", available=100),
        make("BUY", 45, "b", ["Monobank"], exchange="BINANCE"),
    ]
    result = find_opportunities(ads, transfer_fee_usdt=1.0, min_net_profit_percent=0)
    assert result[0].cross_exchange
    # buy 100 USDT for 4400, sell 99 USDT for 4455
    assert result[0].amount == pytest.approx(4400)
    assert result[0].gross_profit == pytest.approx(99 * 45 - 4400)
    assert not find_opportunities(ads, cross_exchange=False)


def test_same_exchange_can_be_disabled():
    ads = [make("SELL", 44, "s", ["Monobank"]), make("BUY", 45, "b", ["Monobank"])]
    assert not find_opportunities(ads, same_exchange=False)


def test_max_pay_time_filter():
    ads = [make("SELL", 44, "s", ["Monobank"], pay_time=180),
           make("BUY", 45, "b", ["Monobank"])]
    assert find_opportunities(ads)
    assert not find_opportunities(ads, max_pay_time_minutes=60)


def test_fixed_amount_ad_must_fit_other_leg():
    # Seller accepts only exactly 20000 UAH, buyer takes at most 10000 -> impossible.
    ads = [make("SELL", 44, "s", ["Monobank"], min_amount=20000, max_amount=20000),
           make("BUY", 45, "b", ["Monobank"], max_amount=10000)]
    assert not find_opportunities(ads)


def test_faster_pay_time_scores_higher():
    fast = find_opportunities([make("SELL", 44, "s", ["Monobank"], pay_time=15),
                               make("BUY", 45, "b", ["Monobank"], pay_time=15)])[0]
    slow = find_opportunities([make("SELL", 44, "s", ["Monobank"], pay_time=90),
                               make("BUY", 45, "b", ["Monobank"], pay_time=90)])[0]
    assert fast.score > slow.score


def test_each_ad_used_once():
    ads = [make("SELL", 44, "s1", ["Monobank"]), make("SELL", 44.1, "s2", ["Monobank"]),
           make("BUY", 45, "b", ["Monobank"])]
    assert len(find_opportunities(ads)) == 1
    assert len(find_opportunities(ads, unique_ads=False)) == 2


def test_passes_filters_my_banks():
    from app.analyzer import passes_filters
    a = make("SELL", 44, "s", ["PUMB"])
    assert passes_filters(a)
    assert not passes_filters(a, my_payment_methods=["monobank"])
