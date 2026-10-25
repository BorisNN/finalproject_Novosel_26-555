"""Точка входа в приложение ValutaTrade Hub."""

from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.cli.interface import run


def main() -> None:
    setup_logging()
    run()


if __name__ == "__main__":
    main()