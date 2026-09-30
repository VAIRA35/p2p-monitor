# P2P Monitor — полное описание проекта

## Назначение
Консольный монитор P2P USDT/UAH. Получает объявления, приводит их к общей модели, ищет потенциальный арбитраж и показывает сигналы.

## Архитектура
`ExchangeAdapter -> Advertisement -> Arbitrage Analyzer -> Signal filters -> Terminal`

## Файлы
- `app/models.py` — единая модель объявления.
- `app/exchanges/base.py` — интерфейс адаптеров бирж.
- `app/exchanges/binance.py` — рабочий Binance P2P adapter.
- `app/exchanges/bybit.py` — placeholder: проверенный endpoint `/v5/p2p/item/online` требует apiKey/соответствующие P2P permissions.
- `app/exchanges/okx.py` — placeholder, без выдуманного endpoint.
- `app/analyzer/arbitrage.py` — расчёт spread, объёма, комиссий, safety buffer и score.
- `app/terminal.py` — вывод в консоль.
- `app/main.py` — основной цикл и конфигурация.
- `config.yaml` — настройки пары, частоты, фильтров и сигналов.
- `tests/` — базовые тесты.
- `.env.example` — заготовка для будущих ключей; реальные ключи не коммитить.

## Соглашение side
`SELL` означает merchant продаёт USDT -> мы покупаем USDT.
`BUY` означает merchant покупает USDT -> мы продаём USDT.

## Арбитраж
1. Отбираются качественные объявления.
2. Требуется общий способ оплаты.
3. Объём ограничивается ликвидностью и лимитами обеих сторон.
4. Считается spread.
5. Вычитаются комиссии.
6. Вычитается safety buffer.
7. Рассчитывается технический score.

Score состоит из компонентов: прибыль, completion rate, ликвидность, история ордеров и совместимость payment method. Score не является гарантией прибыли.

## Текущее состояние
Рабочее ядро: Binance.
Bybit и OKX пока не подключены. Автоматические сделки, Telegram, БД и полноценный cross-exchange режим пока не реализованы.

## Запуск
```bash
cd ~/p2p-monitor
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Тесты:
```bash
pytest -q
```

## Дальнейший план
1. Реализовать/проверить Bybit источник данных.
2. Реализовать OKX.
3. Добавить cross-exchange анализ.
4. Добавить storage/историю.
5. Добавить Telegram alerts.
6. Добавить retry/rate-limit/logging и production monitoring.
