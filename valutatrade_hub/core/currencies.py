"""Иерархия валют: абстрактный Currency и реестр кодов."""

import re
from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError, ValidationError

_CODE = re.compile(r"^[A-Z]{2,5}$")


def _check_code(code: str) -> str:
    """Код: 2–5 заглавных букв, без пробелов."""
    if not isinstance(code, str):
        raise ValidationError("Код валюты должен быть строкой")
    cleaned = code.strip().upper()
    if not _CODE.fullmatch(cleaned):
        raise ValidationError("Код валюты: 2–5 заглавных латинских букв, без пробелов")
    return cleaned


def _check_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Имя валюты не может быть пустым")
    return name.strip()


def _market_cap(value: float) -> str:
    """1.12e+12 превращает в вид из задания: 1.12e12."""
    return f"{value:.2e}".replace("e+", "e")


class Currency(ABC):
    """Общий контракт валюты. Сам по себе объект не создаётся."""

    def __init__(self, code: str, name: str) -> None:
        self._code = _check_code(code)
        self._name = _check_name(name)

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_crypto(self) -> bool:
        return False

    @abstractmethod
    def get_display_info(self) -> str:
        """Строка для интерфейса и логов."""


class FiatCurrency(Currency):
    """Фиат. issuing_country — страна или зона эмиссии."""

    def __init__(self, code: str, name: str, issuing_country: str) -> None:
        super().__init__(code, name)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValidationError("Страна эмиссии не может быть пустой")
        self._issuing_country = issuing_country.strip()

    @property
    def issuing_country(self) -> str:
        return self._issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта. coin_id нужен CoinGecko, не входит в строку задания."""

    def __init__(
        self,
        code: str,
        name: str,
        coin_id: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(code, name)
        if not isinstance(coin_id, str) or not coin_id.strip():
            raise ValidationError("coin_id не может быть пустым")
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValidationError("Алгоритм не может быть пустым")
        if isinstance(market_cap, bool) or not isinstance(market_cap, (int, float)):
            raise ValidationError("Капитализация должна быть числом")
        if market_cap < 0:
            raise ValidationError("Капитализация не может быть отрицательной")
        self._coin_id = coin_id.strip()
        self._algorithm = algorithm.strip()
        self._market_cap = float(market_cap)

    @property
    def coin_id(self) -> str:
        return self._coin_id

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def market_cap(self) -> float:
        return self._market_cap

    @property
    def is_crypto(self) -> bool:
        return True

    def get_display_info(self) -> str:
        cap = _market_cap(self.market_cap)
        return (
            f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {cap})"
        )


# Капитализация учебная: задание требует поле, живой API её сюда не пишет.
_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("USD", "US Dollar", "United States"),
    "EUR": FiatCurrency("EUR", "Euro", "Eurozone"),
    "GBP": FiatCurrency("GBP", "British Pound", "United Kingdom"),
    "RUB": FiatCurrency("RUB", "Russian Ruble", "Russia"),
    "BTC": CryptoCurrency("BTC", "Bitcoin", "bitcoin", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("ETH", "Ethereum", "ethereum", "Ethash", 4.00e11),
    "SOL": CryptoCurrency("SOL", "Solana", "solana", "Proof-of-History", 8.00e10),
}


def get_currency(code: str) -> Currency:
    """Фабрика. Неизвестный или кривой код — CurrencyNotFoundError."""
    if not isinstance(code, str) or not code.strip():
        shown = code if isinstance(code, str) else ""
        raise CurrencyNotFoundError(f"Неизвестная валюта '{shown}'")
    key = code.strip().upper()
    if not _CODE.fullmatch(key):
        raise CurrencyNotFoundError(f"Неизвестная валюта '{key}'")
    currency = _REGISTRY.get(key)
    if currency is None:
        raise CurrencyNotFoundError(f"Неизвестная валюта '{key}'")
    return currency


def is_crypto_code(code: str) -> bool:
    """True, если код есть в реестре и это криптовалюта."""
    try:
        return get_currency(code).is_crypto
    except CurrencyNotFoundError:
        return False
