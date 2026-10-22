"""Бизнес-логика: регистрация, вход, операции с портфелем."""

from datetime import datetime
import secrets

from .models import User, Portfolio, Wallet
from .utils import load_users, save_users, load_portfolios, save_portfolios


def register_user(username: str, password: str) -> str:
    """
    Регистрирует нового пользователя.
    Возвращает сообщение об успехе или бросает ValueError.
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

    portfolios = load_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    save_portfolios(portfolios)

    return f"Пользователь '{username}' зарегистрирован (id={user_id}). Войдите: login --username {username} --password ****"


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
    total = portfolio.get_total_value(base)

    for code, wallet in sorted(portfolio.wallets.items()):
        rate_key = f"{code}_{base}"
        rate = Portfolio._FAKE_RATES.get(rate_key, 0.0)
        value = wallet.balance * rate
        lines.append(f"- {code}: {wallet.balance:.4f} → {value:.2f} {base}")

    lines.append("---------------------------------")
    lines.append(f"ИТОГО: {total:.2f} {base}")
    return "\n".join(lines)


def buy_currency(user: User, currency: str, amount: float) -> str:
    """
    Покупает указанное количество валюты.
    Пока просто добавляет на кошелёк (без списания USD — это добавим позже, когда будет полноценный обмен).
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

    # Оценочная стоимость по фиксированному курсу
    rate = Portfolio._FAKE_RATES.get(f"{code}_USD", 0.0)
    cost = amount * rate

    return (
        f"Покупка выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"Оценочная стоимость покупки: {cost:.2f} USD"
    )


def sell_currency(user: User, currency: str, amount: float) -> str:
    """
    Продаёт указанное количество валюты.
    Пока просто снимает с кошелька (зачисление USD добавим позже).
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
        raise ValueError(f"У вас нет кошелька '{code}'. Добавьте валюту: она создаётся автоматически при первой покупке.")

    old_balance = wallet.balance
    wallet.withdraw(amount)  # сам проверит, хватает ли
    save_portfolio(portfolio)

    rate = Portfolio._FAKE_RATES.get(f"{code}_USD", 0.0)
    revenue = amount * rate

    return (
        f"Продажа выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"Оценочная выручка: {revenue:.2f} USD"
    )