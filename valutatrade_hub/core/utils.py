"""Вспомогательные функции: работа с JSON-файлами и простые утилиты."""

import json
from pathlib import Path
from typing import Any


# Пути относительно корня проекта
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def load_json(path: Path, default: Any = None) -> Any:
    """Читает JSON. Если файла нет или он пустой — возвращает default."""
    if not path.exists():
        return default if default is not None else []
    try:
        with path.open(encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default if default is not None else []
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else []


def save_json(path: Path, data: Any) -> None:
    """Записывает данные в JSON с нормальным форматированием."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users() -> list[dict]:
    return load_json(USERS_FILE, default=[])


def save_users(users: list[dict]) -> None:
    save_json(USERS_FILE, users)


def load_portfolios() -> list[dict]:
    return load_json(PORTFOLIOS_FILE, default=[])


def save_portfolios(portfolios: list[dict]) -> None:
    save_json(PORTFOLIOS_FILE, portfolios)