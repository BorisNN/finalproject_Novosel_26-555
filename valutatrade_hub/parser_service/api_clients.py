"""Клиенты для внешних API курсов."""

import requests
from abc import ABC, abstractmethod

from .config import ParserConfig


class ApiRequestError(Exception):
    """Ошибка при запросе к внешнему API."""
    pass


class BaseApiClient(ABC):
    @abstractmethod
    def fetch_rates(self) -> dict:
        """Возвращает словарь вида {'BTC_USD': 60000.0, ...}."""
        pass


class CoinGeckoClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self.config = config

    def fetch_rates(self) -> dict:
        ids = ",".join(self.config.CRYPTO_ID_MAP.values())
        params = {
            "ids": ids,
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
        try:
            resp = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise ApiRequestError(f"CoinGecko: {e}") from e

        result = {}
        id_to_code = {v: k for k, v in self.config.CRYPTO_ID_MAP.items()}
        for coin_id, prices in data.items():
            code = id_to_code.get(coin_id)
            if not code:
                continue
            rate = prices.get(self.config.BASE_CURRENCY.lower())
            if rate is not None:
                result[f"{code}_{self.config.BASE_CURRENCY}"] = float(rate)
        return result


class ExchangeRateApiClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self.config = config

    def fetch_rates(self) -> dict:
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("Не задан EXCHANGERATE_API_KEY")

        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )
        try:
            resp = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API: {e}") from e

        if data.get("result") != "success":
            raise ApiRequestError(f"ExchangeRate-API вернул ошибку: {data.get('error-type')}")

        rates = data.get("conversion_rates", {})
        result = {}
        for fiat in self.config.FIAT_CURRENCIES:
            rate = rates.get(fiat)
            if rate is not None and rate > 0:
                # В API курс — сколько единиц fiat за 1 USD, нам нужен fiat→USD
                result[f"{fiat}_{self.config.BASE_CURRENCY}"] = 1.0 / float(rate)
        return result