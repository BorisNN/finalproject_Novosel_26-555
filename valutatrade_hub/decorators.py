"""Декоратор журнала действий."""

from collections.abc import Callable
from contextvars import ContextVar
from datetime import datetime
from functools import wraps

from .logging_config import get_logger

_fields: ContextVar[dict | None] = ContextVar("log_action_fields", default=None)


def set_log_fields(**fields: object) -> None:
    """Дописывает rate, base и подробности до выхода из buy/sell/get-rate."""
    current = dict(_fields.get() or {})
    current.update(fields)
    _fields.set(current)


def _pull(args: tuple, name: str) -> str:
    for arg in args:
        username = getattr(arg, "username", None)
        user_id = getattr(arg, "user_id", None)
        if name == "user" and isinstance(username, str) and isinstance(user_id, int):
            return username
    return ""


def _value(args: tuple, kwargs: dict, index: int, key: str) -> str:
    if key in kwargs and kwargs[key] not in (None, ""):
        return str(kwargs[key])
    if len(args) > index and isinstance(args[index], (str, int, float)):
        if isinstance(args[index], bool):
            return ""
        return str(args[index])
    return ""


def log_action(
    action: str | Callable | None = None,
    *,
    verbose: bool = False,
) -> Callable:
    """Журнал BUY/SELL. Исключение пишется и пробрасывается дальше.

    verbose=True добавляет поле detail, если операция вызвала set_log_fields.
    """

    def decorator(func: Callable) -> Callable:
        label = action if isinstance(action, str) else func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            token = _fields.set({})
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                extra = _fields.get() or {}
                logger.info("%s", _line(label, args, kwargs, extra, exc, verbose))
                raise
            else:
                extra = _fields.get() or {}
                logger.info("%s", _line(label, args, kwargs, extra, None, verbose))
                return result
            finally:
                _fields.reset(token)

        return wrapper

    if callable(action):
        function = action
        action = None
        return decorator(function)
    return decorator


def _line(
    label: str,
    args: tuple,
    kwargs: dict,
    extra: dict,
    error: BaseException | None,
    verbose: bool,
) -> str:
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    parts = [stamp, label.upper()]
    user = extra.get("user") or _pull(args, "user")
    if not user and args and isinstance(args[0], str):
        user = args[0]
    if user:
        parts.append(f"user='{user}'")
    trade = label.lower() in {"buy", "sell", "deposit"}
    currency = extra.get("currency") or ""
    if not currency and trade:
        currency = _value(args, kwargs, 1, "currency")
    if currency:
        parts.append(f"currency='{currency}'")
    amount = extra.get("amount")
    if amount is None and trade:
        amount = _value(args, kwargs, 2, "amount")
    if amount not in ("", None):
        parts.append(f"amount={amount}")
    if label.lower() == "update-rate" and len(args) >= 3:
        parts.append(f"pair={args[0]}_{args[1]}")
        parts.append(f"rate={args[2]}")
    rate = extra.get("rate", kwargs.get("rate"))
    if rate not in (None, "") and label.lower() != "update-rate":
        parts.append(f"rate={rate}")
    base = extra.get("base", kwargs.get("base"))
    if base not in (None, ""):
        parts.append(f"base='{base}'")
    if error is None:
        parts.append("result=OK")
    else:
        parts.append("result=ERROR")
        parts.append(f"error_type={type(error).__name__}")
        parts.append(f"error_message={error}")
    if verbose and extra.get("detail"):
        parts.append(f"detail={extra['detail']}")
    return " ".join(str(part) for part in parts)
