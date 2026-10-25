"""Хранение курсов и истории."""

import json
import os
from pathlib import Path

from ..infra.settings import SettingsLoader

_META_KEYS = {"pairs", "last_refresh", "source"}


def _atomic_write(path: Path, data) -> None:
    """Пишет JSON во временный файл и затем заменяет основной."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _empty_document() -> dict:
    return {"pairs": {}, "last_refresh": None, "source": None}


class RatesStorage:
    """Кеш курсов в rates.json и история в exchange_rates.json.

    Клиенты и этот объект передаются в RatesUpdater, а не создаются внутри него.
    """

    def __init__(
        self,
        path: Path | None = None,
        history_path: Path | None = None,
    ) -> None:
        settings = SettingsLoader()
        self.path = path or settings.rates_file
        self.history_path = history_path or settings.history_file

    def load(self) -> dict:
        """Возвращает {"pairs", "last_refresh", "source"}.

        Старый плоский файл без ключа pairs тоже читается.
        """
        if not self.path.exists():
            return _empty_document()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return _empty_document()
        if not isinstance(raw, dict):
            return _empty_document()
        if "pairs" in raw and isinstance(raw.get("pairs"), dict):
            return {
                "pairs": dict(raw["pairs"]),
                "last_refresh": raw.get("last_refresh"),
                "source": raw.get("source"),
            }
        pairs = {
            key: value
            for key, value in raw.items()
            if key not in _META_KEYS and isinstance(value, dict)
        }
        return {
            "pairs": pairs,
            "last_refresh": raw.get("last_refresh"),
            "source": raw.get("source"),
        }

    def save(self, document: dict) -> None:
        """Атомарно сохраняет кеш и дописывает снимок в историю."""
        payload = {
            "pairs": document.get("pairs", {}),
            "last_refresh": document.get("last_refresh"),
            "source": document.get("source"),
        }
        _atomic_write(self.path, payload)
        self._append_history(payload)

    def _append_history(self, payload: dict) -> None:
        history: list = []
        if self.history_path.exists():
            try:
                loaded = json.loads(self.history_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    history = loaded
            except (json.JSONDecodeError, OSError):
                history = []
        known = {
            item.get("id")
            for item in history
            if isinstance(item, dict) and item.get("id")
        }
        source = payload.get("source") or "unknown"
        added = False
        for key, value in payload.get("pairs", {}).items():
            if not isinstance(value, dict) or "_" not in key:
                continue
            left, _, right = key.partition("_")
            rate = value.get("rate")
            stamp = value.get("updated_at")
            if not left or not right or not isinstance(stamp, str):
                continue
            if isinstance(rate, bool) or not isinstance(rate, (int, float)):
                continue
            record_id = f"{left}_{right}_{stamp}"
            if record_id in known:
                continue
            history.append(
                {
                    "id": record_id,
                    "from_currency": left,
                    "to_currency": right,
                    "rate": float(rate),
                    "timestamp": stamp,
                    "source": value.get("source") or source,
                }
            )
            known.add(record_id)
            added = True
        if added:
            _atomic_write(self.history_path, history[-500:])
