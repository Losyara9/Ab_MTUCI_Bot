from aiogram import types, F, Router, Dispatcher
from aiogram.client.session import aiohttp
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
import re
import os
import requests

from app.logger import log_api_call
from app.states import Registration, Menu
from app.db import Database
from app.middlewares import InjectDatabaseMiddleware
from app.email_utils import send_error_report, generate_code, send_verification_code

router = Router()

API_URL = "http://get-info-stud.dev-lik.ru/api.php"
LOGIN = "mtuci"
PASSWORD = "superpass"


async def get_abiturient_id(phone: str) -> int | None:
    payload = {
        "login": LOGIN,
        "password": PASSWORD,
        "method": "GetAbiturient",
        "phone_number": phone
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload) as resp:
            result = await resp.json()
            if result.get("success"):
                return result["data"].get("id")
    return None


async def is_registered(telegram_id: int, db: Database) -> bool:  # проверка на регистрацию
    applicant = await db.get_applicant(telegram_id)
    return applicant is not None


def register_handlers(dp: Dispatcher, db: Database):  # вызов регистрации
    router.message.middleware(InjectDatabaseMiddleware(db))
    dp.include_router(router)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, db: Database):
    await state.clear()
    telegram_id = message.from_user.id

    is_reg = await is_registered(telegram_id, db)

    text = (
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        "Я — бот приёмной комиссии\n"
        "С моей помощью вы можете:\n"
        "• 🔎 Получить информацию о своих заявлениях\n"
        "• 📋 Узнать результаты вступительных испытаний\n"
        "• 🏆 Посмотреть индивидуальные достижения\n"
        "• 📧 Проверить и подтвердить email\n"
        "• ❗ Отправить жалобу\n\n"
    )

    if is_reg:
        text += "Вы уже зарегистрированы ✅\nОткрываю главное меню:"
        await message.answer(text)
        await menu_command(message, state)
    else:
        text += "Чтобы начать регистрацию, нажмите кнопку 'Начать' ⬇️"
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Начать")]],
            resize_keyboard=True
        )
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "🆘 <b>Справка</b>\n\n"
        "Вот что умеет этот бот:\n"
        "• 📄 Регистрация абитуриента\n"
        "• 📬 Подтверждение email (код на почту)\n"
        "• 🧾 Получение информации о заявлениях, экзаменах и достижениях\n"
        "• 🗣 Отправка жалоб с прикреплёнными файлами\n\n"
        "Для начала используйте команду /start или нажмите кнопку 'Начать'."
    )
    await message.answer(text, parse_mode="HTML")



@router.message(F.text.casefold() == "начать")  # отправка номера телефона
async def start_registration(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(
                text="Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Пожалуйста, отправьте ваш номер телефона:", reply_markup=keyboard)
    await state.set_state(Registration.waiting_for_phone)


def check_phone_exists(phone: str) -> bool:
    payload = {
        "login": LOGIN,
        "password": PASSWORD,
        "method": "GetAbiturient",
        "phone_number": phone
    }
    response = requests.post(API_URL, json=payload)
    if response.ok:
        data = response.json()
        return data.get("success", False)
    return False


@router.message(F.contact)
async def phone_received(message: types.Message, state: FSMContext, **kwargs):
    db: Database = kwargs["db"]
    phone = message.contact.phone_number.lstrip("+")
    username = message.from_user.username

    # проверка через API
    if not check_phone_exists(phone):
        await message.answer("Ваш номер телефона не найден в базе приёмной комиссии. Обратитесь в приёмную комиссию.")
        return

    await db.add_or_update_applicant(
        telegram_id=message.from_user.id,
        phone=phone,
        username=username,
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

    code = generate_code()
    send_verification_code(email, code)

    await state.update_data(email=email, code=code)
    await db.add_or_update_applicant(telegram_id=message.from_user.id, email=email, step=2)

    await message.answer("Код подтверждения отправлен на вашу почту. Введите четырехзначный код")
    await state.set_state(Registration.waiting_for_code)


@router.message(Registration.waiting_for_code)
async def check_code(message: types.Message, state: FSMContext, **kwargs):
    user_code = message.text.strip()
    telegram_id = message.from_user.id
    username = message.from_user.username
    data = await state.get_data()

    if user_code != data.get("code"):
        await message.answer("Неверный код. Попробуйте ещё раз.")
        return

    # Сохраняем email и step
    db: Database = kwargs["db"]

    try:
        await db.add_or_update_applicant(
            telegram_id=message.from_user.id,
            email=data["email"],
            step=2
        )

        email = data["email"]
        applicant = await db.get_applicant(telegram_id)
        abiturient_data = await get_abiturient_data(applicant["phone"], db)
        abiturient_id = abiturient_data["id"]

        payload = {
            "login": LOGIN,
            "password": PASSWORD,
            "method": "UpdateEmail",
            "abiturient_id": abiturient_id,
            "email": email
        }

        if telegram_id:
            await log_api_call(telegram_id, "UpdateEmail", payload, username=username, type_="request")

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload) as resp:
                result = await resp.json()

        if telegram_id:
            await log_api_call(telegram_id, "UpdateEmail", result, username=username, type_="response")

        await message.answer("Email подтверждён. Регистрация завершена.")
        await menu_command(message, state)

    except Exception as e:
        await log_api_call(
            telegram_id=telegram_id,
            method="UpdateEmail",
            username=username,
            type_="error",
            data={"error": str(e)})

        await message.answer(
            "Произошла ошибка при подтверждении email. Пожалуйста, попробуйте снова чуть позже."
        )


def is_valid_inn(inn: str) -> bool:  # проверка ввода инн
    return inn.isdigit() and len(inn) == 12


@router.message(Command("menu"))
async def menu_command(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📋 Получить информацию")],
            [types.KeyboardButton(text="✏ Изменить ИНН"),
             types.KeyboardButton(text="✏ Изменить Email")],
            [types.KeyboardButton(text="🛠 Сообщить об ошибке")],
        ],
        resize_keyboard=True
    )
    await state.set_state(Menu.main)
    await message.answer("Добро пожаловать в личный кабинет. Выберите действие:", reply_markup=keyboard)


@router.message(lambda message: message.text == "🔙 Назад")
async def back_to_menu(message: types.Message, state: FSMContext):
    await menu_command(message, state)


@router.message(Menu.main, F.text == "📋 Получить информацию")
async def choose_info_type(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Заявление и статус")],
            [types.KeyboardButton(text="Вступительные экзамены")],
            [types.KeyboardButton(text="Результаты экзаменов")],
            [types.KeyboardButton(text="Индивидуальные достижения")],
            [types.KeyboardButton(text="📧 Моя почта")],
            [types.KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    await state.set_state(Menu.choose_info_type)
    await message.answer("Что вы хотите узнать?", reply_markup=keyboard)


async def get_abiturient_data(phone: str, db: Database) -> dict | None:
    applicant = await db.get_applicant_by_phone(phone)
    telegram_id = applicant["telegram_id"] if applicant else None
    username = applicant["username"] if applicant and "username" in applicant else "-"

    payload = {
        "login": LOGIN,
        "password": PASSWORD,
        "method": "GetAbiturient",
        "phone_number": phone
    }

    if telegram_id:
        await log_api_call(telegram_id, "GetAbiturient", payload, username=username, type_="request")

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload) as resp:
            result = await resp.json()
    if telegram_id:
        await log_api_call(telegram_id, "GetAbiturient", result, username=username, type_="response")

    if result.get("success"):
        return result["data"]
    return None


@router.message(Menu.choose_info_type)
async def info_handler(message: types.Message, state: FSMContext, db: Database):
    text = message.text
    telegram_id = message.from_user.id
    username = message.from_user.username

    applicant = await db.get_applicant(telegram_id)
    phone = applicant["phone"] if applicant else None

    abiturient_data = await get_abiturient_data(phone, db)
    if not abiturient_data:
        await message.answer("Не удалось получить данные абитуриента.")
        return

    abiturient_id = abiturient_data.get("id")

    if text == "Заявление и статус":
        payload = {
            "login": LOGIN,
            "password": PASSWORD,
            "method": "GetApplication",
            "abiturient_id": abiturient_id
        }

        if telegram_id:
            await log_api_call(telegram_id, "GetApplication", payload, username=username, type_="request")

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload) as resp:
                result = await resp.json()

        if telegram_id:
            await log_api_call(telegram_id, "GetApplication", result, username=username, type_="response")

        if not result.get("success") or not result.get("data"):
            await message.answer("У вас пока нет поданных заявлений.")
            return

        msg = "📄 Ваши заявления:\n\n"
        for app in result["data"]:
            msg += (
                f"🔸 Специальность: {app['specialty']}\n"
                f"📌 Статус: {app['status'].capitalize()}\n"
                f"🕒 Подано: {app['created_at']}\n\n"
            )
        await message.answer(msg)

    elif text == "Вступительные экзамены":
        payload = {
            "login": LOGIN,
            "password": PASSWORD,
            "method": "GetEntranceTests",
            "abiturient_id": abiturient_id
        }

        if telegram_id:
            await log_api_call(telegram_id, "GetEntranceTests", payload, username=username, type_="request")

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload) as resp:
                result = await resp.json()

        if telegram_id:
            await log_api_call(telegram_id, "GetEntranceTests", result, username=username, type_="response")

        if not result.get("success") or not result.get("data"):
            await message.answer("Информация о вступительных экзаменах недоступна.")
            return

        msg = "📚 Вступительные экзамены:\n\n"
        for exam in result["data"]:
            msg += (
                f"🗓 Дата и время: {exam['test_date']}\n"
                f"🔐 Логин: {exam['login']}\n"
                f"🔑 Пароль: {exam['password']}\n"
                f"🌐 Ссылка: {exam['eios_link']}\n\n"
            )
        await message.answer(msg)

    elif text == "Результаты экзаменов":
        payload = {
            "login": LOGIN,
            "password": PASSWORD,
            "method": "GetExamResults",
            "abiturient_id": abiturient_id
        }

        if telegram_id:
            await log_api_call(telegram_id, "GetExamResults", payload, username=username, type_="request")

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload) as resp:
                result = await resp.json()

        if telegram_id:
            await log_api_call(telegram_id, "GetExamResults", result, username=username, type_="response")

        if not result.get("success") or not result.get("data"):
            await message.answer("Результаты экзаменов недоступны.")
            return

        ege_results = []
        vstup_results = []

        for exam in result["data"]:
            name = exam.get("exam_name", "Неизвестный экзамен")
            score = exam.get("score", "-")
            date = exam.get("exam_date", "-")

            if "ЕГЭ" in name.upper():
                ege_results.append(
                    f"• {name.replace('ЕГЭ ', '')}: {score} (от {date})")
            else:
                vstup_results.append(f"• {name}: {score} (от {date})")

        msg = ""
        if ege_results:
            msg += "📊 Результаты ЕГЭ:\n" + "\n".join(ege_results) + "\n"
        if vstup_results:
            msg += "\n📚 Внутренние экзамены:\n" + "\n".join(vstup_results)

        await message.answer(msg.strip())

    elif text == "Индивидуальные достижения":
        payload = {
            "login": LOGIN,
            "password": PASSWORD,
            "method": "GetAchievements",
            "abiturient_id": abiturient_id
        }

        if telegram_id:
            await log_api_call(telegram_id, "GetAchievements", payload, username=username, type_="request")

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload) as resp:
                result = await resp.json()

        if telegram_id:
            await log_api_call(telegram_id, "GetAchievements", result, username=username, type_="response")

        if not result.get("success") or not result.get("data"):
            await message.answer("Информация об индивидуальных достижениях отсутствует.")
            return

        msg = "🏅 Индивидуальные достижения:\n\n"
        for item in result["data"]:
            achievement = item.get("achievement", "—")
            description = item.get("description", "")
            msg += f"• {achievement}"
            if description:
                msg += f" — {description}"
            msg += "\n"

        await message.answer(msg.strip())

    elif text == "📧 Моя почта":
        payload = {
            "login": LOGIN,
            "password": PASSWORD,
            "method": "GetEmail",
            "phone_number": phone
        }

        if telegram_id:
            await log_api_call(telegram_id, "GetEmail", payload, username=username, type_="request")

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload) as resp:
                result = await resp.json()

        if telegram_id:
            await log_api_call(telegram_id, "GetEmail", result, username=username, type_="response")

        if result.get("success") and result.get("data"):
            email = result["data"].get("email", "не указан")
            await message.answer(f"📧 Текущий email: {email}")
        else:
            await message.answer("Не удалось получить email. Попробуйте позже.")

    elif text == "🔙 Назад":
        await message.answer("Вы вернулись в главное меню.", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Menu.main)

    else:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.")


@router.message(Menu.main, F.text == "✏ Изменить ИНН")
async def start_change_inn(message: types.Message, state: FSMContext):
    await state.set_state(Menu.change_inn)
    await message.answer("Введите новый ИНН:")


@router.message(Menu.change_inn)
async def save_new_inn(message: types.Message, state: FSMContext, db: Database):
    inn = message.text.strip()
    telegram_id = message.from_user.id
    username = message.from_user.username
    if not is_valid_inn(inn):
        await message.answer("❗ ИНН должен содержать ровно 12 цифр. Попробуйте снова.")
        return

    applicant = await db.get_applicant(message.from_user.id)
    abiturient_data = await get_abiturient_data(applicant["phone"], db)
    abiturient_id = abiturient_data["id"]

    payload = {
        "login": LOGIN,
        "password": PASSWORD,
        "method": "UpdateINN",
        "abiturient_id": abiturient_id,
        "inn": inn
    }

    if telegram_id:
        await log_api_call(telegram_id, "UpdateINN", payload, username=username, type_="request")

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload) as resp:
            result = await resp.json()

    if telegram_id:
        await log_api_call(telegram_id, "UpdateINN", result, username=username, type_="response")

    if result.get("success"):
        await message.answer("ИНН успешно обновлён ✅")
    else:
        await message.answer(f"Не удалось обновить ИНН: {result.get('message', 'ошибка')}")
    await menu_command(message, state)


@router.message(Menu.main, F.text == "✏ Изменить Email")
async def start_change_email(message: types.Message, state: FSMContext):
    await state.set_state(Menu.change_email)
    await message.answer("Введите новый email:")


@router.message(Menu.change_email)
async def save_new_email_and_send_code(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not is_valid_email(email):
        await message.answer("❗ Неверный формат email. Попробуйте снова.")
        return

    code = generate_code()
    send_verification_code(email, code)

    await state.update_data(email=email, code=code)
    await state.set_state(Menu.waiting_for_email_code)
    await message.answer("На указанный email отправлен 4-значный код. Введите его для подтверждения:")


@router.message(Menu.waiting_for_email_code)
async def confirm_email_code_and_update(message: types.Message, state: FSMContext, db: Database):
    user_code = message.text.strip()
    data = await state.get_data()
    telegram_id = message.from_user.id
    username = message.from_user.username

    if user_code != data.get("code"):
        await message.answer("Неверный код. Попробуйте ещё раз.")
        return

    email = data["email"]
    applicant = await db.get_applicant(message.from_user.id)
    abiturient_data = await get_abiturient_data(applicant["phone"], db)
    abiturient_id = abiturient_data["id"]

    payload = {
        "login": LOGIN,
        "password": PASSWORD,
        "method": "UpdateEmail",
        "abiturient_id": abiturient_id,
        "email": email
    }

    if telegram_id:
        await log_api_call(telegram_id, "UpdateEmail", payload, username=username, type_="request")

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload) as resp:
            result = await resp.json()

    if telegram_id:
        await log_api_call(telegram_id, "UpdateEmail", result, username=username, type_="response")

    if result.get("success"):
        await db.add_or_update_applicant(telegram_id=message.from_user.id, email=email)
        await message.answer("Email успешно обновлён и подтверждён ✅")
    else:
        await message.answer(f"Ошибка при обновлении email: {result.get('message', 'неизвестная ошибка')}")

    await menu_command(message, state)


@router.message(Menu.main, F.text == "🛠 Сообщить об ошибке")
async def report_start(message: types.Message, state: FSMContext):
    await state.set_state(Menu.report_issue)
    await message.answer("Опишите проблему, которую вы хотите сообщить:")


@router.message(Menu.report_issue)
async def handle_report(message: types.Message, state: FSMContext, **kwargs):
    db: Database = kwargs["db"]
    telegram_id = message.from_user.id
    username = message.from_user.username
    photos = message.photo
    text = message.caption or message.text or "Без текста"
    screenshot_paths = []

    # Сохраняем все прикреплённые фото
    if photos:
        os.makedirs("screenshots", exist_ok=True)
        photo = message.photo[-1]  # Только одно, самое большое изображение
        path = f"screenshots/{telegram_id}.jpg"
        await message.bot.download(photo.file_id, destination=path)
        screenshot_paths = [path]

    # Получаем номер телефона из БД
    applicant = await db.get_applicant(telegram_id)
    phone = applicant["phone"] if applicant else None

    # Получаем данные абитуриента из API
    user_data = {}
    if phone:
        async with aiohttp.ClientSession() as session:
            payload = {
                "login": "mtuci",
                "password": "superpass",
                "method": "GetAbiturient",
                "phone_number": phone
            }
            async with session.post("http://get-info-stud.dev-lik.ru/api.php", json=payload) as resp:
                result = await resp.json()
                if result.get("success"):
                    user_data = result["data"]

    try:
        send_error_report(username, text, user_data, screenshot_paths)
        await message.answer("Спасибо! Ваша жалоба отправлена.")
    except Exception as e:
        print("Ошибка при отправке жалобы:", e)
        await message.answer("Произошла ошибка при отправке. Попробуйте позже.")

    await state.set_state(Menu.main)
