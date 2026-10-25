"""Загрузчик настроек приложения."""

import os
from pathlib import Path

from dotenv import load_dotenv


class SettingsLoader:
    """Читает .env и хранит пути и параметры парсера.

    Это не ParserConfig: у парсера свой объект клиента,
    а здесь общие настройки приложения.
    """

    def __init__(self) -> None:
        load_dotenv()
        root = Path(__file__).resolve().parent.parent.parent
        self.data_dir = root / "data"
        self.rates_file = self.data_dir / "rates.json"
        self.history_file = self.data_dir / "exchange_rates.json"
        self.exchange_rate_api_key = os.getenv("EXCHANGERATE_API_KEY", "")
        self.base_currency = "USD"
        self.fiat_currencies = ("EUR", "GBP", "RUB")
        self.crypto_currencies = ("BTC", "ETH", "SOL")
        self.crypto_id_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"
        self.exchangerate_api_url = "https://v6.exchangerate-api.com/v6"
        self.request_timeout = 10
        self.ttl_seconds = 3600
