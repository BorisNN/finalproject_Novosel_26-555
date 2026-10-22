"""Обёртка для вызова обновления курсов."""

from .updater import RatesUpdater


def fetch_and_update_rates() -> str:
    updater = RatesUpdater()
    return updater.update()