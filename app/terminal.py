from datetime import datetime

from app import format as fmt
from app.analyzer.arbitrage import ArbitrageOpportunity
from app.models import Advertisement

LINE = "─" * 46
STATUS_ICONS = {"LIVE": "🟢", "COOLDOWN": "🟡", "OFFLINE": "🔴"}


def _status(name: str, state: str) -> str:
    icon = next((v for k, v in STATUS_ICONS.items() if state.startswith(k)), "⚪")
    note = {"COOLDOWN": " (пауза 30с)", "OFFLINE": " (нет связи)"}
    extra = next((v for k, v in note.items() if state.startswith(k)), "")
    return f"{icon} {fmt.exchange(name)}{extra}"


def render(ads: list[Advertisement], statuses: dict[str, str],
           signals: list[ArbitrageOpportunity], asset: str, fiat: str,
           max_signals: int, elapsed: float) -> None:
    """`ads` are already filtered: reliable merchants, our banks."""
    title = f" P2P MONITOR · {asset}/{fiat}"
    out = ["\033[2J\033[H" + title + f"{datetime.now():%H:%M:%S}".rjust(46 - len(title))]
    out.append(" " + "  ".join(_status(n, s) for n, s in statuses.items()))
    out.append(LINE)

    capital = signals[0].capital if signals else 0
    note = f" · % от капитала {fmt.money(capital, fiat)}" if capital else ""
    out.append(f" СДЕЛКИ ({len(signals)}){note}")
    if not signals:
        out.append("\n   Сейчас подходящих сделок нет.")
    for i, x in enumerate(signals[:max_signals], 1):
        profit = f"+{fmt.money(x.realistic_profit, fiat)}  ({x.capital_percent:.1f}%)"
        head = f" #{i}  {fmt.route(x)}"
        out.append("")
        out.append(head + profit.rjust(46 - len(head)))
        out.append(f"     купить {x.buy.price:.2f}  →  продать {x.sell.price:.2f}")
        out.append(f"     объём {fmt.money(x.amount, fiat)} · заморозка ≤ {x.lockup_minutes} мин")
        pay, receive = fmt.banks(x.buy_payment_methods), fmt.banks(x.sell_payment_methods)
        out.append(f"     платишь: {pay} · получаешь: {receive}")
    if len(signals) > max_signals:
        out.append(f"\n   ...и ещё {len(signals) - max_signals}")
    out.append(LINE)

    out.append(f" ЛУЧШИЕ ЦЕНЫ    купить {asset}   продать {asset}")
    out.append("   (надёжные мерчанты, твои банки)")
    for name in statuses:
        own = [a for a in ads if a.exchange == name]
        buy = min((a.price for a in own if a.is_sell()), default=None)
        sell = max((a.price for a in own if a.is_buy()), default=None)
        b = f"{buy:.2f}" if buy else "—"
        s = f"{sell:.2f}" if sell else "—"
        out.append(f" {fmt.exchange(name):14}{b:>10}{s:>15}")
    out.append(LINE)
    out.append(f" обновлено за {elapsed:.1f}с · Ctrl+C — стоп")
    print("\n".join(out))
