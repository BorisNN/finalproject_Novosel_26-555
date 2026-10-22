"""Настройки парсера курсов (по заданию)."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
load_dotenv()


@dataclass
class ParserConfig:
    # Ключ из переменной окружения (для ExchangeRate-API)
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # Эндпоинты из задания
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Списки валют
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")

    # Карта крипто-идентификаторов (правильно инициализируем)
    CRYPTO_ID_MAP: dict = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    })

    # Пути
    RATES_FILE_PATH: str = "data/rates.json"

    # Сетевые параметры
    REQUEST_TIMEOUT: int = 10