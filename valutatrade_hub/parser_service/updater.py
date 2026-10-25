"""Координатор обновления курсов."""

from datetime import datetime

from ..core.exceptions import ValidationError
from ..core.utils import load_rates, save_rates
from ..logging_config import get_logger
from .api_clients import ApiRequestError, CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig

logger = get_logger(__name__)

_SOURCE_ALIASES = {
    "all": "all",
    "coingecko": "crypto",
    "crypto": "crypto",
    "exchangerate": "fiat",
    "exchangerate-api": "fiat",
    "fiat": "fiat",
}


class RatesUpdater:
    def __init__(self):
        self.config = ParserConfig()
        self.crypto_client = CoinGeckoClient(self.config)
        self.fiat_client = ExchangeRateApiClient(self.config)

    def update(self, source: str | None = None) -> str:
        """Получает курсы и сохраняет в rates.json.

        last_refresh меняется только если хотя бы один источник вернул курсы.
        source: coingecko, exchangerate или пусто (оба).
        """
        selected = (source or "all").strip().lower()
        mode = _SOURCE_ALIASES.get(selected)
        if mode is None:
            raise ValidationError(
                "Неизвестный источник. Допустимо: coingecko, exchangerate"
            )

        rates = load_rates()
        now = datetime.now().isoformat(timespec="seconds")
        messages = []
        updated_any = False

        if mode in ("all", "crypto"):
            try:
                crypto_rates = self.crypto_client.fetch_rates()
                for key, value in crypto_rates.items():
                    rates[key] = {"rate": value, "updated_at": now}
                if crypto_rates:
                    updated_any = True
                messages.append(f"крипто: {len(crypto_rates)} курсов")
            except ApiRequestError as e:
                messages.append(f"крипто ошибка: {e}")

        if mode in ("all", "fiat"):
            try:
                fiat_rates = self.fiat_client.fetch_rates()
                for key, value in fiat_rates.items():
                    rates[key] = {"rate": value, "updated_at": now}
                if fiat_rates:
                    updated_any = True
                messages.append(f"фиат: {len(fiat_rates)} курсов")
            except ApiRequestError as e:
                messages.append(f"фиат ошибка: {e}")

        if not updated_any:
            logger.info("Обновление курсов не сохранено: %s", "; ".join(messages))
            return "Обновление не выполнено: " + "; ".join(messages)

        rates["source"] = "ParserService"
        rates["last_refresh"] = now
        save_rates(rates)

        logger.info("Обновление курсов завершено: %s", "; ".join(messages))
        return "Обновление завершено: " + "; ".join(messages)
