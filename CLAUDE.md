# P2P monitor — project notes for Claude

Console monitor for P2P USDT/UAH ads on Binance, Bybit, OKX (all via public endpoints, no API keys). See README.md for full description.

## Commands
- Run once (for checks): `.venv/bin/python run.py --once`
- Run live loop: `.venv/bin/python run.py`
- Tests: `.venv/bin/python -m pytest -q`
- Deps: `.venv/bin/pip install -r requirements.txt` (pytest installed in venv, not in requirements.txt)

## Architecture
`app/exchanges/*` (ExchangeAdapter, shared aiohttp session, `app/http.request_json` retries) ->
`app/models.Advertisement` -> `app/analyzer/arbitrage.find_opportunities` -> signal filters in `app/main.py` ->
`app/terminal.py` + `app/storage` (SQLite `p2p.db`) + `app/alerts` (Telegram). Settings in `config.yaml`.

## Conventions / gotchas
- Side = the MERCHANT's side: `SELL` = merchant sells USDT -> we buy; `BUY` = merchant buys -> we sell.
  Binance: request `tradeType=BUY` returns ads with `adv.tradeType=SELL` (verified 2026-09-30).
- Top-of-book on Binance often looks "inverted" (cheap buy < expensive sell) because of tiny fixed-amount ads
  (min == max) and large-minimum / 180-min pay-time ads. Signals are NOT guaranteed profit.
- Bybit: request/item side "1" = merchant SELL, "0" = merchant BUY. Payment ids -> names via
  queryAllPaymentList (~11 s, cached in `cache/bybit_payments.json` for 24 h).
- OKX: `side` param is already the merchant's side (side=sell -> merchant sells).
- Compare banks via `Advertisement.payment_keys` (normalized in `app/payments.py`), never raw names.
- Never log URLs that contain secrets (Telegram token) — use `request_json(label=...)`.
- Never commit `.env` / API keys. Keys (read-only) go to `.env`, loaded from env vars.
