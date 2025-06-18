from aiogram import Bot
from app.config import BOT_TOKEN
from app.db import Database
from app.logger import log_event, log_error
import logging

logger = logging.getLogger("bot_logger")
print(" === bot_logger handlers ===", logger.handlers)

db = Database()

bot = Bot(token=BOT_TOKEN)


async def notify_applicants(notifications: list[dict]):
    failed_phones = []

    await db.connect()

    print("Вход в notify_applicants")

    for item in notifications:
        phone = item["applicant_phone"]
        message = item["message"]

        print(f"Попытка отправить сообщение {message} на телефон {phone}")

        try:
            user = await db.get_applicant_by_phone(phone)
            if not user or not user.get("telegram_id"):
                log_error(f"[Notify] Не найден Telegram ID для абитуриента {phone}")
                failed_phones.append(phone)
                continue

            await bot.send_message(user["telegram_id"], message)
            log_event(f"[Notify] Сообщение отправлено абитуриенту с номером {phone}")
        except Exception as e:
            log_error(f"[Notify] Ошибка при отправке сообщения абитуриенту {phone}: {e}")
            failed_phones.append(phone)

    print(f"Список неудачников: {failed_phones}")

    return failed_phones
