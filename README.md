# ValutaTrade Hub

Консольная программа для учебного валютного портфеля. Покупка и продажа идут через USD.

## Запуск

Нужны Python 3.12 и uv. В корне проекта:

```powershell
uv sync
uv run python main.py
```

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

## Курсы из интернета

`update-rates` берёт BTC, ETH и SOL с CoinGecko, а EUR, GBP и RUB с ExchangeRate-API.

Для второго сайта нужен ключ. В корне создай файл `.env`:

```text
EXCHANGERATE_API_KEY=ключ
```

Файл `.env` в Git не добавляй. Без ключа CoinGecko всё равно запрашивается, фиатные курсы — нет.

## Файлы

- `data/users.json` — пользователи. Пароль хранится как хеш, не открытым текстом.
- `data/portfolios.json` — кошельки.
- `data/rates.json` — курсы.
- `logs/app.log` — журнал.

Сами JSON и логи в Git не входят.

## Демонстрация
https://asciinema.org/a/tD2cDgbz0NgiPTug

или `demo/valutatrade_hub_demo.cast`