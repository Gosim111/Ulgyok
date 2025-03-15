import aiosqlite
from typing import Optional, Tuple
from config import MAX_MESSAGES_PER_CHAT
import logging

logger = logging.getLogger(__name__)

class BotMemory:
    def __init__(self, db_path: str = "uglyok.db"):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных с таблицами для чатов и сообщений."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    language TEXT DEFAULT 'en',
                    intelligence INTEGER DEFAULT 50,
                    response_frequency INTEGER DEFAULT 50
                )
            """)
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
        """Добавление сообщения в базу данных с учетом лимита."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE chat_id = ?",
                (chat_id,)
            )
            count = (await cursor.fetchone())[0]
            if count >= MAX_MESSAGES_PER_CHAT:
                await db.execute(
                    "DELETE FROM messages WHERE id = (SELECT id FROM messages WHERE chat_id = ? ORDER BY id ASC LIMIT 1)",
                    (chat_id,)
                )
                logger.info(f"Удалено старое сообщение в чате {chat_id} из-за превышения лимита {MAX_MESSAGES_PER_CHAT}")
            try:
                await db.execute(
                    "INSERT INTO messages (chat_id, type, content) VALUES (?, ?, ?)",
                    (chat_id, msg_type, content)
                )
                await db.commit()
                logger.debug(f"Добавлено сообщение в чат {chat_id}: {content}")
                return True
            except aiosqlite.IntegrityError:
                logger.debug(f"Сообщение '{content}' уже существует в чате {chat_id}")
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
            if result:
                logger.debug(f"Язык чата {chat_id}: {result[0]}")
                return result[0]
            logger.debug(f"Чат {chat_id} не найден, возвращается 'en'")
            return "en"

    async def set_language(self, chat_id: int, lang: str) -> bool:
        """Установка языка чата с добавлением чата, если он отсутствует."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM chats WHERE chat_id = ?", (chat_id,))
            count = (await cursor.fetchone())[0]
            if count == 0:
                await db.execute(
                    "INSERT INTO chats (chat_id, chat_title, language) VALUES (?, ?, ?)",
                    (chat_id, "Unknown Chat", lang)
                )
                logger.info(f"Добавлен новый чат {chat_id} с языком {lang}")
            else:
                await db.execute(
                    "UPDATE chats SET language = ? WHERE chat_id = ?",
                    (lang, chat_id)
                )
                logger.debug(f"Язык чата {chat_id} обновлен на {lang}")
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

    async def get_random_message(self, chat_id: int) -> Tuple[Optional[str], Optional[str]]:
        """Получение случайного сообщения (текст или стикер) из базы для чата."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT type, content FROM messages WHERE chat_id = ? ORDER BY RANDOM() LIMIT 1",
                (chat_id,)
            )
            result = await cursor.fetchone()
            if result:
                msg_type, content = result
                return msg_type, content
            return None, None