"""Бизнес-логика: регистрация, вход, операции с портфелем."""

import math
import secrets
from datetime import datetime

from ..logging_config import get_logger
from .exceptions import (
    AuthRequiredError,
    InsufficientFundsError,
    RateUnavailableError,
    UserError,
    ValidationError,
)
from .models import Portfolio, User, Wallet
from .utils import (
    format_updated_at,
    get_rate_info,
    get_rate_value,
    load_portfolios,
    load_rates,
    load_users,
    rate_is_fresh,
    save_portfolios,
    save_rates,
    save_users,
)

logger = get_logger(__name__)


def _positive_number(value: object, name: str) -> float:
    """Отклоняет bool, NaN, бесконечность и неположительные числа."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"'{name}' должен быть положительным числом")
    if not math.isfinite(value) or value <= 0:
        raise ValidationError(f"'{name}' должен быть положительным числом")
    return float(value)


def register_user(username: str, password: str) -> str:
    """
    Регистрирует нового пользователя.
    Создаёт пустой портфель.
    """
    username = username.strip() if username else ""
    if not username:
        raise ValidationError("Имя пользователя не может быть пустым")
    if not password or len(password) < 4:
        raise ValidationError("Пароль должен быть не короче 4 символов")

    users = load_users()
    for u in users:
        if u.get("username", "").lower() == username.lower():
            raise UserError(f"Имя пользователя '{username}' уже занято")

    user_id = max((u.get("user_id", 0) for u in users), default=0) + 1
    salt = secrets.token_hex(16)
    temp_user = User(user_id, username, "", salt, datetime.now())
    temp_user.change_password(password)

    user_data = {
        "user_id": user_id,
        "username": username,
        "hashed_password": temp_user.hashed_password,
        "salt": temp_user.salt,
        "registration_date": datetime.now().isoformat(timespec="seconds"),
    }
    users.append(user_data)
    save_users(users)

    # Пустой портфель, как в задании
    portfolios = load_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    save_portfolios(portfolios)

    logger.info("Зарегистрирован пользователь %s (id=%s)", username, user_id)
    return (
        f"Пользователь '{username}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {username} --password ****"
    )


def _user_from_dict(data: dict) -> User:
    """Собирает объект User из словаря, который лежит в users.json."""
    reg_date = datetime.fromisoformat(data["registration_date"])
    return User(
        user_id=data["user_id"],
        username=data["username"],
        hashed_password=data["hashed_password"],
        salt=data["salt"],
        registration_date=reg_date,
    )


def login_user(username: str, password: str) -> User:
    """
    Проверяет имя и пароль.
    Возвращает объект User при успехе или бросает UserError.
    """
    username = username.strip() if username else ""
    if not username or not password:
        raise ValidationError("Нужно указать имя пользователя и пароль")

    users = load_users()
    found = None
    for u in users:
        if u.get("username", "").lower() == username.lower():
            found = u
            break

    if found is None:
        raise UserError(f"Пользователь '{username}' не найден")

    user = _user_from_dict(found)
    if not user.verify_password(password):
        raise UserError("Неверный пароль")

    logger.info("Пользователь %s вошёл в систему", username)
    return user


def load_portfolio(user_id: int) -> Portfolio:
    """Загружает портфель пользователя из JSON и собирает объекты Wallet."""
    portfolios = load_portfolios()
    for p in portfolios:
        if p.get("user_id") == user_id:
            portfolio = Portfolio(user_id)
            wallets_data = p.get("wallets", {})
            for code, w_data in wallets_data.items():
                balance = w_data.get("balance", 0.0)
                wallet = Wallet(code, balance)
                portfolio._wallets[code] = wallet
            return portfolio
    return Portfolio(user_id)


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет портфель обратно в portfolios.json."""
    portfolios = load_portfolios()
    wallets_dict = {
        code: {"balance": wallet.balance}
        for code, wallet in portfolio.wallets.items()
    }
    found = False
    for p in portfolios:
        if p.get("user_id") == portfolio.user_id:
            p["wallets"] = wallets_dict
            found = True
            break
    if not found:
        portfolios.append({"user_id": portfolio.user_id, "wallets": wallets_dict})
    save_portfolios(portfolios)


def show_portfolio(user: User, base_currency: str = "USD") -> str:
    """
    Формирует текстовое представление портфеля.
    Если кошельков нет — говорит об этом.
    """
    if user is None:
        raise AuthRequiredError("Сначала выполните login")

    portfolio = load_portfolio(user.user_id)
    base = base_currency.strip().upper() if base_currency else "USD"

    if not portfolio.wallets:
        return f"Портфель пользователя '{user.username}' пуст. Купите валюту командой buy."

    lines = [f"Портфель пользователя '{user.username}' (база: {base}):"]
    total = 0.0

    for code, wallet in sorted(portfolio.wallets.items()):
        if wallet.balance == 0:
            lines.append(f"- {code}: {wallet.balance:.4f} → 0.00 {base}")
            continue
        rate = get_rate_value(code, base)
        if rate is None:
            raise RateUnavailableError(
                f"Не удалось получить курс для {code}→{base}. "
                "Задайте курс командой update-rate или укажите другую --base."
            )
        value = wallet.balance * rate
        total += value
        lines.append(f"- {code}: {wallet.balance:.4f} → {value:.2f} {base}")

    lines.append("---------------------------------")
    lines.append(f"ИТОГО: {total:.2f} {base}")
    return "\n".join(lines)


def buy_currency(user: User, currency: str, amount: float) -> str:
    """
    Покупает указанное количество валюты.
    Списывает эквивалент в USD с кошелька USD.
    """
    if user is None:
        raise AuthRequiredError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValidationError("Нужно указать код валюты")
    amount = _positive_number(amount, "amount")

    code = currency.strip().upper()
    if code == "USD":
        raise ValidationError("Нельзя купить USD за USD")

    portfolio = load_portfolio(user.user_id)

    rate = get_rate_value(code, "USD")
    if rate is None or rate <= 0:
        raise RateUnavailableError(f"Не удалось получить курс для {code}→USD")

    cost = amount * rate

    usd_wallet = portfolio.get_wallet("USD")
    if usd_wallet is None or usd_wallet.balance < cost:
        available = usd_wallet.balance if usd_wallet else 0.0
        raise InsufficientFundsError(
            f"Недостаточно USD: доступно {available:.2f}, требуется {cost:.2f}"
        )

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)

    old_balance = wallet.balance
    old_usd = usd_wallet.balance

    usd_wallet.withdraw(cost)
    wallet.deposit(amount)
    save_portfolio(portfolio)

    logger.info("Пользователь %s купил %.4f %s за %.2f USD", user.username, amount, code, cost)
    return (
        f"Покупка выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"- USD: было {old_usd:.2f} → стало {usd_wallet.balance:.2f}\n"
        f"Стоимость покупки: {cost:.2f} USD"
    )


def sell_currency(user: User, currency: str, amount: float) -> str:
    """
    Продаёт указанное количество валюты.
    Зачисляет эквивалент в USD на кошелёк USD.
    """
    if user is None:
        raise AuthRequiredError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValidationError("Нужно указать код валюты")
    amount = _positive_number(amount, "amount")

    code = currency.strip().upper()
    if code == "USD":
        raise ValidationError("Нельзя продать USD за USD")

    portfolio = load_portfolio(user.user_id)

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise InsufficientFundsError(
            f"У вас нет кошелька '{code}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    rate = get_rate_value(code, "USD")
    if rate is None or rate <= 0:
        raise RateUnavailableError(f"Не удалось получить курс для {code}→USD")

    revenue = amount * rate
    old_balance = wallet.balance

    wallet.withdraw(amount)

    usd_wallet = portfolio.get_wallet("USD")
    if usd_wallet is None:
        usd_wallet = portfolio.add_currency("USD")
    old_usd = usd_wallet.balance
    usd_wallet.deposit(revenue)

    save_portfolio(portfolio)

    logger.info("Пользователь %s продал %.4f %s за %.2f USD", user.username, amount, code, revenue)
    return (
        f"Продажа выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"- USD: было {old_usd:.2f} → стало {usd_wallet.balance:.2f}\n"
        f"Выручка: {revenue:.2f} USD"
    )


def get_rate(from_currency: str, to_currency: str) -> str:
    """
    Возвращает курс одной валюты к другой из файла rates.json.
    """
    if not from_currency or not to_currency:
        raise ValidationError("Нужно указать обе валюты")

    from_code = from_currency.strip().upper()
    to_code = to_currency.strip().upper()

    info = get_rate_info(from_code, to_code)
    if info is None:
        raise RateUnavailableError(
            f"Курс {from_code}→{to_code} недоступен. Повторите попытку позже."
        )

    updated = info.get("updated_at")
    if not rate_is_fresh(updated):
        shown = format_updated_at(updated)
        raise RateUnavailableError(
            f"Курс {from_code}→{to_code} устарел (обновлено: {shown}). "
            "Выполните update-rates или update-rate."
        )

    rate = info["rate"]
    reverse_info = get_rate_info(to_code, from_code)
    reverse = reverse_info["rate"] if reverse_info else (1.0 / rate if rate > 0 else None)
    shown = format_updated_at(updated) if updated else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Курс {from_code}→{to_code}: {rate:.8f} (обновлено: {shown})\n"
        f"Обратный курс {to_code}→{from_code}: {reverse:.8f}"
    )


def deposit(user: User, currency: str, amount: float) -> str:
    """
    Пополняет кошелёк указанной валюты.
    Если кошелька нет — создаёт его.
    """
    if user is None:
        raise AuthRequiredError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValidationError("Нужно указать код валюты")
    amount = _positive_number(amount, "amount")

    code = currency.strip().upper()
    portfolio = load_portfolio(user.user_id)

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)

    old_balance = wallet.balance
    wallet.deposit(amount)
    save_portfolio(portfolio)

    logger.info("Пользователь %s пополнил %s на %.4f", user.username, code, amount)
    return (
        f"Пополнение выполнено: +{amount:.4f} {code}\n"
        f"{code}: было {old_balance:.4f} → стало {wallet.balance:.4f}"
    )

def show_rates(currency: str | None = None, top: int | None = None) -> str:
    """Показывает курсы из rates.json. Можно сузить по валюте и взять top N."""
    rates = load_rates()
    if not rates:
        return "Курсы не загружены."

    code_filter = currency.strip().upper() if currency else ""
    items: list[tuple[str, dict]] = []
    for key, value in rates.items():
        if key in ("source", "last_refresh"):
            continue
        if not isinstance(value, dict) or "rate" not in value:
            continue
        if code_filter:
            left, _, right = key.partition("_")
            if code_filter not in (left, right):
                continue
        items.append((key, value))

    if top is not None:
        if isinstance(top, bool) or not isinstance(top, int) or top <= 0:
            raise ValidationError("'top' должен быть положительным целым числом")
        items.sort(key=lambda item: float(item[1]["rate"]), reverse=True)
        items = items[:top]

    if not items:
        if code_filter:
            return f"Курсы для {code_filter} не найдены."
        return "Курсы не загружены."

    lines = ["Текущие курсы:"]
    for key, value in items:
        updated = format_updated_at(value.get("updated_at"))
        lines.append(f"- {key}: {value['rate']} (обновлено: {updated})")

    source = rates.get("source", "неизвестно")
    last = format_updated_at(rates.get("last_refresh")) if rates.get("last_refresh") else "неизвестно"
    lines.append(f"Источник: {source}")
    lines.append(f"Последнее обновление: {last}")
    return "\n".join(lines)


def update_rate(from_currency: str, to_currency: str, new_rate: float) -> str:
    """
    Вручную обновляет один курс в rates.json.
    Пока это заглушка — позже её заменит парсер.
    """
    if not from_currency or not to_currency:
        raise ValidationError("Нужно указать обе валюты")
    new_rate = _positive_number(new_rate, "rate")

    from_code = from_currency.strip().upper()
    to_code = to_currency.strip().upper()
    key = f"{from_code}_{to_code}"

    rates = load_rates()
    now = datetime.now().isoformat(timespec="seconds")

    rates[key] = {
        "rate": float(new_rate),
        "updated_at": now,
    }
    rates["source"] = "manual"
    rates["last_refresh"] = now

    save_rates(rates)
    return f"Курс {key} обновлён: {new_rate} (время: {now})"
