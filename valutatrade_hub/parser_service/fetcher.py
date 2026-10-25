"""Обёртка для вызова обновления курсов."""

from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig
from .storage import RatesStorage
from .updater import RatesUpdater


def fetch_and_update_rates(source: str | None = None) -> str:
    config = ParserConfig()
    updater = RatesUpdater(
        CoinGeckoClient(config),
        ExchangeRateApiClient(config),
        RatesStorage(),
    )
    return updater.run_update(source)
