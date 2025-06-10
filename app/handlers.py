from aiogram import types, F, Router, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
import re
from app.states import Registration, Menu
from app.db import Database
from app.middlewares import InjectDatabaseMiddleware
from app.email_utils import send_error_report

router = Router()

async def is_registered(telegram_id: int, db: Database) -> bool: # проверка на регистрацию
    applicant = await db.get_applicant(telegram_id)
    return applicant is not None

def register_handlers(dp: Dispatcher, db: Database): # вызов регистрации
    router.message.middleware(InjectDatabaseMiddleware(db))
    dp.include_router(router)

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, db: Database):
    await state.clear()
    telegram_id = message.from_user.id

    if await is_registered(telegram_id, db):
        await message.answer("Вы уже зарегистрированы ✅")
        await menu_command(message, state)
    else:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Начать")]
            ],
            resize_keyboard=True
        )
        await message.answer("Привет! Для начала регистрации нажмите кнопку 'Начать'.", reply_markup=keyboard)


@router.message(F.text.casefold() == "начать") # отправка номера телефона
async def start_registration(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Пожалуйста, отправьте ваш номер телефона:", reply_markup=keyboard)
    await state.set_state(Registration.waiting_for_phone)

@router.message(F.contact)
async def phone_received(message: types.Message, state: FSMContext, **kwargs):
    db: Database = kwargs["db"]
    phone = message.contact.phone_number

    await db.add_or_update_applicant(
        telegram_id=message.from_user.id,
        phone=phone,
        step=1
    )
    await state.update_data(phone=phone)
    await message.answer("Спасибо! Теперь введите вашу почту.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.waiting_for_email)

def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

@router.message(Registration.waiting_for_email)
async def email_received(message: types.Message, state: FSMContext, **kwargs):
    db: Database = kwargs["db"]
    email = message.text.strip()

    if not is_valid_email(email):
        await message.answer("Неверный формат email. Пожалуйста, введите корректный адрес электронной почты.")
        return

    await state.update_data(email=email)
    await db.add_or_update_applicant(telegram_id=message.from_user.id, email=email, step=2)

    await message.answer("Спасибо! Введите ваше ФИО.")
    await state.set_state(Registration.waiting_for_fullname)

@router.message(Registration.waiting_for_fullname)
async def fullname_received(message: types.Message, state: FSMContext, **kwargs):
    db: Database = kwargs["db"]
    fullname = message.text
    await state.update_data(fullname=fullname)

    # Записываем fullname в БД
    await db.add_or_update_applicant(
        telegram_id=message.from_user.id,
        fullname=fullname,
        step=2  # или другой шаг, если нужно
    )

    await message.answer("Теперь введите ваш ИНН.")
    await state.set_state(Registration.waiting_for_inn)

def is_valid_inn(inn: str) -> bool: # проверка ввода инн
    return inn.isdigit() and len(inn) == 12

@router.message(Registration.waiting_for_inn)
async def inn_received(message: types.Message, state: FSMContext, **kwargs):
    db: Database = kwargs["db"]
    inn = message.text.strip()

    if not is_valid_inn(inn):
        await message.answer("ИНН должен содержать ровно 12 цифр. Пожалуйста, введите корректный ИНН.")
        return

    user_data = await state.get_data()
    await state.update_data(inn=inn)

    await db.add_or_update_applicant(
        telegram_id=message.from_user.id,
        phone=user_data.get("phone"),
        email=user_data.get("email"),
        inn=inn,
        step=3
    )

    await message.answer("Регистрация завершена! Спасибо.")
    await menu_command(message, state)


@router.message(Command("menu"))
async def menu_command(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📋 Получить информацию")],
            [types.KeyboardButton(text="✏ Изменить ИНН"), types.KeyboardButton(text="✏ Изменить Email")],
            [types.KeyboardButton(text="🛠 Сообщить об ошибке")],
        ],
        resize_keyboard=True
    )
    await state.set_state(Menu.main)
    await message.answer("Добро пожаловать в личный кабинет. Выберите действие:", reply_markup=keyboard)


@router.message(lambda message: message.text == "🔙 Назад")
async def back_to_menu(message: types.Message, state: FSMContext, **kwargs):
    await menu_command(message, state)


@router.message(Menu.main, F.text == "📋 Получить информацию")
async def choose_info_type(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Заявление и статус")],
            [types.KeyboardButton(text="Вступительные экзамены")],
            [types.KeyboardButton(text="Результаты ЕГЭ")],
            [types.KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    await state.set_state(Menu.choose_info_type)
    await message.answer("Что вы хотите узнать?", reply_markup=keyboard)

@router.message(Menu.choose_info_type)
async def info_handler(message: types.Message):
    text = message.text
    if text == "Заявление и статус":
        await message.answer("📝 Ваше заявление подано. Статус: Ожидает рассмотрения.")
    elif text == "Вступительные экзамены":
        await message.answer("📚 Вступительные экзамены: Математика, Физика. Назначены на 15 июля.")
    elif text == "Результаты ЕГЭ":
        await message.answer("📊 Математика: 80, Русский: 75, Информатика: 90.")
    elif text == "🔙 Назад":
        await menu_command(message, state=None)

@router.message(Menu.main, F.text == "✏ Изменить ИНН")
async def start_change_inn(message: types.Message, state: FSMContext):
    await state.set_state(Menu.change_inn)
    await message.answer("Введите новый ИНН:")

@router.message(Menu.change_inn)
async def save_new_inn(message: types.Message, state: FSMContext, **kwargs):
    inn = message.text.strip()
    if not is_valid_inn(inn):
        await message.answer("❗ ИНН должен содержать ровно 12 цифр. Попробуйте снова.")
        return
    db: Database = kwargs["db"]
    await db.add_or_update_applicant(telegram_id=message.from_user.id, inn=inn)
    await message.answer("ИНН обновлён ✅")
    await menu_command(message, state)

@router.message(Menu.main, F.text == "✏ Изменить Email")
async def start_change_email(message: types.Message, state: FSMContext):
    await state.set_state(Menu.change_email)
    await message.answer("Введите новый email:")

@router.message(Menu.change_email)
async def save_new_email(message: types.Message, state: FSMContext, **kwargs):
    email = message.text.strip()
    if not is_valid_email(email):
        await message.answer("❗ Неверный формат email. Попробуйте снова.")
        return
    db: Database = kwargs["db"]
    await db.add_or_update_applicant(telegram_id=message.from_user.id, email=email)
    await message.answer("Email обновлён ✅")
    await menu_command(message, state)

@router.message(Menu.main, F.text == "🛠 Сообщить об ошибке")
async def report_start(message: types.Message, state: FSMContext):
    await state.set_state(Menu.report_issue)
    await message.answer("Опишите проблему, которую вы хотите сообщить:")

@router.message(Menu.report_issue)
async def handle_report(message: types.Message, state: FSMContext):
    user_text = message.text
    user_id = message.from_user.id

    try:
        send_error_report(user_id, user_text)
        await message.answer("Спасибо! Ваше сообщение отправлено.")
    except Exception as e:
        await message.answer("Не удалось отправить сообщение. Попробуйте позже.")
        print("Ошибка при отправке email:", e)

    await state.set_state(Menu.main)

