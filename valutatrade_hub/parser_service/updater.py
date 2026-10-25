"""Координатор обновления курсов."""

import math
from datetime import datetime

from ..core.exceptions import RateUnavailableError, ValidationError
from ..decorators import log_action
from .api_clients import ApiRequestError
from .storage import RatesStorage

_SOURCE_ALIASES = {
    "all": "all",
    "coingecko": "crypto",
    "crypto": "crypto",
    "exchangerate": "fiat",
    "exchangerate-api": "fiat",
    "fiat": "fiat",
}


def _acceptable_rate(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and value > 0


class RatesUpdater:
    """Обновляет кеш. Клиенты и хранилище приходят снаружи."""

    def __init__(self, crypto_client, fiat_client, storage: RatesStorage) -> None:
        self.crypto_client = crypto_client
        self.fiat_client = fiat_client
        self.storage = storage

    @log_action("update-rates")
    def run_update(self, source: str | None = None) -> str:
        """Получает курсы и сохраняет документ {"pairs", "last_refresh"}.

        last_refresh меняется только если хотя бы один источник вернул курсы.
        source: coingecko, exchangerate или пусто (оба).
        """
        selected = (source or "all").strip().lower()
        mode = _SOURCE_ALIASES.get(selected)
        if mode is None:
            raise ValidationError(
                "Неизвестный источник. Допустимо: coingecko, exchangerate"
            )

        document = self.storage.load()
        pairs = document["pairs"]
        now = datetime.now().isoformat(timespec="seconds")
        messages = []
        updated_any = False

        if mode in ("all", "crypto"):
            try:
                crypto_rates = self.crypto_client.fetch_rates()
                self._store_pairs(pairs, crypto_rates, now)
                if crypto_rates:
                    updated_any = True
                messages.append(f"крипто: {len(crypto_rates)} курсов")
            except (ApiRequestError, ValueError) as exc:
                messages.append(f"крипто ошибка: {exc}")

        if mode in ("all", "fiat"):
            try:
                fiat_rates = self.fiat_client.fetch_rates()
                self._store_pairs(pairs, fiat_rates, now)
                if fiat_rates:
                    updated_any = True
                messages.append(f"фиат: {len(fiat_rates)} курсов")
            except (ApiRequestError, ValueError) as exc:
                messages.append(f"фиат ошибка: {exc}")

        if not updated_any:
            raise RateUnavailableError(
                "Обновление не выполнено: " + "; ".join(messages)
            )

        document["pairs"] = pairs
        document["source"] = "ParserService"
        document["last_refresh"] = now
        self.storage.save(document)
        return "Обновление завершено: " + "; ".join(messages)

    @staticmethod
    def _store_pairs(pairs: dict, fresh: dict, now: str) -> None:
        cleaned: dict = {}
        for key, value in fresh.items():
            if not _acceptable_rate(value):
                raise ValueError(f"Некорректный курс {key}: {value}")
            cleaned[key] = {"rate": float(value), "updated_at": now}
        pairs.update(cleaned)
