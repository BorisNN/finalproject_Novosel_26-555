"""Настройка логирования для ValutaTrade Hub."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> None:
    """Консоль и файл logs/app.log с ротацией."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            RotatingFileHandler(
                log_file,
                maxBytes=512_000,
                backupCount=3,
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    """Возвращает логгер с указанным именем."""
    return logging.getLogger(name)
