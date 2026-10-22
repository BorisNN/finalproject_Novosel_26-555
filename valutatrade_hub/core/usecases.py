"""Бизнес-логика: регистрация, вход, операции с портфелем."""

from datetime import datetime
import secrets

from .models import User, Portfolio
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