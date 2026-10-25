"""Координатор обновления курсов."""

from datetime import datetime

from ..core.utils import load_rates, save_rates
from .api_clients import CoinGeckoClient, ExchangeRateApiClient, ApiRequestError
from .config import ParserConfig
from ..logging_config import get_logger

logger = get_logger(__name__)

class RatesUpdater:
    def __init__(self):
        self.config = ParserConfig()
        self.crypto_client = CoinGeckoClient(self.config)
        self.fiat_client = ExchangeRateApiClient(self.config)

    def update(self) -> str:
        """Получает курсы от обоих клиентов и сохраняет в rates.json."""
        rates = load_rates()
        now = datetime.now().isoformat(timespec="seconds")
        messages = []

        # Крипто
        try:
            crypto_rates = self.crypto_client.fetch_rates()
            for key, value in crypto_rates.items():
                rates[key] = {"rate": value, "updated_at": now}
            messages.append(f"крипто: {len(crypto_rates)} курсов")
        except ApiRequestError as e:
            messages.append(f"крипто ошибка: {e}")

        # Фиат
        try:
            fiat_rates = self.fiat_client.fetch_rates()
            for key, value in fiat_rates.items():
                rates[key] = {"rate": value, "updated_at": now}
            messages.append(f"фиат: {len(fiat_rates)} курсов")
        except ApiRequestError as e:
            messages.append(f"фиат ошибка: {e}")

        rates["source"] = "ParserService"
        rates["last_refresh"] = now
        save_rates(rates)

        logger.info("Обновление курсов завершено: %s", "; ".join(messages))
        return "Обновление завершено: " + "; ".join(messages)