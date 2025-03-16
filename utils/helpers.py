from aiogram import Bot
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception as e:
        logger.error(f"Ошибка проверки админа в чате {chat_id}: {e}")
        return False

async def get_available_reactions(bot: Bot, chat_id: int, cache: Dict[int, List[str]]) -> List[str]:
    """Получает список доступных реакций для чата."""
    if chat_id in cache:
        return cache[chat_id]
    try:
        chat = await bot.get_chat(chat_id)
        # Упрощаем: если это группа или супергруппа, предполагаем, что реакции доступны
        if chat.type in ("group", "supergroup"):
            reactions = ["👍", "👎", "😂", "😮", "😢"]
            cache[chat_id] = reactions
            logger.debug(f"Реакции для чата {chat_id}: {reactions}")
            return reactions
        logger.debug(f"Реакции недоступны в чате {chat_id} (тип: {chat.type})")
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении реакций для чата {chat_id}: {e}")
        return []