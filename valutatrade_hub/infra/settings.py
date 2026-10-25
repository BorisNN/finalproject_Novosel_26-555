"""Единая точка настроек проекта. Синглтон через __new__."""

import json
from pathlib import Path
from typing import Any, Self

# Корень проекта: папка, где лежат main.py и data/.
ROOT = Path(__file__).resolve().parent.parent.parent


class SettingsLoader:
    """Один объект на всё приложение.

    __new__ выбран потому, что он проще метакласса:
    повторный вызов SettingsLoader() возвращает тот же объект,
    даже если импорт случился из разных модулей.
    """

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            created = super().__new__(cls)
            created._ready = False
            cls._instance = created
        return cls._instance

    def __init__(self) -> None:
        # __init__ вызывается при каждом SettingsLoader(),
        # поэтому загрузку делаем только один раз.
        if self._ready:
            return
        self._data: dict[str, Any] = {}
        self.reload()
        self._ready = True

    def reload(self) -> None:
        """Перечитывает config.json поверх значений по умолчанию."""
        defaults: dict[str, Any] = {
            "data_dir": "data",
            "users_file": "data/users.json",
            "portfolios_file": "data/portfolios.json",
            "rates_file": "data/rates.json",
            "history_file": "data/exchange_rates.json",
            "logs_dir": "logs",
            "rates_ttl_seconds": 3600,
            "base_currency": "USD",
            "log_level": "INFO",
        }
        path = ROOT / "config.json"
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    defaults.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
        self._data = defaults

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает настройку по ключу или default, если ключа нет."""
        return self._data.get(key, default)

    def _resolve(self, key: str, default: str) -> Path:
        raw = Path(str(self.get(key, default)))
        if raw.is_absolute():
            return raw
        return ROOT / raw

    @property
    def rates_file(self) -> Path:
        """Абсолютный путь к data/rates.json."""
        return self._resolve("rates_file", "data/rates.json")

    @property
    def history_file(self) -> Path:
        """Абсолютный путь к data/exchange_rates.json."""
        return self._resolve("history_file", "data/exchange_rates.json")

    @property
    def rates_ttl_seconds(self) -> int:
        """Срок годности курса в секундах. Битый ключ не принимается."""
        value = self.get("rates_ttl_seconds", 3600)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return 3600
        return value
