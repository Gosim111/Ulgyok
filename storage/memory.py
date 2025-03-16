import aiosqlite
from typing import Optional, Tuple, List
from config import MAX_MESSAGES_PER_CHAT
import logging
import re

logger = logging.getLogger(__name__)

class BotMemory:
    def __init__(self, db_path: str = "uglyok.db"):
        self.db_path = db_path
        self.chat_settings_cache = {}
        self.db = None

    async def init_db(self):
        """Инициализация базы данных и создание постоянного соединения."""
        try:
            self.db = await aiosqlite.connect(self.db_path)
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    language TEXT DEFAULT 'en',
                    intelligence INTEGER DEFAULT 50,
                    response_frequency INTEGER DEFAULT 50
                )
            """)  # noqa: SQL101
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    type TEXT,
                    content TEXT,
                    UNIQUE(chat_id, type, content),
                    FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
                )
            """)  # noqa: SQL101
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS sentences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    content TEXT,
                    FOREIGN KEY(message_id) REFERENCES messages(id)
                )
            """)  # noqa: SQL101
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence_id INTEGER,
                    content TEXT,
                    FOREIGN KEY(sentence_id) REFERENCES sentences(id)
                )
            """)  # noqa: SQL101
            await self.db.commit()
            logger.info("База данных успешно инициализирована")
            return True
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            self.db = None
            return False

    async def close_db(self):
        """Закрытие соединения с базой."""
        if self.db:
            await self.db.close()
            logger.info("Соединение с базой данных закрыто")
        else:
            logger.warning("Попытка закрыть неинициализированное соединение с базой")

    async def add_chat(self, chat_id: int, chat_title: str) -> bool:
        """Добавление нового чата в базу данных."""
        if not self.db:
            logger.error(f"База данных не инициализирована для добавления чата {chat_id}")
            return False
        try:
            await self.db.execute(
                "INSERT INTO chats (chat_id, chat_title) VALUES (?, ?) ON CONFLICT(chat_id) DO NOTHING",
                (chat_id, chat_title)
            )
            await self.db.commit()
            self.chat_settings_cache[chat_id] = {
                "language": "en",
                "intelligence": 50,
                "frequency": 50
            }
            logger.debug(f"Чат {chat_id} добавлен в кэш")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении чата {chat_id}: {e}")
            return False

    async def add_message(self, chat_id: int, msg_type: str, content: str) -> bool:
        """Добавление сообщения с разбиением текста на предложения и слова."""
        if not self.db:
            logger.error(f"База данных не инициализирована для добавления сообщения в чат {chat_id}")
            return False
        try:
            cursor = await self.db.execute(
                "SELECT COUNT(*) FROM messages WHERE chat_id = ?",
                (chat_id,)
            )
            count = (await cursor.fetchone())[0]
            if count >= MAX_MESSAGES_PER_CHAT:
                await self.db.execute(
                    "DELETE FROM messages WHERE id = (SELECT id FROM messages WHERE chat_id = ? ORDER BY id ASC LIMIT 1)",
                    (chat_id,)
                )
                logger.info(f"Удалено старое сообщение в чате {chat_id} из-за превышения лимита {MAX_MESSAGES_PER_CHAT}")

            cursor = await self.db.execute(
                "INSERT INTO messages (chat_id, type, content) VALUES (?, ?, ?) ON CONFLICT(chat_id, type, content) DO NOTHING RETURNING id",
                (chat_id, msg_type, content)
            )
            row = await cursor.fetchone()
            message_id = row[0] if row else None
            if message_id and msg_type == "text":
                sentences = re.split(r'[.!?]+', content)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        cursor = await self.db.execute(
                            "INSERT INTO sentences (message_id, content) VALUES (?, ?)",
                            (message_id, sentence)
                        )
                        sentence_id = cursor.lastrowid
                        words = sentence.split()
                        for word in words:
                            await self.db.execute(
                                "INSERT INTO words (sentence_id, content) VALUES (?, ?)",
                                (sentence_id, word)
                            )
            await self.db.commit()
            logger.debug(f"Добавлено сообщение в чат {chat_id}: {content}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения в чате {chat_id}: {e}")
            return False

    async def message_exists(self, chat_id: int, msg_type: str, content: str) -> bool:
        """Проверка, существует ли сообщение в базе."""
        if not self.db:
            logger.error(f"База данных не инициализирована для проверки сообщения в чате {chat_id}")
            return False
        try:
            cursor = await self.db.execute(
                "SELECT COUNT(*) FROM messages WHERE chat_id = ? AND type = ? AND content = ?",
                (chat_id, msg_type, content)
            )
            count = (await cursor.fetchone())[0]
            return count > 0
        except Exception as e:
            logger.error(f"Ошибка при проверке сообщения в чате {chat_id}: {e}")
            return False

    async def get_language(self, chat_id: int) -> str:
        """Получение языка чата."""
        if chat_id in self.chat_settings_cache:
            return self.chat_settings_cache[chat_id]["language"]
        if not self.db:
            logger.error(f"База данных не инициализирована для получения языка чата {chat_id}")
            return "en"
        try:
            cursor = await self.db.execute(
                "SELECT language, intelligence, response_frequency FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            result = await cursor.fetchone()
            if result:
                lang, intel, freq = result
                self.chat_settings_cache[chat_id] = {
                    "language": lang,
                    "intelligence": intel,
                    "frequency": freq
                }
                logger.debug(f"Загружены настройки чата {chat_id} из базы")
                return lang
            return "en"
        except Exception as e:
            logger.error(f"Ошибка при получении языка чата {chat_id}: {e}")
            return "en"

    async def set_language(self, chat_id: int, lang: str) -> bool:
        """Установка языка чата."""
        if not self.db:
            logger.error(f"База данных не инициализирована для установки языка чата {chat_id}")
            return False
        try:
            cursor = await self.db.execute("SELECT COUNT(*) FROM chats WHERE chat_id = ?", (chat_id,))
            count = (await cursor.fetchone())[0]
            if count == 0:
                await self.db.execute(
                    "INSERT INTO chats (chat_id, chat_title, language) VALUES (?, ?, ?)",
                    (chat_id, "Unknown Chat", lang)
                )
                logger.info(f"Добавлен новый чат {chat_id} с языком {lang}")
            else:
                await self.db.execute(
                    "UPDATE chats SET language = ? WHERE chat_id = ?",
                    (lang, chat_id)
                )
                logger.debug(f"Язык чата {chat_id} обновлен на {lang}")
            await self.db.commit()
            self.chat_settings_cache[chat_id] = self.chat_settings_cache.get(chat_id, {
                "language": "en",
                "intelligence": 50,
                "frequency": 50
            })
            self.chat_settings_cache[chat_id]["language"] = lang
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке языка чата {chat_id}: {e}")
            return False

    async def get_intelligence(self, chat_id: int) -> int:
        """Получение уровня интеллекта чата."""
        if chat_id in self.chat_settings_cache:
            return self.chat_settings_cache[chat_id]["intelligence"]
        if not self.db:
            logger.error(f"База данных не инициализирована для получения интеллекта чата {chat_id}")
            return 50
        try:
            cursor = await self.db.execute(
                "SELECT language, intelligence, response_frequency FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            result = await cursor.fetchone()
            if result:
                lang, intel, freq = result
                self.chat_settings_cache[chat_id] = {
                    "language": lang,
                    "intelligence": intel,
                    "frequency": freq
                }
                logger.debug(f"Загружены настройки чата {chat_id} из базы")
                return intel
            return 50
        except Exception as e:
            logger.error(f"Ошибка при получении интеллекта чата {chat_id}: {e}")
            return 50

    async def set_intelligence(self, chat_id: int, level: int) -> bool:
        """Установка уровня интеллекта чата."""
        if not self.db:
            logger.error(f"База данных не инициализирована для установки интеллекта чата {chat_id}")
            return False
        try:
            await self.db.execute(
                "UPDATE chats SET intelligence = ? WHERE chat_id = ?",
                (level, chat_id)
            )
            await self.db.commit()
            self.chat_settings_cache[chat_id] = self.chat_settings_cache.get(chat_id, {
                "language": "en",
                "intelligence": 50,
                "frequency": 50
            })
            self.chat_settings_cache[chat_id]["intelligence"] = level
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке интеллекта чата {chat_id}: {e}")
            return False

    async def get_response_frequency(self, chat_id: int) -> int:
        """Получение частоты ответа чата."""
        if chat_id in self.chat_settings_cache:
            return self.chat_settings_cache[chat_id]["frequency"]
        if not self.db:
            logger.error(f"База данных не инициализирована для получения частоты чата {chat_id}")
            return 50
        try:
            cursor = await self.db.execute(
                "SELECT language, intelligence, response_frequency FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            result = await cursor.fetchone()
            if result:
                lang, intel, freq = result
                self.chat_settings_cache[chat_id] = {
                    "language": lang,
                    "intelligence": intel,
                    "frequency": freq
                }
                logger.debug(f"Загружены настройки чата {chat_id} из базы")
                return freq
            return 50
        except Exception as e:
            logger.error(f"Ошибка при получении частоты чата {chat_id}: {e}")
            return 50

    async def set_response_frequency(self, chat_id: int, freq: int) -> bool:
        """Установка частоты ответа чата."""
        if not self.db:
            logger.error(f"База данных не инициализирована для установки частоты чата {chat_id}")
            return False
        try:
            await self.db.execute(
                "UPDATE chats SET response_frequency = ? WHERE chat_id = ?",
                (freq, chat_id)
            )
            await self.db.commit()
            self.chat_settings_cache[chat_id] = self.chat_settings_cache.get(chat_id, {
                "language": "en",
                "intelligence": 50,
                "frequency": 50
            })
            self.chat_settings_cache[chat_id]["frequency"] = freq
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке частоты чата {chat_id}: {e}")
            return False

    async def get_random_message(self, chat_id: int) -> Tuple[Optional[str], Optional[str]]:
        """Получение случайного сообщения из базы."""
        if not self.db:
            logger.error(f"База данных не инициализирована для получения сообщения в чате {chat_id}")
            return None, None
        try:
            cursor = await self.db.execute(
                "SELECT type, content FROM messages WHERE chat_id = ? ORDER BY RANDOM() LIMIT 1",
                (chat_id,)
            )
            result = await cursor.fetchone()
            if result:
                msg_type, content = result
                return msg_type, content
            return None, None
        except Exception as e:
            logger.error(f"Ошибка при получении случайного сообщения в чате {chat_id}: {e}")
            return None, None

    async def get_random_sentence(self, chat_id: int) -> Optional[str]:
        """Получение случайного предложения из базы."""
        if not self.db:
            logger.error(f"База данных не инициализирована для получения предложения в чате {chat_id}")
            return None
        try:
            cursor = await self.db.execute(
                "SELECT content FROM sentences WHERE message_id IN (SELECT id FROM messages WHERE chat_id = ?) ORDER BY RANDOM() LIMIT 1",
                (chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении случайного предложения в чате {chat_id}: {e}")
            return None

    async def get_random_words(self, chat_id: int, count: int) -> List[str]:
        """Получение случайных слов из базы."""
        if not self.db:
            logger.error(f"База данных не инициализирована для получения слов в чате {chat_id}")
            return []
        try:
            cursor = await self.db.execute(
                "SELECT content FROM words WHERE sentence_id IN (SELECT id FROM sentences WHERE message_id IN (SELECT id FROM messages WHERE chat_id = ?)) ORDER BY RANDOM() LIMIT ?",
                (chat_id, count)
            )
            results = await cursor.fetchall()
            return [row[0] for row in results] if results else []
        except Exception as e:
            logger.error(f"Ошибка при получении случайных слов в чате {chat_id}: {e}")
            return []

    async def get_chats(self) -> List[int]:
        """Получение списка всех зарегистрированных чатов."""
        if not self.db:
            logger.error("База данных не инициализирована для получения списка чатов")
            return []
        try:
            cursor = await self.db.execute("SELECT chat_id FROM chats")
            chats = await cursor.fetchall()
            return [chat[0] for chat in chats]
        except Exception as e:
            logger.error(f"Ошибка при получении списка чатов: {e}")
            return []

    async def clear_chat_data(self, chat_id: int):
        """Удаление всех данных чата из базы."""
        if not self.db:
            logger.error(f"База данных не инициализирована для удаления данных чата {chat_id}")
            return
        try:
            await self.db.execute(
                "DELETE FROM words WHERE sentence_id IN (SELECT id FROM sentences WHERE message_id IN (SELECT id FROM messages WHERE chat_id = ?))",
                (chat_id,)
            )
            await self.db.execute(
                "DELETE FROM sentences WHERE message_id IN (SELECT id FROM messages WHERE chat_id = ?)",
                (chat_id,)
            )
            await self.db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            await self.db.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
            await self.db.commit()
            if chat_id in self.chat_settings_cache:
                del self.chat_settings_cache[chat_id]
            logger.info(f"Все данные чата {chat_id} удалены из базы")
        except Exception as e:
            logger.error(f"Ошибка при удалении данных чата {chat_id}: {e}")