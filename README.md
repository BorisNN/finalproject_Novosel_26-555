# ValutaTrade Hub

Консольная программа для учебного валютного портфеля. Покупка и продажа идут через USD.

## Запуск

Нужны Python 3.12 и uv. В корне проекта:

```powershell
uv sync
uv run python main.py
```

Ту же программу открывает `uv run valutatrade-hub`.
Команда `help` показывает список команд, `exit` закрывает программу.

## Пример

```text
register --username demo --password 1234
login --username demo --password 1234
deposit --currency USD --amount 1000
update-rate --from BTC --to USD --rate 60000
buy --currency BTC --amount 0.01
show-portfolio
get-rate --from BTC --to USD
show-rates
sell --currency BTC --amount 0.01
logout
exit
```

`update-rate` записывает курс вручную, интернет для этого не нужен.

## Курсы из интернета

`update-rates` берёт BTC, ETH и SOL с CoinGecko, а EUR, GBP и RUB с ExchangeRate-API.

Для второго сайта нужен ключ. В корне создай файл `.env` по образцу `.env.example`:

```text
EXCHANGERATE_API_KEY=ключ
```

Файл `.env` в Git не добавлятся.

Курсы лежат в локальном кеше `data/rates.json` в виде `{"pairs": ..., "last_refresh": ...}`.
Каждое сохранение дописывает в `data/exchange_rates.json` отдельные измерения: id, from_currency, to_currency, rate, timestamp, source. Повтор того же id не пишется. Оба файла в Git не входят.
Срок актуальности курса берётся из config.json, ключ rates_ttl_seconds (сейчас 3600). Его проверяют `get-rate`, `buy` и `sell`.
`show-rates --top N` показывает N самых дорогих криптовалют.
`show-rates --base EUR` пересчитывает пары в евро.

## Файлы

- `data/users.json` — пользователи. Пароль хранится как хеш, не открытым текстом.
- `data/portfolios.json` — кошельки.
- `data/rates.json` — текущий кеш курсов.
- `data/exchange_rates.json` — история курсов.
- `logs/app.log` — журнал. Файл обрезается по размеру, хранятся 3 старые копии.

Сами JSON и логи в Git не входят.

## Структура

- `main.py` — запуск
- `valutatrade_hub/core/` — валюты, модели, операции, исключения
- `valutatrade_hub/cli/` — разбор команд
- `valutatrade_hub/parser_service/` — клиенты API, обновление и хранение курсов
- `valutatrade_hub/infra/` — SettingsLoader и DatabaseManager
- `valutatrade_hub/decorators.py` — журнал действий `@log_action`
- `valutatrade_hub/logging_config.py` — консоль и файл с ротацией

## Демонстрация

https://asciinema.org/a/tD2cDgbz0NgiPTug

или `demo/valutatrade_hub_demo.cast`

