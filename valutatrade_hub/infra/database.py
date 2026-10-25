"""Сохранение пользователей и портфелей."""

from ..core.utils import (
    PORTFOLIOS_FILE,
    USERS_FILE,
    load_json,
    save_json,
)


class DatabaseManager:
    """Читает и атомарно записывает users.json и portfolios.json."""

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
