import asyncpg
from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

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
        query = """
        CREATE TABLE IF NOT EXISTS applicants (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            phone TEXT,
            email TEXT,
            inn TEXT,
            fullname TEXT,
            registration_step INT DEFAULT 0
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def add_or_update_applicant(self, telegram_id, phone=None, email=None, inn=None, fullname=None, step=None):
        async with self.pool.acquire() as conn:
            applicant = await conn.fetchrow("SELECT * FROM applicants WHERE telegram_id=$1", telegram_id)
            if applicant:
                # обновляем данные
                await conn.execute("""
                    UPDATE applicants SET 
                        phone=COALESCE($2, phone),
                        email=COALESCE($3, email),
                        inn=COALESCE($4, inn),
                        fullname=COALESCE($5, fullname),
                        registration_step=COALESCE($6, registration_step)
                    WHERE telegram_id=$1
                """, telegram_id, phone, email, inn, fullname, step)
            else:
                # создаем нового абитуриента (если такого еще нет)
                await conn.execute("""
                    INSERT INTO applicants (telegram_id, phone, email, inn, fullname, registration_step)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, telegram_id, phone, email, inn, fullname, step or 0)

    async def get_applicant(self, telegram_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM applicants WHERE telegram_id=$1", telegram_id)
