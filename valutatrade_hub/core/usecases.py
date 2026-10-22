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
    # Проверяем уникальность имени
    for u in users:
        if u.get("username", "").lower() == username.lower():
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    # Генерируем id и соль
    user_id = max((u.get("user_id", 0) for u in users), default=0) + 1
    salt = secrets.token_hex(16)
    # Временный объект только чтобы посчитать хеш
    temp_user = User(user_id, username, "", salt, datetime.now())
    temp_user.change_password(password)  # сам поставит хеш и новую соль

    user_data = {
        "user_id": user_id,
        "username": username,
        "hashed_password": temp_user.hashed_password,
        "salt": temp_user.salt,
        "registration_date": datetime.now().isoformat(timespec="seconds"),
    }
    users.append(user_data)
    save_users(users)

    # Создаём пустой портфель
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
    # Если портфеля нет — создаём пустой
    return Portfolio(user_id)


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
        # Считаем стоимость этого кошелька отдельно
        rate_key = f"{code}_{base}"
        rate = Portfolio._FAKE_RATES.get(rate_key, 0.0)
        value = wallet.balance * rate
        lines.append(f"- {code}: {wallet.balance:.4f} → {value:.2f} {base}")

    lines.append("---------------------------------")
    lines.append(f"ИТОГО: {total:.2f} {base}")
    return "\n".join(lines)