import asyncpg
from app.logger import log_event, log_error


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host="localhost",
            port="5432",
            user="postgres",
            password="123",
            database="AbitBot"
        )
        await self.create_tables()

    async def create_tables(self):
        applicants_query = """
        CREATE TABLE IF NOT EXISTS applicants (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT,
            registration_step INT DEFAULT 0,
            username text
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(applicants_query)

    async def add_or_update_applicant(self, telegram_id, phone=None, email=None, step=None, username=None):
        log_event(f"[DB] Запрос на добавление/обновление пользователя: telegram_id: {telegram_id}, phone: {phone}")
        try:
            async with self.pool.acquire() as conn:
                applicant = await conn.fetchrow("SELECT * FROM applicants WHERE telegram_id=$1", telegram_id)
                if applicant:
                    await conn.execute("""
                        UPDATE applicants SET 
                            phone=COALESCE($2, phone),
                            email=COALESCE($3, email),
                            registration_step=COALESCE($4, registration_step),
                            username=COALESCE($5, username)
                        WHERE telegram_id=$1
                    """, telegram_id, phone, email, step, username)
                else:
                    await conn.execute("""
                        INSERT INTO applicants (telegram_id, phone, email, registration_step, username)
                        VALUES ($1, $2, $3, $4, $5)
                    """, telegram_id, phone, email, step, username or 0)
            log_event(f"[DB] Успешно добавлен/обновлен пользователь с phone={phone}")
        except Exception as e:
            log_error(f"[DB] Ошибка при добавлении/обновлении пользователя с phone={phone}: {e}")

    async def get_applicant(self, telegram_id):
        log_event(f"[DB] Получение пользователя по телеграм айди: {telegram_id}")
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("SELECT * FROM applicants WHERE telegram_id=$1", telegram_id)
                if result:
                    log_event(f"[DB] Пользователь по телеграм айди {telegram_id} найден")
                else:
                    log_event(f"[DB] Пользователь по телеграм айди {telegram_id} не найден")
                return result
        except Exception as e:
            log_error(f"[DB] Ошибка при получении пользователя по телеграм айди {telegram_id}: {e}")

    async def get_applicant_by_phone(self, phone):
        log_event(f"[DB] Получение пользователя по номеру телефона: {phone}")
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("SELECT * FROM applicants WHERE phone=$1", phone)
                if result:
                    log_event(f"[DB] Пользователь по номеру телефона {phone} найден")
                else:
                    log_event(f"[DB] Пользователь по номеру телефона {phone} не найден")
                return result
        except Exception as e:
            log_error(f"[DB] Ошибка при получении пользователя по номеру {phone}: {e}")
