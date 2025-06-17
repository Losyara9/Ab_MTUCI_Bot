import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

Path("logs").mkdir(exist_ok=True)


def make_rotating_logger(name, filename, fmt, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        handler = RotatingFileHandler(
            f"logs/{filename}", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S", style="{")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


api_logger = make_rotating_logger(
    name="api_logger",
    filename="api.log",
    fmt="[{asctime}] [TelegramID: {telegram_id}] [Username: {username}] "
        "[METHOD: {method}] [TYPE: {type}]\nDATA: {data}\n"
)


async def log_api_call(telegram_id: int, method: str, data: dict, *,
                       username: str = "-", type_: str = "request", response=None):
    api_logger.info("", extra={
        "telegram_id": telegram_id,
        "username": username or "-",
        "method": method,
        "type": type_,
        "data": data,
        "response": response
    })


bot_logger = make_rotating_logger(
    name="bot_logger",
    filename="bot.log",
    fmt="[{asctime}] [LEVEL: {levelname}] {message}",
)


def log_event(message: str):
    bot_logger.info(message)


def log_error(message: str):
    bot_logger.error(message)
