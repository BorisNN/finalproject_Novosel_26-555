"""Пользовательские исключения ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Базовая ошибка приложения. Её текст можно показать пользователю."""


class ValidationError(ValutaTradeError):
    """Неверные данные в команде или в модели."""


class UserError(ValutaTradeError):
    """Пользователь не найден, уже существует или неверный пароль."""


class InsufficientFundsError(ValutaTradeError):
    """Не хватает средств для операции."""


class RateUnavailableError(ValutaTradeError):
    """Курс недоступен или устарел."""


class AuthRequiredError(ValutaTradeError):
    """Команда доступна только после входа."""


class CurrencyNotFoundError(ValutaTradeError):
    """Кода нет в реестре валют."""
