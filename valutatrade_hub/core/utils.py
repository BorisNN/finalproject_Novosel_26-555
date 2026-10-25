"""Вспомогательные функции: работа с JSON-файлами и курсами."""

import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"

# Срок актуальности курса: 1 час.
RATE_TTL_SECONDS = 3600


def load_json(path: Path, default: Any = None) -> Any:
    """Читает JSON. Если файла нет или он пустой — возвращает default."""
    if not path.exists():
        return default if default is not None else []
    try:
        with path.open(encoding="utf-8") as file:
            content = file.read().strip()
            if not content:
                return default if default is not None else []
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else []


def save_json(path: Path, data: Any) -> None:
    """Атомарно записывает JSON: сначала временный файл, потом замена."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_users() -> list[dict]:
    return load_json(USERS_FILE, default=[])


def save_users(users: list[dict]) -> None:
    save_json(USERS_FILE, users)


def load_portfolios() -> list[dict]:
    return load_json(PORTFOLIOS_FILE, default=[])


def save_portfolios(portfolios: list[dict]) -> None:
    save_json(PORTFOLIOS_FILE, portfolios)


def load_rates() -> dict:
    """Документ курсов: pairs, last_refresh, source."""
    from ..parser_service.storage import RatesStorage

    return RatesStorage().load()


def save_rates(rates: dict) -> None:
    """Сохраняет документ курсов и снимок истории."""
    from ..parser_service.storage import RatesStorage

    RatesStorage().save(rates)


def _positive_rate(value: Any) -> float | None:
    """Возвращает курс, только если это конечное положительное число."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def _rate_entry(
    pairs: dict, from_code: str, to_code: str
) -> tuple[float, str | None] | None:
    """Прямая запись FROM_TO из pairs."""
    item = pairs.get(f"{from_code}_{to_code}")
    if not isinstance(item, dict):
        return None
    rate = _positive_rate(item.get("rate"))
    if rate is None:
        return None
    updated = item.get("updated_at")
    return rate, updated if isinstance(updated, str) else None


def _aware(value: datetime) -> datetime:
    """Делает дату со смещением, чтобы наивные и UTC-даты можно было вычитать."""
    if value.tzinfo is None:
        return value.astimezone()
    return value


def get_rate_info(from_currency: str, to_currency: str) -> dict | None:
    """Курс FROM→TO и время, с которого он посчитан.

    Сначала обе валюты ищутся в реестре. Одинаковые валюты дают 1.0.
    Дальше прямая запись, обратная и перекрёстный курс через USD.
    """
    from .models import get_currency

    from_code = from_currency.strip().upper()
    to_code = to_currency.strip().upper()
    if not from_code or not to_code:
        return None
    get_currency(from_code)
    get_currency(to_code)
    if from_code == to_code:
        return {"rate": 1.0, "updated_at": None}

    pairs = load_rates().get("pairs", {})
    direct = _rate_entry(pairs, from_code, to_code)
    if direct is not None:
        return {"rate": direct[0], "updated_at": direct[1]}

    reverse = _rate_entry(pairs, to_code, from_code)
    if reverse is not None:
        return {"rate": 1.0 / reverse[0], "updated_at": reverse[1]}

    if "USD" in (from_code, to_code):
        return None

    left = get_rate_info(from_code, "USD")
    right = get_rate_info(to_code, "USD")
    if left is None or right is None or right["rate"] <= 0:
        return None
    stamps = [item["updated_at"] for item in (left, right) if item.get("updated_at")]
    return {
        "rate": left["rate"] / right["rate"],
        "updated_at": min(stamps) if stamps else None,
    }


def get_rate_value(from_currency: str, to_currency: str) -> float | None:
    """Число курса FROM→TO или None, если посчитать нельзя."""
    info = get_rate_info(from_currency, to_currency)
    if info is None:
        return None
    return info["rate"]


def rate_is_fresh(updated_at: str | None, now: datetime | None = None) -> bool:
    """True, если метки нет или она не старше RATE_TTL_SECONDS."""
    if not updated_at:
        return True
    try:
        updated = _aware(datetime.fromisoformat(updated_at))
    except ValueError:
        return False
    current = _aware(now or datetime.now().astimezone())
    return (current - updated).total_seconds() <= RATE_TTL_SECONDS


def format_updated_at(updated_at: str | None) -> str:
    """Показывает сохранённое время, а не текущие часы."""
    if not updated_at:
        return "неизвестно"
    return updated_at.replace("T", " ")
