"""ValutaTrade Hub — консольный учёт валютного портфеля."""


def main() -> None:
    """Точка входа команды valutatrade-hub и main.py."""
    from .cli.interface import run
    from .logging_config import setup_logging

    setup_logging()
    run()
