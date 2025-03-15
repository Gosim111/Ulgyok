import logging
from aiogram import Bot
from aiogram.types import ChatPermissions, InlineKeyboardButton
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, ChatMember

logger = logging.getLogger(__name__)

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором чата."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        logger.debug(f"Информация о пользователе {user_id} в чате {chat_id}: {member}") # Лог всего объекта member

        is_admin_status = isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
        logger.debug(f"Пользователь {user_id} в чате {chat_id} - администратор (isinstance): {is_admin_status}")

        if not is_admin_status: # Дополнительная проверка на другие типы админов, на всякий случай
            is_admin_status = member.status in ["administrator", "creator"] # Проверка по status
            logger.debug(f"Пользователь {user_id} в чате {chat_id} - администратор (status check): {is_admin_status}")

        logger.debug(f"Финальный статус админа для пользователя {user_id} в чате {chat_id}: {is_admin_status}")
        return is_admin_status
    except Exception as e:
        logger.error(f"Ошибка при проверке прав администратора для {user_id} в чате {chat_id}: {e}")
        return False

async def get_available_reactions(bot: Bot, chat_id: int, cache: dict) -> list:
    """Получение списка доступных реакций для чата."""
    # Временно отключаем кэш для диагностики
    # if chat_id in cache:
    #     logger.debug(f"Реакции для чата {chat_id} взяты из кэша: {cache[chat_id]}")
    #     return cache[chat_id]

    logger.debug(f"Запрос реакций для чата {chat_id} (без использования кэша)") # Лог перед запросом

    try:
        chat = await bot.get_chat(chat_id)
        logger.debug(f"Информация о чате {chat_id} при запросе реакций: {chat}") # Лог объекта chat

        if hasattr(chat, "available_reactions"):
            available_reactions = chat.available_reactions
            logger.debug(f"Поле available_reactions присутствует: {available_reactions}") # Лог available_reactions

            if available_reactions:
                reactions = []
                for reaction in available_reactions:
                    if hasattr(reaction, 'emoji'):
                        reactions.append(reaction.emoji)
                    else:
                        logger.warning(f"Реакция без emoji атрибута: {reaction}") # Лог, если нет emoji
                cache[chat_id] = reactions # Возвращаем кэширование после диагностики
                logger.debug(f"Доступные реакции (emoji) для чата {chat_id}: {reactions}")
                return reactions
            else:
                logger.debug(f"available_reactions is empty list or None") # Лог, если available_reactions пуст
        else:
            logger.debug(f"Поле available_reactions отсутствует в объекте chat") # Лог, если нет поля available_reactions
            cache[chat_id] = [] # Возвращаем кэширование после диагностики
            return []
    except Exception as e:
        logger.error(f"Ошибка при получении реакций для чата {chat_id}: {e}")
        return []

def translate_button(setting: str, value: int, lang: str) -> str:
    translations = {
        "ru": {"intel": f"Интеллект: {value}", "freq": f"Частота: {value}%", "custom": "Кастом"},
        "uk": {"intel": f"Інтелект: {value}", "freq": f"Частота: {value}%", "custom": "Кастом"},
        "en": {"intel": f"Intelligence: {value}", "freq": f"Frequency: {value}%", "custom": "Custom"}
    }
    return translations.get(lang, translations["en"])[setting]