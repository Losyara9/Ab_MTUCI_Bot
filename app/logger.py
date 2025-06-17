import logging
from datetime import datetime
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)

handler = logging.FileHandler("logs/api.log", encoding="utf-8")
formatter = logging.Formatter(
    fmt="[{asctime}] [TelegramID: {telegram_id}] [Username: {username}] [METHOD: {method}] [TYPE: {type}]\nDATA: {data}\n",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

async def log_api_call(telegram_id: int, method: str, data: dict, *, username: str = "-", type_: str = "request"):
    logger.info("", extra={
        "telegram_id": telegram_id,
        "username": username or "-",
        "method": method,
        "type": type_,
        "data": data
    })
