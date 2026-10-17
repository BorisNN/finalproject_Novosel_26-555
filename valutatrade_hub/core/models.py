"""Модели предметной области: пользователи, кошельки, портфели."""

from datetime import datetime
import hashlib
import secrets


class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self._user_id = user_id
        self.username = username         
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    # геттеры и сеттеры

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    # методы

    def get_user_info(self) -> str:
        """Возвращает информацию о пользователе без пароля."""
        date_str = self._registration_date.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"Пользователь: {self._username} (id={self._user_id}), "
            f"зарегистрирован: {date_str}"
        )

    def change_password(self, new_password: str) -> None:
        """Меняет пароль: генерирует новую соль и считает хеш."""
        if not new_password or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        # Новая соль на каждый смену пароля
        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли введённый пароль с сохранённым хешем."""
        if not password:
            return False
        return self._hash_password(password, self._salt) == self._hashed_password

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Простой односторонний хеш: SHA-256 от password + salt."""
        data = (password + salt).encode("utf-8")
        return hashlib.sha256(data).hexdigest()