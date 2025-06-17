import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

Path("logs").mkdir(exist_ok=True)

logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    "logs/api.log",
    maxBytes=1_000_000,
    backupCount=5,
    encoding="utf-8")

formatter = logging.Formatter(
    fmt="[{asctime}] [TelegramID: {telegram_id}] "
        "[Username: {username}] [METHOD: {method}] [TYPE: {type}]\nDATA: {data}\n",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


async def log_api_call(telegram_id: int, method: str, data: dict, *, username: str = "-",
                       type_: str = "request", response=None):
    logger.info("", extra={
        "telegram_id": telegram_id,
        "username": username or "-",
        "method": method,
        "type": type_,
        "data": data,
        "response": response
    })


general_logger = logging.getLogger("general_logger")
general_logger.setLevel(logging.INFO)

if not general_logger.hasHandlers():
    general_handler = RotatingFileHandler(
        "logs/general.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )

    general_formatter = logging.Formatter(
        fmt="[{asctime}] [LEVEL: {levelname}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{"
    )

    general_handler.setFormatter(general_formatter)
    general_logger.addHandler(general_handler)


def log_event(message: str):
    general_logger.info(message)


def log_error(message: str):
    general_logger.error(message)
