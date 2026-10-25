"""Бизнес-логика: регистрация, вход, операции с портфелем."""

import math
import secrets
from datetime import datetime

from ..decorators import log_action
from ..infra.database import DatabaseManager
from ..parser_service.storage import RatesStorage
from .exceptions import (
    AuthRequiredError,
    InsufficientFundsError,
    RateUnavailableError,
    UserError,
    ValidationError,
)
from .models import Portfolio, User, Wallet, get_currency, is_crypto_code
from .utils import (
    format_updated_at,
    get_rate_info,
    get_rate_value,
    rate_is_fresh,
)

db = DatabaseManager()


def _positive_number(value: object, name: str) -> float:
    """Отклоняет bool, NaN, бесконечность и неположительные числа."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"'{name}' должен быть положительным числом")
    if not math.isfinite(value) or value <= 0:
        raise ValidationError(f"'{name}' должен быть положительным числом")
    return float(value)


def _require_known(code: str) -> str:
    return get_currency(code).code


def _fresh_rate(from_code: str, to_code: str) -> float:
    """Курс для сделки. Устаревший курс сюда не проходит."""
    info = get_rate_info(from_code, to_code)
    if info is None or info["rate"] <= 0:
        raise RateUnavailableError(
            f"Не удалось получить курс для {from_code}→{to_code}"
        )
    if not rate_is_fresh(info.get("updated_at")):
        shown = format_updated_at(info.get("updated_at"))
        raise RateUnavailableError(
            f"Курс {from_code}→{to_code} устарел (обновлено: {shown}). "
            "Выполните update-rates или update-rate."
        )
    return info["rate"]


@log_action("register")
def register_user(username: str, password: str) -> str:
    """Регистрирует нового пользователя и создаёт пустой портфель."""
    username = username.strip() if username else ""
    if not username:
        raise ValidationError("Имя пользователя не может быть пустым")
    if not password or len(password) < 4:
        raise ValidationError("Пароль должен быть не короче 4 символов")

    users = db.load_users()
    for user in users:
        if user.get("username", "").lower() == username.lower():
            raise UserError(f"Имя пользователя '{username}' уже занято")

    user_id = max((user.get("user_id", 0) for user in users), default=0) + 1
    salt = secrets.token_hex(16)
    temp_user = User(user_id, username, "", salt, datetime.now())
    temp_user.change_password(password)

    users.append(
        {
            "user_id": user_id,
            "username": username,
            "hashed_password": temp_user.hashed_password,
            "salt": temp_user.salt,
            "registration_date": datetime.now().isoformat(timespec="seconds"),
        }
    )
    db.save_users(users)

    portfolios = db.load_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    db.save_portfolios(portfolios)

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


@log_action("login")
def login_user(username: str, password: str) -> User:
    """Проверяет имя и пароль. Возвращает User или бросает UserError."""
    username = username.strip() if username else ""
    if not username or not password:
        raise ValidationError("Нужно указать имя пользователя и пароль")

    found = None
    for user in db.load_users():
        if user.get("username", "").lower() == username.lower():
            found = user
            break

    if found is None:
        raise UserError(f"Пользователь '{username}' не найден")

    user = _user_from_dict(found)
    if not user.verify_password(password):
        raise UserError("Неверный пароль")
    return user


def load_portfolio(user: User) -> Portfolio:
    """Загружает портфель пользователя из JSON и собирает объекты Wallet."""
    portfolio = Portfolio(user)
    for item in db.load_portfolios():
        if item.get("user_id") != user.user_id:
            continue
        for code, wallet_data in item.get("wallets", {}).items():
            balance = wallet_data.get("balance", 0.0)
            portfolio._wallets[code] = Wallet(code, balance)
        break
    return portfolio


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет портфель обратно в portfolios.json."""
    portfolios = db.load_portfolios()
    wallets_dict = {
        code: {"balance": wallet.balance} for code, wallet in portfolio.wallets.items()
    }
    for item in portfolios:
        if item.get("user_id") == portfolio.user_id:
            item["wallets"] = wallets_dict
            db.save_portfolios(portfolios)
            return
    portfolios.append({"user_id": portfolio.user_id, "wallets": wallets_dict})
    db.save_portfolios(portfolios)


@log_action("show-portfolio")
def show_portfolio(user: User, base_currency: str = "USD") -> str:
    """Текстовое представление портфеля. Пустой портфель сообщает об этом."""
    if user is None:
        raise AuthRequiredError("Сначала выполните login")

    base = _require_known(base_currency)
    portfolio = load_portfolio(user)

    if not portfolio.wallets:
        return (
            f"Портфель пользователя '{user.username}' пуст. Купите валюту командой buy."
        )

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


@log_action("buy")
def buy_currency(user: User, currency: str, amount: float) -> str:
    """Покупает валюту и списывает эквивалент в USD."""
    if user is None:
        raise AuthRequiredError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValidationError("Нужно указать код валюты")
    amount = _positive_number(amount, "amount")

    code = _require_known(currency)
    if code == "USD":
        raise ValidationError("Нельзя купить USD за USD")

    portfolio = load_portfolio(user)
    rate = _fresh_rate(code, "USD")
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

    return (
        f"Покупка выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"- USD: было {old_usd:.2f} → стало {usd_wallet.balance:.2f}\n"
        f"Стоимость покупки: {cost:.2f} USD"
    )


@log_action("sell")
def sell_currency(user: User, currency: str, amount: float) -> str:
    """Продаёт валюту и зачисляет эквивалент в USD."""
    if user is None:
        raise AuthRequiredError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValidationError("Нужно указать код валюты")
    amount = _positive_number(amount, "amount")

    code = _require_known(currency)
    if code == "USD":
        raise ValidationError("Нельзя продать USD за USD")

    portfolio = load_portfolio(user)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise InsufficientFundsError(
            f"У вас нет кошелька '{code}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    rate = _fresh_rate(code, "USD")
    revenue = amount * rate
    old_balance = wallet.balance
    wallet.withdraw(amount)

    usd_wallet = portfolio.get_wallet("USD")
    if usd_wallet is None:
        usd_wallet = portfolio.add_currency("USD")
    old_usd = usd_wallet.balance
    usd_wallet.deposit(revenue)
    save_portfolio(portfolio)

    return (
        f"Продажа выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"- USD: было {old_usd:.2f} → стало {usd_wallet.balance:.2f}\n"
        f"Выручка: {revenue:.2f} USD"
    )


@log_action("get-rate")
def get_rate(from_currency: str, to_currency: str) -> str:
    """Возвращает курс одной валюты к другой из файла rates.json."""
    if not from_currency or not to_currency:
        raise ValidationError("Нужно указать обе валюты")

    from_code = _require_known(from_currency)
    to_code = _require_known(to_currency)
    rate = _fresh_rate(from_code, to_code)
    reverse_info = get_rate_info(to_code, from_code)
    reverse = reverse_info["rate"] if reverse_info else 1.0 / rate
    info = get_rate_info(from_code, to_code)
    updated = info.get("updated_at") if info else None
    shown = format_updated_at(updated) if updated else "неизвестно"
    return (
        f"Курс {from_code}→{to_code}: {rate:.8f} (обновлено: {shown})\n"
        f"Обратный курс {to_code}→{from_code}: {reverse:.8f}"
    )


@log_action("deposit")
def deposit(user: User, currency: str, amount: float) -> str:
    """Пополняет кошелёк известной валюты. Неизвестную не создаёт."""
    if user is None:
        raise AuthRequiredError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValidationError("Нужно указать код валюты")
    amount = _positive_number(amount, "amount")

    code = _require_known(currency)
    portfolio = load_portfolio(user)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)

    old_balance = wallet.balance
    wallet.deposit(amount)
    save_portfolio(portfolio)
    return (
        f"Пополнение выполнено: +{amount:.4f} {code}\n"
        f"{code}: было {old_balance:.4f} → стало {wallet.balance:.4f}"
    )


def show_rates(
    currency: str | None = None,
    top: int | None = None,
    base: str | None = None,
) -> str:
    """Курсы из кеша. --base пересчитывает пары, --top берёт дорогие криптовалюты."""
    document = RatesStorage().load()
    pairs = document.get("pairs", {})
    if not pairs:
        return "Курсы не загружены."

    code_filter = currency.strip().upper() if currency else ""
    if code_filter:
        _require_known(code_filter)
    base_code = _require_known(base) if base else "USD"

    items: list[tuple[str, float, str | None]] = []
    for key, value in pairs.items():
        if not isinstance(value, dict) or "rate" not in value:
            continue
        left, _, right = key.partition("_")
        if code_filter and code_filter not in (left, right):
            continue
        rate = get_rate_value(left, right)
        if rate is None:
            continue
        if base_code != right:
            bridge = get_rate_value(right, base_code)
            if bridge is None:
                raise RateUnavailableError(
                    f"Не удалось пересчитать курсы в {base_code}. "
                    "Сначала обновите курс этой валюты к USD."
                )
            rate *= bridge
        if left == base_code:
            continue
        items.append((f"{left}_{base_code}", rate, value.get("updated_at")))

    if top is not None:
        if isinstance(top, bool) or not isinstance(top, int) or top <= 0:
            raise ValidationError("'top' должен быть положительным целым числом")
        items = [item for item in items if is_crypto_code(item[0].split("_", 1)[0])]
        items.sort(key=lambda item: item[1], reverse=True)
        items = items[:top]

    if not items:
        if code_filter:
            return f"Курсы для {code_filter} не найдены."
        return "Курсы не загружены."

    lines = ["Текущие курсы:"]
    for key, rate, updated_at in items:
        lines.append(f"- {key}: {rate} (обновлено: {format_updated_at(updated_at)})")

    source = document.get("source") or "неизвестно"
    last = document.get("last_refresh")
    lines.append(f"Источник: {source}")
    lines.append(
        f"Последнее обновление: {format_updated_at(last) if last else 'неизвестно'}"
    )
    return "\n".join(lines)


@log_action("update-rate")
def update_rate(from_currency: str, to_currency: str, new_rate: float) -> str:
    """Вручную обновляет один курс в кеше."""
    if not from_currency or not to_currency:
        raise ValidationError("Нужно указать обе валюты")
    new_rate = _positive_number(new_rate, "rate")
    from_code = _require_known(from_currency)
    to_code = _require_known(to_currency)
    key = f"{from_code}_{to_code}"

    storage = RatesStorage()
    document = storage.load()
    now = datetime.now().isoformat(timespec="seconds")
    document["pairs"][key] = {"rate": float(new_rate), "updated_at": now}
    document["source"] = "manual"
    document["last_refresh"] = now
    storage.save(document)
    return f"Курс {key} обновлён: {new_rate} (время: {now})"
