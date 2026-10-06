import asyncio

from app.alerts import telegram
from app.alerts.telegram import TelegramNotifier
from app.analyzer.arbitrage import find_opportunities
from app.models import Advertisement


def _signal():
    def make(side, price, name):
        return Advertisement("TEST", name, "USDT", "UAH", side, price, 1000, 100, 50000,
                             payment_methods=["Monobank"], month_order_count=1000,
                             month_finish_rate=0.99)
    return find_opportunities([make("SELL", 44, "s"), make("BUY", 45, "b")])


def test_persistent_signal_sent_once(monkeypatch):
    calls = []

    async def fake_request(*args, **kwargs):
        calls.append(kwargs["json"]["text"])
        return {"ok": True}

    clock = [1000.0]
    monkeypatch.setattr(telegram, "request_json", fake_request)
    monkeypatch.setattr(telegram.time, "monotonic", lambda: clock[0])
    n = TelegramNotifier(None, "token", "1", cooldown_seconds=600)
    items = _signal()

    async def run():
        assert await n.notify(items, "UAH") == 1
        for _ in range(10):              # present every tick for a long time
            clock[0] += 120
            assert await n.notify(items, "UAH") == 0
        clock[0] += 700                  # gone for longer than cooldown, then back
        assert await n.notify(items, "UAH") == 1

    asyncio.run(run())
    assert len(calls) == 2


def test_format_signal_three_lines():
    text = telegram.format_signal(_signal()[0], "UAH")
    lines = text.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("🟢 +") and "₴" in lines[0]
    assert "Моно" in lines[1]
