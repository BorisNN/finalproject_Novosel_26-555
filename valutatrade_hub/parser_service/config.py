"""Настройки парсера курсов (синглтон)."""

import os
from dataclasses import dataclass, field
from typing import ClassVar

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ParserConfig:
    """Единственный экземпляр настроек парсера.

    Повторный вызов ParserConfig() возвращает тот же объект.
    """

    _instance: ClassVar["ParserConfig | None"] = None

    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "")
    )
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )
    RATES_FILE_PATH: str = "data/rates.json"
    REQUEST_TIMEOUT: int = 10

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ParserConfig":
        return cls()
