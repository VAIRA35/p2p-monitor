# P2P monitor — project notes for Claude

Console monitor for P2P USDT/UAH ads (Binance works; Bybit/OKX are placeholders). See README.md for full description.

## Commands
- Run once (for checks): `.venv/bin/python run.py --once`
- Run live loop: `.venv/bin/python run.py`
- Tests: `.venv/bin/python -m pytest -q`
- Deps: `.venv/bin/pip install -r requirements.txt` (pytest installed in venv, not in requirements.txt)

## Architecture
`app/exchanges/*` (ExchangeAdapter) -> `app/models.Advertisement` -> `app/analyzer/arbitrage.find_opportunities`
-> signal filters in `app/main.py` -> `app/terminal.py`. Settings in `config.yaml`.

## Conventions / gotchas
- Side = the MERCHANT's side: `SELL` = merchant sells USDT -> we buy; `BUY` = merchant buys -> we sell.
  Binance: request `tradeType=BUY` returns ads with `adv.tradeType=SELL` (verified 2026-09-30).
- Top-of-book on Binance often looks "inverted" (cheap buy < expensive sell) because of tiny fixed-amount ads
  (min == max) and large-minimum / 180-min pay-time ads. Signals are NOT guaranteed profit.
- `config.yaml` `exchanges:` flags are not wired up yet — main.py always uses Binance.
- Never commit `.env` / API keys. Keys (read-only) go to `.env`, loaded from env vars.
