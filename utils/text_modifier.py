import random
import string
from typing import List, Optional
import logging
from storage.memory import BotMemory  # Импортируем глобальный BotMemory

logger = logging.getLogger(__name__)

class TextModifier:
    def __init__(self):
        self.BotMemory = BotMemory  # Используем глобальный BotMemory
        self.word_cache = {}
        self.sentence_cache = {}

    async def _update_cache(self, chat_id: int):
        """Обновление кэша слов и предложений для чата."""
        if chat_id not in self.word_cache or not self.word_cache[chat_id]:
            try:
                cursor = await self.BotMemory.db.execute(
                    "SELECT content FROM words WHERE sentence_id IN (SELECT id FROM sentences WHERE message_id IN (SELECT id FROM messages WHERE chat_id = ?))",
                    (chat_id,)
                )
                words = await cursor.fetchall()
                self.word_cache[chat_id] = [word[0] for word in words] if words else []
                logger.debug(f"Обновлен кэш слов для чата {chat_id}: {len(self.word_cache[chat_id])} слов")
            except Exception as e:
                logger.error(f"Ошибка обновления кэша слов для чата {chat_id}: {e}")
                self.word_cache[chat_id] = []

        if chat_id not in self.sentence_cache or not self.sentence_cache[chat_id]:
            try:
                cursor = await self.BotMemory.db.execute(
                    "SELECT content FROM sentences WHERE message_id IN (SELECT id FROM messages WHERE chat_id = ?)",
                    (chat_id,)
                )
                sentences = await cursor.fetchall()
                self.sentence_cache[chat_id] = [sentence[0] for sentence in sentences] if sentences else []
                logger.debug(f"Обновлен кэш предложений для чата {chat_id}: {len(self.sentence_cache[chat_id])} предложений")
            except Exception as e:
                logger.error(f"Ошибка обновления кэша предложений для чата {chat_id}: {e}")
                self.sentence_cache[chat_id] = []

    async def modify_text(self, chat_id: int, input_text: str, intelligence: int) -> str:
        """Модифицирует текст на основе уровня интеллекта."""
        try:
            await self._update_cache(chat_id)
            words_available = self.word_cache.get(chat_id, [])
            sentences_available = self.sentence_cache.get(chat_id, [])

            if intelligence == 0:
                length = len(input_text.split())
                random_words = random.sample(words_available, min(length, len(words_available))) if words_available else ["gibberish"]
                return " ".join(random_words)

            elif intelligence == 100:
                if sentences_available:
                    return random.choice(sentences_available)
                return input_text

            elif intelligence < 20:
                return await self.modify_text(chat_id, input_text, 0)

            elif 20 <= intelligence < 50:
                probability = (50 - intelligence) / 30
                words = input_text.split()
                modified_words = []
                random_words = random.sample(words_available, len(words)) if len(words_available) >= len(words) else words_available + ["random"] * (len(words) - len(words_available))
                for i, word in enumerate(words):
                    if random.random() < probability and i < len(random_words):
                        modified_words.append(random_words[i])
                    else:
                        modified_words.append(word)
                return " ".join(modified_words)

            elif 50 <= intelligence < 80:
                num_swaps = int((80 - intelligence) / 30 * len(input_text) / 2)
                text_list: List[str] = list(input_text)
                for _ in range(max(1, num_swaps)):
                    if len(text_list) < 2:
                        break
                    i = random.randint(0, len(text_list) - 2)
                    text_list[i], text_list[i + 1] = text_list[i + 1], text_list[i]
                return ''.join(text_list)

            elif 80 <= intelligence < 100:
                if sentences_available:
                    sentence = random.choice(sentences_available)
                    num_changes = int((100 - intelligence) / 20)
                    text_list: List[str] = sentence.split()
                    random_words = random.sample(words_available, min(num_changes, len(words_available))) if words_available else ["random"]
                    for _ in range(max(1, num_changes)):
                        if not text_list or not random_words:
                            break
                        index = random.randint(0, len(text_list) - 1)
                        text_list[index] = random_words.pop(0)
                    return " ".join(text_list)
                return input_text

            return input_text

        except Exception as e:
            logger.error(f"Ошибка модификации текста в чате {chat_id}: {e}")
            return input_text

    async def clear_cache(self, chat_id: int):
        """Очистка кэша для чата."""
        if chat_id in self.word_cache:
            del self.word_cache[chat_id]
        if chat_id in self.sentence_cache:
            del self.sentence_cache[chat_id]
        logger.debug(f"Кэш очищен для чата {chat_id}")