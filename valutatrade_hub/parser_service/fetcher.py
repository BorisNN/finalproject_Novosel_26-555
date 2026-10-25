"""Обёртка для вызова обновления курсов."""

from .updater import RatesUpdater


def fetch_and_update_rates(source: str | None = None) -> str:
    updater = RatesUpdater()
    return updater.update(source)
