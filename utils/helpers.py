import logging
from aiogram import Bot
from aiogram.types import ChatPermissions, InlineKeyboardButton

logger = logging.getLogger(__name__)

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        logger.debug(f"Пользователь {user_id} в чате {chat_id} - администратор: {member.is_chat_admin()}")
        return member.is_chat_admin()
    except Exception as e:
        logger.error(f"Ошибка при проверке админства для {user_id} в чате {chat_id}: {e}")
        return False

async def get_available_reactions(bot: Bot, chat_id: int, cache: dict) -> list:
    if chat_id in cache:
        logger.debug(f"Реакции для чата {chat_id} взяты из кэша: {cache[chat_id]}")
        return cache[chat_id]
    try:
        chat = await bot.get_chat(chat_id)
        logger.debug(f"Получена информация о чате {chat_id}: {chat}")
        if hasattr(chat, 'available_reactions') and chat.available_reactions:
            reactions = [reaction.emoji for reaction in chat.available_reactions if hasattr(reaction, 'emoji')]
            cache[chat_id] = reactions
            logger.debug(f"Доступные реакции для чата {chat_id}: {reactions}")
            return reactions
        logger.debug(f"Реакции в чате {chat_id} отключены или отсутствуют")
        cache[chat_id] = []
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении реакций для чата {chat_id}: {e}")
        cache[chat_id] = []
        return []

def translate_button(setting: str, value: int, lang: str) -> str:
    translations = {
        "ru": {"intel": f"Интеллект: {value}", "freq": f"Частота: {value}%", "custom": "Кастом"},
        "uk": {"intel": f"Інтелект: {value}", "freq": f"Частота: {value}%", "custom": "Кастом"},
        "en": {"intel": f"Intelligence: {value}", "freq": f"Frequency: {value}%", "custom": "Custom"}
    }
    return translations.get(lang, translations["en"])[setting]