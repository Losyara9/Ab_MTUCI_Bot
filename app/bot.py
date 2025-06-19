import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from app.config import BOT_TOKEN
from app.db import Database
from app.handlers import register_handlers
from aiogram.fsm.storage.memory import MemoryStorage

db = Database()  # глобальная БД


async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    await db.connect()  # подключение к бд

    register_handlers(dp, db)  # регистрация обработчиков

    # команды бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать регистрацию"),
        BotCommand(command="help", description="Помощь и описание возможностей")
    ])

    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
