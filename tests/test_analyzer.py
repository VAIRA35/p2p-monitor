from app.models import Advertisement
from app.analyzer.arbitrage import find_opportunities

def make(side, price, name, payments):
    return Advertisement("TEST", name, "USDT", "UAH", side, price, 1000, 100, 50000,
                          merchant=name, payment_methods=payments,
                          month_order_count=1000, month_finish_rate=0.99)

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
