import logging
import time

import aiohttp

from app.analyzer.arbitrage import ArbitrageOpportunity
from app.http import request_json

log = logging.getLogger(__name__)


def format_signal(x: ArbitrageOpportunity, fiat: str) -> str:
    route = f"{x.buy.exchange} -> {x.sell.exchange}" if x.cross_exchange else x.buy.exchange
    lines = [
        f"P2P signal | {route} | score {x.score:.0f}",
        f"Buy {x.buy.price:.2f} ({x.buy.merchant}) -> sell {x.sell.price:.2f} ({x.sell.merchant})",
        f"Volume {x.amount:,.0f} {fiat} | spread {x.spread_percent:.2f}%",
        f"Realistic profit {x.realistic_profit:,.2f} {fiat} ({x.realistic_profit_percent:.2f}%)",
        f"Pay via {', '.join(x.buy_payment_methods)} | receive via {', '.join(x.sell_payment_methods)}",
        f"Lock-up up to {x.lockup_minutes} min",
    ]
    if x.cross_exchange:
        lines.append(f"Transfer fee {x.transfer_fee_usdt} USDT included")
    lines.append("Check ad terms before trading. Not guaranteed profit.")
    return "\n".join(lines)


class TelegramNotifier:
    def __init__(self, session: aiohttp.ClientSession, token: str, chat_id: str,
                 cooldown_seconds: float = 300):
        self.session = session
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.cooldown = cooldown_seconds
        self._sent: dict[tuple, float] = {}

    async def notify(self, items: list[ArbitrageOpportunity], fiat: str) -> int:
        """Send signals not alerted within the cooldown; return how many were sent."""
        now = time.monotonic()
        sent = 0
        for x in items:
            if now - self._sent.get(x.key, -self.cooldown) < self.cooldown:
                continue
            try:
                await request_json(
                    self.session, "POST", self.url, retries=1, label="telegram sendMessage",
                    json={"chat_id": self.chat_id, "text": format_signal(x, fiat)},
                )
            except Exception as exc:
                # Never log the URL: it contains the bot token.
                log.error("Telegram send failed: %s", type(exc).__name__)
                continue
            self._sent[x.key] = now
            sent += 1
        return sent
