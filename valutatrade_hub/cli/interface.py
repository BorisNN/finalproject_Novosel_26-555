"""Простой командный интерфейс ValutaTrade Hub."""

import shlex

from ..core.usecases import (
    register_user,
    login_user,
    show_portfolio,
    buy_currency,
    sell_currency,
    get_rate,
    deposit,
    show_rates,
    update_rate,
)
from ..core.models import User


# Текущая сессия (пока просто переменная в памяти)
current_user: User | None = None


def parse_args(parts: list[str]) -> dict[str, str]:
    """Простой разбор аргументов вида --key value."""
    args = {}
    i = 0
    while i < len(parts):
        if parts[i].startswith("--") and i + 1 < len(parts):
            key = parts[i][2:]
            args[key] = parts[i + 1]
            i += 2
        else:
            i += 1
    return args


def handle_command(line: str) -> str:
    """Обрабатывает одну команду и возвращает текст ответа."""
    global current_user

    line = line.strip()
    if not line:
        return ""

    try:
        parts = shlex.split(line)
    except ValueError:
        return "Ошибка: незакрытая кавычка"

    if not parts:
        return ""

    cmd = parts[0].lower()
    args = parse_args(parts[1:])

    try:
        if cmd == "register":
            username = args.get("username", "")
            password = args.get("password", "")
            return register_user(username, password)

        elif cmd == "login":
            username = args.get("username", "")
            password = args.get("password", "")
            user = login_user(username, password)
            current_user = user
            return f"Вы вошли как '{user.username}'"

        elif cmd == "logout":
            if current_user is None:
                return "Вы и так не вошли в систему"
            name = current_user.username
            current_user = None
            return f"Вы вышли из аккаунта '{name}'"

        elif cmd == "show-portfolio":
            if current_user is None:
                return "Сначала выполните login"
            base = args.get("base", "USD")
            return show_portfolio(current_user, base)

        elif cmd == "deposit":
            if current_user is None:
                return "Сначала выполните login"
            currency = args.get("currency", "")
            amount_str = args.get("amount", "")
            if not amount_str:
                return "Нужно указать --amount"
            try:
                amount = float(amount_str)
            except ValueError:
                return "'amount' должен быть числом"
            return deposit(current_user, currency, amount)

        elif cmd == "buy":
            if current_user is None:
                return "Сначала выполните login"
            currency = args.get("currency", "")
            amount_str = args.get("amount", "")
            if not amount_str:
                return "Нужно указать --amount"
            try:
                amount = float(amount_str)
            except ValueError:
                return "'amount' должен быть числом"
            return buy_currency(current_user, currency, amount)

        elif cmd == "sell":
            if current_user is None:
                return "Сначала выполните login"
            currency = args.get("currency", "")
            amount_str = args.get("amount", "")
            if not amount_str:
                return "Нужно указать --amount"
            try:
                amount = float(amount_str)
            except ValueError:
                return "'amount' должен быть числом"
            return sell_currency(current_user, currency, amount)

        elif cmd == "get-rate":
            from_cur = args.get("from", "")
            to_cur = args.get("to", "")
            return get_rate(from_cur, to_cur)

        elif cmd == "show-rates":
            return show_rates()

        elif cmd == "update-rate":
            from_cur = args.get("from", "")
            to_cur = args.get("to", "")
            rate_str = args.get("rate", "")
            if not rate_str:
                return "Нужно указать --rate"
            try:
                new_rate = float(rate_str)
            except ValueError:
                return "'rate' должен быть числом"
            return update_rate(from_cur, to_cur, new_rate)

        elif cmd in ("exit", "quit"):
            return "exit"

        elif cmd == "help":
            return (
                "Доступные команды:\n"
                "  register --username NAME --password PASS\n"
                "  login --username NAME --password PASS\n"
                "  logout\n"
                "  show-portfolio [--base USD]\n"
                "  deposit --currency CODE --amount NUMBER\n"
                "  buy --currency CODE --amount NUMBER\n"
                "  sell --currency CODE --amount NUMBER\n"
                "  get-rate --from CODE --to CODE\n"
                "  show-rates\n"
                "  update-rate --from CODE --to CODE --rate NUMBER\n"
                "  exit"
            )

        else:
            return f"Неизвестная команда: {cmd}. Напишите help"

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Ошибка: {e}"


def run() -> None:
    """Запускает цикл чтения команд."""
    print("ValutaTrade Hub. Напишите help для списка команд.")
    while True:
        # Показываем, кто сейчас залогинен
        prompt = f"{current_user.username}> " if current_user else "> "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        result = handle_command(line)
        if result == "exit":
            break
        if result:
            print(result)