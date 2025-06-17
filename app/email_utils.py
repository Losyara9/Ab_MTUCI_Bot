import smtplib
import random
import os
from email.message import EmailMessage
import mimetypes
from logger import log_error, log_event

SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_ADDRESS = "bmtusi@bk.ru"
EMAIL_PASSWORD = "2Pmgu2Fh5B4ZP7PPqo8d"


def generate_code():
    return str(random.randint(1000, 9999))


def send_verification_code(to_email, code):
    msg = EmailMessage()
    msg["Subject"] = "Подтверждение адреса электронной почты"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(f"Ваш код подтверждения: {code}\n"
                    f"Если вы не запрашивали код, проигнорируйте данное письмо.")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        try:
            server.send_message(msg)
            log_event(f"Email отправлен на адрес: {to_email}")
        except Exception as e:
            log_error(f"Ошибка при отправке письма на {to_email}: {e}")


def send_error_report(username: str, message_text: str, user_data: dict, screenshot_paths: list[str]):
    msg = EmailMessage()
    msg["Subject"] = "Жалоба от пользователя"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    tg_link = f"https://t.me/{username}"

    full_name = f"{user_data.get('last_name', '')} {user_data.get('first_name', '')} {user_data.get('patronymic', '')}"
    email = user_data.get("email", "Не указано")

    msg.set_content(
        f"Пользователь: {full_name}\n"
        f"Email: {email}\n"
        f"Ссылка на чат: {tg_link}\n\n"
        f"Текст жалобы:\n{message_text}"
    )

    for path in screenshot_paths:
        try:
            with open(path, "rb") as f:
                file_data = f.read()
                file_name = path.split("/")[-1]
                mime_type, _ = mimetypes.guess_type(path)
                maintype, subtype = mime_type.split("/") if mime_type else ("application", "octet-stream")
                msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=file_name)
                log_event(f"Изображение прикреплено")
        except Exception as e:
            log_error(f"Ошибка при прикреплении изображения: {e}")

    try:
        with smtplib.SMTP("smtp.mail.ru", 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            log_event(f"Письмо с жалобой отправлено от пользователя с почтой {email}")
    except Exception as e:
        log_error(f"Ошибка при отправке письма: {e}")

    for path in screenshot_paths:
        try:
            os.remove(path)
            log_event(f"Директория со изображениями очищена")
        except Exception as e:
            log_error(f"Не удалось удалить файл {path}: {e}")
