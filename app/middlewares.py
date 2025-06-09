from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.db import Database


class InjectDatabaseMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        self.db = db
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db  # 👈 передаём db в data
        return await handler(event, data)
