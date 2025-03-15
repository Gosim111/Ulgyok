import aiosqlite
from typing import Optional

class BotMemory:
    def __init__(self, db_path: str = "uglyok.db"):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных с таблицами для чатов и сообщений."""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица для чатов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    language TEXT DEFAULT 'en',
                    intelligence INTEGER DEFAULT 50,
                    response_frequency INTEGER DEFAULT 50
                )
            """)
            # Таблица для сообщений
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    type TEXT,
                    content TEXT,
                    UNIQUE(chat_id, type, content),
                    FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
                )
            """)
            await db.commit()

    async def add_chat(self, chat_id: int, chat_title: str) -> bool:
        """Добавление нового чата в базу данных."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO chats (chat_id, chat_title) VALUES (?, ?)",
                    (chat_id, chat_title)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def add_message(self, chat_id: int, msg_type: str, content: str) -> bool:
        """Добавление сообщения в базу данных."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO messages (chat_id, type, content) VALUES (?, ?, ?)",
                    (chat_id, msg_type, content)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def message_exists(self, chat_id: int, msg_type: str, content: str) -> bool:
        """Проверка, существует ли сообщение в базе."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE chat_id = ? AND type = ? AND content = ?",
                (chat_id, msg_type, content)
            )
            count = (await cursor.fetchone())[0]
            return count > 0

    async def get_language(self, chat_id: int) -> str:
        """Получение языка чата."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT language FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else "en"

    async def set_language(self, chat_id: int, lang: str) -> bool:
        """Установка языка чата."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chats SET language = ? WHERE chat_id = ?",
                (lang, chat_id)
            )
            await db.commit()
            return True

    async def get_intelligence(self, chat_id: int) -> int:
        """Получение уровня интеллекта чата."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT intelligence FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else 50

    async def set_intelligence(self, chat_id: int, level: int) -> bool:
        """Установка уровня интеллекта чата."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chats SET intelligence = ? WHERE chat_id = ?",
                (level, chat_id)
            )
            await db.commit()
            return True

    async def get_response_frequency(self, chat_id: int) -> int:
        """Получение частоты ответа чата."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT response_frequency FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else 50

    async def set_response_frequency(self, chat_id: int, freq: int) -> bool:
        """Установка частоты ответа чата."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chats SET response_frequency = ? WHERE chat_id = ?",
                (freq, chat_id)
            )
            await db.commit()
            return True

    async def get_random_message(self, chat_id: int) -> Optional[str]:
        """Получение случайного текстового сообщения из базы для чата."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT content FROM messages WHERE chat_id = ? AND type = 'text' ORDER BY RANDOM() LIMIT 1",
                (chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else None