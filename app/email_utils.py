import smtplib
from email.message import EmailMessage

SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_ADDRESS = "bmtusi@bk.ru"
EMAIL_PASSWORD = "2Pmgu2Fh5B4ZP7PPqo8d"

def send_error_report(user_id: int, message_text: str):
    msg = EmailMessage()
    msg['Subject'] = f"Ошибка от пользователя {user_id}"
    msg['From'] = "bmtusi@bk.ru"
    msg['To'] = "bmtusi@bk.ru"

    msg.set_content(message_text, subtype='plain', charset='utf-8')

    with smtplib.SMTP("smtp.mail.ru", 587) as smtp:
        smtp.starttls()
        smtp.login("bmtusi@bk.ru", "2Pmgu2Fh5B4ZP7PPqo8d")
        smtp.send_message(msg)