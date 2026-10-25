"""Пользовательские исключения ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Базовое исключение проекта."""


class ValidationError(ValutaTradeError):
    """Ошибка валидации входных данных."""


class UserError(ValutaTradeError):
    """Ошибки, связанные с пользователями (регистрация, вход)."""


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств на счёте."""


class RateUnavailableError(ValutaTradeError):
    """Курс валюты недоступен."""


class AuthRequiredError(ValutaTradeError):
    """Операция требует авторизации."""
