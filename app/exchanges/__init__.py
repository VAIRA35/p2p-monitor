from app.exchanges.binance import BinanceAdapter
from app.exchanges.bybit import BybitAdapter
from app.exchanges.okx import OKXAdapter

ADAPTERS = {"binance": BinanceAdapter, "bybit": BybitAdapter, "okx": OKXAdapter}
