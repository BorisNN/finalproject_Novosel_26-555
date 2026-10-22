"""Бизнес-логика: регистрация, вход, операции с портфелем."""

from datetime import datetime
import secrets

from .models import User, Portfolio, Wallet
from .utils import (
    load_users, save_users, load_portfolios, save_portfolios,
    load_rates, save_rates, get_rate_value,
)


def register_user(username: str, password: str) -> str:
    """
    Регистрирует нового пользователя.
    Создаёт пустой портфель.
    """
    username = username.strip() if username else ""
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    if not password or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = load_users()
    for u in users:
        if u.get("username", "").lower() == username.lower():
            raise ValueError(f"Имя пользователя '{username}' уже занято")

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
    Возвращает объект User при успехе или бросает ValueError.
    """
    username = username.strip() if username else ""
    if not username or not password:
        raise ValueError("Нужно указать имя пользователя и пароль")

    users = load_users()
    found = None
    for u in users:
        if u.get("username", "").lower() == username.lower():
            found = u
            break

    if found is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = _user_from_dict(found)
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

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
        raise ValueError("Сначала выполните login")

    portfolio = load_portfolio(user.user_id)
    base = base_currency.strip().upper() if base_currency else "USD"

    if not portfolio.wallets:
        return f"Портфель пользователя '{user.username}' пуст. Купите валюту командой buy."

    lines = [f"Портфель пользователя '{user.username}' (база: {base}):"]
    total = 0.0

    for code, wallet in sorted(portfolio.wallets.items()):
        rate = get_rate_value(code, base)
        if rate is None:
            rate = 0.0
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
        raise ValueError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValueError("Нужно указать код валюты")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    code = currency.strip().upper()
    if code == "USD":
        raise ValueError("Нельзя купить USD за USD")

    portfolio = load_portfolio(user.user_id)

    rate = get_rate_value(code, "USD")
    if rate is None or rate <= 0:
        raise ValueError(f"Не удалось получить курс для {code}→USD")

    cost = amount * rate

    usd_wallet = portfolio.get_wallet("USD")
    if usd_wallet is None or usd_wallet.balance < cost:
        available = usd_wallet.balance if usd_wallet else 0.0
        raise ValueError(
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


def sell_currency(user: User, currency: str, amount: float) -> str:
    """
    Продаёт указанное количество валюты.
    Зачисляет эквивалент в USD на кошелёк USD.
    """
    if user is None:
        raise ValueError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValueError("Нужно указать код валюты")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    code = currency.strip().upper()
    if code == "USD":
        raise ValueError("Нельзя продать USD за USD")

    portfolio = load_portfolio(user.user_id)

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    rate = get_rate_value(code, "USD")
    if rate is None or rate <= 0:
        raise ValueError(f"Не удалось получить курс для {code}→USD")

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


def get_rate(from_currency: str, to_currency: str) -> str:
    """
    Возвращает курс одной валюты к другой из файла rates.json.
    """
    if not from_currency or not to_currency:
        raise ValueError("Нужно указать обе валюты")

    from_code = from_currency.strip().upper()
    to_code = to_currency.strip().upper()

    rate = get_rate_value(from_code, to_code)
    if rate is None:
        raise ValueError(f"Курс {from_code}→{to_code} недоступен. Повторите попытку позже.")

    reverse = get_rate_value(to_code, from_code)
    if reverse is None and rate > 0:
        reverse = 1.0 / rate

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Курс {from_code}→{to_code}: {rate:.8f} (обновлено: {now})\n"
        f"Обратный курс {to_code}→{from_code}: {reverse:.8f}"
    )


def deposit(user: User, currency: str, amount: float) -> str:
    """
    Пополняет кошелёк указанной валюты.
    Если кошелька нет — создаёт его.
    """
    if user is None:
        raise ValueError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValueError("Нужно указать код валюты")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    code = currency.strip().upper()
    portfolio = load_portfolio(user.user_id)

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

def deposit(user: User, currency: str, amount: float) -> str:
    """
    Пополняет кошелёк указанной валюты.
    Если кошелька нет — создаёт его.
    """
    if user is None:
        raise ValueError("Сначала выполните login")
    if not currency or not currency.strip():
        raise ValueError("Нужно указать код валюты")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    code = currency.strip().upper()
    portfolio = load_portfolio(user.user_id)

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


def show_rates() -> str:
    """Показывает все курсы из rates.json."""
    rates = load_rates()
    if not rates:
        return "Курсы не загружены."

    lines = ["Текущие курсы:"]
    for key, value in rates.items():
        if key in ("source", "last_refresh"):
            continue
        if isinstance(value, dict) and "rate" in value:
            updated = value.get("updated_at", "неизвестно")
            lines.append(f"- {key}: {value['rate']} (обновлено: {updated})")

    source = rates.get("source", "неизвестно")
    last = rates.get("last_refresh", "неизвестно")
    lines.append(f"Источник: {source}")
    lines.append(f"Последнее обновление: {last}")
    return "\n".join(lines)


def update_rate(from_currency: str, to_currency: str, new_rate: float) -> str:
    """
    Вручную обновляет один курс в rates.json.
    Пока это заглушка — позже её заменит парсер.
    """
    if not from_currency or not to_currency:
        raise ValueError("Нужно указать обе валюты")
    if not isinstance(new_rate, (int, float)) or new_rate <= 0:
        raise ValueError("Курс должен быть положительным числом")

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