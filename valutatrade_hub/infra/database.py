"""Сохранение пользователей и портфелей. Синглтон через __new__."""

from typing import Self

from ..core.utils import (
    PORTFOLIOS_FILE,
    USERS_FILE,
    load_json,
    save_json,
)


class DatabaseManager:
    """Читает и атомарно записывает users.json и portfolios.json.

    __new__ выбран по той же причине, что и в SettingsLoader:
    повторный вызов возвращает тот же объект.
    """

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_users(self) -> list[dict]:
        data = load_json(USERS_FILE, default=[])
        return data if isinstance(data, list) else []

    def save_users(self, users: list[dict]) -> None:
        save_json(USERS_FILE, users)

    def load_portfolios(self) -> list[dict]:
        data = load_json(PORTFOLIOS_FILE, default=[])
        return data if isinstance(data, list) else []

    def save_portfolios(self, portfolios: list[dict]) -> None:
        save_json(PORTFOLIOS_FILE, portfolios)
