import logging
from aiogram import Bot
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner

logger = logging.getLogger(__name__)

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором чата."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_admin_status = isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
        logger.debug(f"Пользователь {user_id} в чате {chat_id} - администратор: {is_admin_status}")
        return is_admin_status
    except Exception as e:
        logger.error(f"Ошибка проверки прав администратора для {user_id} в чате {chat_id}: {e}")
        return False

async def get_available_reactions(bot: Bot, chat_id: int, cache: dict) -> list[str]:
    """Получение списка доступных реакций для чата."""
    if chat_id in cache:
        logger.debug(f"Реакции для чата {chat_id} взяты из кэша: {cache[chat_id]}")
        return cache[chat_id]

    try:
        chat = await bot.get_chat(chat_id)
        logger.debug(f"Получена информация о чате {chat_id}: {chat}")
        if hasattr(chat, "available_reactions") and chat.available_reactions:
            reactions = []
            logger.debug(f"available_reactions: type={chat.available_reactions.type}, value={chat.available_reactions}")
            if chat.available_reactions.type == "all":
                reactions = [
                    "👍", "👎", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😢",
                    "🎉", "🤩", "🙈", "😇", "😂", "🤓", "😡", "🤗", "🫡", "💩"
                ]
                logger.debug(f"Чат {chat_id} позволяет все реакции: {reactions}")
            elif chat.available_reactions.type == "some":
                reactions = [r.emoji for r in chat.available_reactions.reactions if r.type == "emoji"]
                logger.debug(f"Чат {chat_id} имеет реакции: {reactions}")
            cache[chat_id] = reactions
            return reactions
        else:
            logger.debug(f"Реакции в чате {chat_id} отключены или отсутствуют")
            cache[chat_id] = []
            return []
    except Exception as e:
        logger.error(f"Ошибка при получении реакций для чата {chat_id}: {e}")
        return []

def translate_button(key: str, value: int, lang: str) -> str:
    """Перевод текста кнопок в зависимости от языка."""
    translations = {
        "ru": {
            "intel": f"Интеллект: {value}",
            "freq": f"Частота: {value}%",
            "custom": "Кастом"
        },
        "uk": {
            "intel": f"Інтелект: {value}",
            "freq": f"Частота: {value}%",
            "custom": "Кастомний"
        },
        "en": {
            "intel": f"Intelligence: {value}",
            "freq": f"Frequency: {value}%",
            "custom": "Custom"
        }
    }
    return translations.get(lang, translations["en"])[key]