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

def load_rates() -> dict:
    """Загружает курсы из rates.json. Если файла нет — возвращает пустой словарь."""
    return load_json(RATES_FILE, default={})


def save_rates(rates: dict) -> None:
    """Сохраняет курсы в rates.json."""
    save_json(RATES_FILE, rates)


def get_rate_value(from_currency: str, to_currency: str) -> float | None:
    """
    Возвращает числовое значение курса FROM→TO или None, если его нет.
    Поддерживает прямой и обратный курс.
    """
    rates = load_rates()
    from_code = from_currency.strip().upper()
    to_code = to_currency.strip().upper()

    direct_key = f"{from_code}_{to_code}"
    if direct_key in rates and isinstance(rates[direct_key], dict):
        return rates[direct_key].get("rate")

    reverse_key = f"{to_code}_{from_code}"
    if reverse_key in rates and isinstance(rates[reverse_key], dict):
        reverse = rates[reverse_key].get("rate")
        if reverse and reverse > 0:
            return 1.0 / reverse

    return None