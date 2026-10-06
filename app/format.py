"""Human-friendly names and numbers shared by the terminal and Telegram."""
from app.analyzer.arbitrage import ArbitrageOpportunity

EXCHANGE_NAMES = {"BINANCE": "Binance", "BYBIT": "Bybit", "OKX": "OKX"}
BANK_NAMES = {
    "monobank": "Моно", "privatbank": "Приват", "pumb": "ПУМБ", "a-bank": "А-Банк",
    "sense": "Sense", "raiffeisen": "Райф", "oschadbank": "Ощад", "izibank": "izibank",
    "ukrsibbank": "УкрСиб", "otp": "OTP", "bank transfer": "банк. перевод",
}
FIAT_SYMBOLS = {"UAH": "₴", "USD": "$", "EUR": "€"}


def exchange(name: str) -> str:
    return EXCHANGE_NAMES.get(name.upper(), name.title())


def banks(keys: list[str]) -> str:
    return ", ".join(BANK_NAMES.get(k, k) for k in keys)


def money(value: float, fiat: str) -> str:
    """15500.3 -> '15 500 ₴'"""
    return f"{value:,.0f}".replace(",", " ") + f" {FIAT_SYMBOLS.get(fiat, fiat)}"


def route(x: ArbitrageOpportunity) -> str:
    if x.cross_exchange:
        return f"{exchange(x.buy.exchange)} → {exchange(x.sell.exchange)}"
    return exchange(x.buy.exchange)


def payment_route(x: ArbitrageOpportunity) -> str:
    """'Приват' when both legs use the same bank, else 'Моно → Приват'."""
    pay, receive = banks(x.buy_payment_methods), banks(x.sell_payment_methods)
    return pay if pay == receive else f"{pay} → {receive}"
