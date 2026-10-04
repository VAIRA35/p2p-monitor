import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.analyzer.arbitrage import ArbitrageOpportunity
from app.models import Advertisement

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    buy_exchange TEXT, buy_ad TEXT, sell_exchange TEXT, sell_ad TEXT,
    first_seen TEXT, last_seen TEXT, seen_count INTEGER,
    buy_price REAL, sell_price REAL, amount REAL,
    realistic_profit REAL, realistic_profit_percent REAL,
    best_profit_percent REAL, score REAL, payments TEXT, lockup_minutes INTEGER,
    PRIMARY KEY (buy_exchange, buy_ad, sell_exchange, sell_ad)
);
CREATE TABLE IF NOT EXISTS best_prices (
    ts TEXT, exchange TEXT, best_buy REAL, best_sell REAL, ads INTEGER
);
"""


class Storage:
    """SQLite history: how long each signal lives and best prices per exchange over time."""

    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    def save_signals(self, items: list[ArbitrageOpportunity]) -> list[ArbitrageOpportunity]:
        """Upsert signals; return the ones seen for the first time."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        new = []
        for x in items:
            exists = self.conn.execute(
                "SELECT 1 FROM signals WHERE buy_exchange=? AND buy_ad=? "
                "AND sell_exchange=? AND sell_ad=?", x.key,
            ).fetchone()
            if exists:
                self.conn.execute(
                    "UPDATE signals SET last_seen=?, seen_count=seen_count+1, buy_price=?, "
                    "sell_price=?, amount=?, realistic_profit=?, realistic_profit_percent=?, "
                    "best_profit_percent=MAX(best_profit_percent, ?), score=? "
                    "WHERE buy_exchange=? AND buy_ad=? AND sell_exchange=? AND sell_ad=?",
                    (now, x.buy.price, x.sell.price, x.amount, x.realistic_profit,
                     x.realistic_profit_percent, x.realistic_profit_percent, x.score, *x.key),
                )
            else:
                new.append(x)
                self.conn.execute(
                    "INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (*x.key, now, now, 1, x.buy.price, x.sell.price, x.amount,
                     x.realistic_profit, x.realistic_profit_percent,
                     x.realistic_profit_percent, x.score, ", ".join(x.payment_methods),
                     x.lockup_minutes),
                )
        self.conn.commit()
        return new

    def save_best_prices(self, ads: list[Advertisement]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for exchange in sorted({a.exchange for a in ads}):
            own = [a for a in ads if a.exchange == exchange]
            we_buy = [a.price for a in own if a.is_sell()]
            we_sell = [a.price for a in own if a.is_buy()]
            self.conn.execute(
                "INSERT INTO best_prices VALUES (?,?,?,?,?)",
                (now, exchange, min(we_buy, default=None), max(we_sell, default=None), len(own)),
            )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
