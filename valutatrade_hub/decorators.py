"""Декоратор журнала действий."""

from collections.abc import Callable
from functools import wraps

from .logging_config import get_logger


def _context(action: str, args: tuple) -> str:
    """Контекст сделки без пароля."""
    parts: list[str] = []
    for arg in args:
        username = getattr(arg, "username", None)
        user_id = getattr(arg, "user_id", None)
        if isinstance(username, str) and isinstance(user_id, int):
            parts.append(f"user={username}")
    if (
        action in {"register", "login", "register_user", "login_user"}
        and args
        and isinstance(args[0], str)
    ):
        parts.append(f"username={args[0]}")
    if (
        action in {"buy", "sell", "deposit", "buy_currency", "sell_currency"}
        and len(args) >= 3
    ):
        parts.append(f"currency={args[1]}")
        parts.append(f"amount={args[2]}")
    if action in {"update-rate", "update_rate"} and len(args) >= 3:
        parts.append(f"pair={args[0]}_{args[1]}")
        parts.append(f"rate={args[2]}")
    return " ".join(parts)


def log_action(action: str | Callable | None = None) -> Callable:
    """Журнал OK/ERROR. Можно писать @log_action и @log_action(\"buy\")."""

    def decorator(func: Callable) -> Callable:
        label = action if isinstance(action, str) else func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            context = _context(label, args)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                logger.error("ERROR action=%s %s error=%s", label, context, exc)
                raise
            logger.info("OK action=%s %s", label, context)
            return result

        return wrapper

    if callable(action):
        function = action
        action = None
        return decorator(function)
    return decorator
