from app.models import Advertisement

def test_helpers():
    a = Advertisement("TEST", "1", "USDT", "UAH", "SELL", 44.5, 100, 500, 5000,
                       month_finish_rate=0.995, positive_rate=0.99)
    assert a.is_sell()
    assert not a.is_buy()
    assert a.finish_rate_percent == 99.5
