"""Модели предметной области: пользователи, кошельки, портфели."""

import hashlib
import math
import secrets
from datetime import datetime

from .currencies import get_currency, is_crypto_code
from .exceptions import InsufficientFundsError

__all__ = [
    "Portfolio",
    "User",
    "Wallet",
    "get_currency",
    "is_crypto_code",
]


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


class Wallet:
    """Кошелёк одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not currency_code or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        self._currency_code = currency_code.strip().upper()
        self.balance = balance

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if not math.isfinite(value):
            raise ValueError("Баланс должен быть конечным числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет баланс. Сумма должна быть положительной."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма пополнения должна быть положительным числом")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом")
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Снимает деньги, если их хватает."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма снятия должна быть положительным числом")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом")
        if amount > self.balance:
            raise InsufficientFundsError(
                "Недостаточно средств: "
                f"доступно {self.balance:.4f} {self.currency_code}, "
                f"требуется {amount:.4f} {self.currency_code}"
            )
        self.balance -= amount

    def get_balance_info(self) -> str:
        """Коротко показывает, сколько сейчас на кошельке."""
        return f"{self.currency_code}: {self.balance:.4f}"


class Portfolio:
    """Портфель пользователя — набор кошельков разных валют."""

    def __init__(self, user: User) -> None:
        if not isinstance(user, User):
            raise TypeError("Портфель создаётся только с объектом User")
        self._user = user
        self._wallets: dict[str, Wallet] = {}

    @property
    def user(self) -> User:
        return self._user

    @property
    def user_id(self) -> int:
        return self._user.user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Копия словаря, чтобы снаружи не меняли внутреннее хранилище."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелёк, если такой валюты ещё нет."""
        code = get_currency(currency_code).code
        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже есть в портфеле")
        wallet = Wallet(code, 0.0)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает кошелёк по коду валюты или None, если его нет."""
        if not currency_code:
            return None
        return self._wallets.get(currency_code.strip().upper())

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Считает общую стоимость всех кошельков в базовой валюте."""
        from .exceptions import RateUnavailableError
        from .utils import get_rate_value

        base = get_currency(base_currency).code
        total = 0.0
        missing: list[str] = []

        for code, wallet in self._wallets.items():
            if wallet.balance == 0:
                continue
            rate = get_rate_value(code, base)
            if rate is None:
                missing.append(code)
                continue
            total += wallet.balance * rate

        if missing:
            codes = ", ".join(missing)
            raise RateUnavailableError(f"Не удалось получить курс для {codes}→{base}")
        return total
