from aiogram import types
from app.db import Database

db = Database()

async def start_registration(message: types.Message):
    # Начинаем регистрацию — сохраняем телефон из профиля Telegram
    phone = message.contact.phone_number if message.contact else None
    await db.add_or_update_applicant(telegram_id=message.from_user.id, phone=phone, step=1)
    await message.answer("Регистрация начата. Пожалуйста, введите ваш email:")

async def process_email(message: types.Message):
    email = message.text.strip()
    # Простейшая валидация email
    if "@" not in email or "." not in email:
        await message.answer("Введите корректный email.")
        return
    await db.add_or_update_applicant(telegram_id=message.from_user.id, email=email, step=2)
    await message.answer("Email сохранён. В этом тестовом варианте регистрация завершена.")
