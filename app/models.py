from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass(slots=True)
class Advertisement:
    exchange: str
    ad_id: str
    asset: str
    fiat: str
    side: str
    price: float
    available: float
    min_amount: float
    max_amount: float
    merchant: str = ""
    user_type: str = ""
    payment_methods: list[str] = field(default_factory=list)
    month_order_count: int = 0
    month_finish_rate: float = 0.0
    positive_rate: float = 0.0
    pay_time_limit: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def payment_text(self) -> str:
        return ", ".join(self.payment_methods) if self.payment_methods else "-"

    @property
    def finish_rate_percent(self) -> float:
        return self.month_finish_rate * 100

    @property
    def positive_rate_percent(self) -> float:
        return self.positive_rate * 100

    def is_buy(self) -> bool:
        return self.side.upper() == "BUY"

    def is_sell(self) -> bool:
        return self.side.upper() == "SELL"
