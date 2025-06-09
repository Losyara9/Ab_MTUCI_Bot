FROM python:3

WORKDIR /app

COPY app/ /app/app/
COPY .env /app/.env
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "-m", "app.bot"]
