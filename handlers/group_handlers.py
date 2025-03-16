from aiogram import Router, Bot, types
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
from aiogram.fsm.context import FSMContext
from storage.memory import BotMemory  # Импортируем глобальный memory
from utils.helpers import is_admin, get_available_reactions
from utils.text_modifier import TextModifier
from states.settings_states import SettingsState
import random
import logging

group_router = Router()
logger = logging.getLogger(__name__)

chat_reactions_cache = {}
active_settings_user = {}

MESSAGES = {
    "ru": {
        "start": "Привет всем, меня Углём звать. Настройте язык, позязя :)",
        "only_admins": "Только администраторы могут настраивать меня!",
        "settings_in_use": "Настройки уже использует другой пользователь!",
        "intel_prompt": "Ответьте числом от 0 до 100 на это сообщение для уровня интеллекта:",
        "freq_prompt": "Ответьте числом от 0 до 100 на это сообщение для частоты ответа:",
        "invalid_range": "Значение должно быть от 0 до 100!",
        "no_reactions": "Реакции в этом чате отключены или не настроены.",
        "no_messages": "Я еще не знаю, что сказать!",
        "back": "Назад",
        "help": "*Справка по Угольку:*\n"
                "• `/start` - Настроить язык (только админы)\n"
                "• `/settings` - Изменить интеллект и частоту (только админы)\n"
                "• `/help` - Показать эту справку\n"
                "• `/forget_me` - Удалить все данные чата (только админы)",
        "forget_confirm": "Вы уверены, что хотите удалить все данные чата? Это нельзя отменить!",
        "forget_success": "Все данные чата удалены.",
        "forget_error": "Ошибка при удалении данных чата."
    },
    "uk": {
        "start": "Привіт усім, мене Вуглем звати. Налаштуйте мову, будь ласка :)",
        "only_admins": "Тільки адміністратори можуть мене налаштовувати!",
        "settings_in_use": "Налаштування вже використовує інший користувач!",
        "intel_prompt": "Відповідьте числом (0-100) на це повідомлення для рівня інтелекту:",
        "freq_prompt": "Відповідьте числом (0-100) на це повідомлення для частоти відповіді:",
        "invalid_range": "Значення має бути від 0 до 100!",
        "no_reactions": "Реакції в цьому чаті відключені або не налаштовані.",
        "no_messages": "Я ще не знаю, що сказати!",
        "back": "Назад",
        "help": "*Довідка по Вуглю:*\n"
                "• `/start` - Налаштувати мову (тільки адміни)\n"
                "• `/settings` - Змінити інтелект і частоту (тільки адміни)\n"
                "• `/help` - Показати цю довідку\n"
                "• `/forget_me` - Видалити всі дані чату (тільки адміни)",
        "forget_confirm": "Ви впевнені, що хочете видалити всі дані чату? Це не можна скасувати!",
        "forget_success": "Усі дані чату видалено.",
        "forget_error": "Помилка при видаленні даних чату."
    },
    "en": {
        "start": "Hello everyone, I'm called Uglyok. Please set the language :)",
        "only_admins": "Only administrators can configure me!",
        "settings_in_use": "Settings are already in use by another user!",
        "intel_prompt": "Reply with a number (0-100) to this message for intelligence level:",
        "freq_prompt": "Reply with a number (0-100) to this message for response frequency:",
        "invalid_range": "Value must be between 0 and 100!",
        "no_reactions": "Reactions in this chat are disabled or not configured.",
        "no_messages": "I don't know what to say yet!",
        "back": "Back",
        "help": "*Uglyok Help:*\n"
                "• `/start` - Set language (admins only)\n"
                "• `/settings` - Adjust intelligence and frequency (admins only)\n"
                "• `/help` - Show this help\n"
                "• `/forget_me` - Delete all chat data (admins only)",
        "forget_confirm": "Are you sure you want to delete all chat data? This cannot be undone!",
        "forget_success": "All chat data has been deleted.",
        "forget_error": "Error deleting chat data."
    }
}

def translate_button(button: str, value: int, lang: str) -> str:
    """Перевод кнопок настроек."""
    if button == "intel":
        return f"Intelligence: {value}" if lang == "en" else f"Інтелект: {value}" if lang == "uk" else f"Интеллект: {value}"
    elif button == "freq":
        return f"Frequency: {value}%" if lang == "en" else f"Частота: {value}%" if lang == "uk" else f"Частота: {value}%"
    elif button == "custom":
        return f"Custom ({value})" if lang == "en" else f"Кастом ({value})" if lang == "uk" else f"Кастом ({value})"
    return button

@group_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: types.ChatMemberUpdated, bot: Bot):
    if event.new_chat_member.user.id == event.bot.id:
        chat_id = event.chat.id
        chat_title = event.chat.title or "Unnamed Chat"
        try:
            await BotMemory.add_chat(chat_id, chat_title)
            logger.info(f"Бот добавлен в чат {chat_id} с названием {chat_title}")
            if chat_id in chat_reactions_cache:
                del chat_reactions_cache[chat_id]
        except Exception as e:
            logger.error(f"Ошибка при добавлении чата {chat_id}: {e}")

@group_router.message(~Command(commands=["start", "settings", "help", "forget_me"]))
async def handle_group_message(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    message_id = message.message_id
    text_modifier = TextModifier(BotMemory)
    logger.debug(f"Получено сообщение в чате {chat_id}, ID: {message_id}")

    # Регистрируем чат, если его нет
    try:
        cursor = await BotMemory.db.execute("SELECT COUNT(*) FROM chats WHERE chat_id = ?", (chat_id,))
        count = (await cursor.fetchone())[0]
        if count == 0:
            chat_title = message.chat.title or "Unnamed Chat"
            await BotMemory.add_chat(chat_id, chat_title)
            logger.info(f"Чат {chat_id} зарегистрирован: {chat_title}")
    except Exception as e:
        logger.error(f"Ошибка при проверке/регистрации чата {chat_id}: {e}")
        return

    # Сохраняем сообщение
    content = message.text if message.text else message.sticker.file_id if message.sticker else None
    msg_type = "text" if message.text else "sticker" if message.sticker else None
    if content and msg_type:
        try:
            if not await BotMemory.message_exists(chat_id, msg_type, content):
                await BotMemory.add_message(chat_id, msg_type, content)
                logger.debug(f"Сохранено сообщение типа {msg_type}: {content}")
            else:
                logger.debug(f"Сообщение типа {msg_type} '{content}' уже существует, пропускаем")
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения в чате {chat_id}: {e}")

    # Получаем настройки
    frequency = await BotMemory.get_response_frequency(chat_id)
    intelligence = await BotMemory.get_intelligence(chat_id)
    lang = await BotMemory.get_language(chat_id)
    logger.debug(f"Частота ответа для чата {chat_id}: {frequency}%, интеллект: {intelligence}")

    # Устанавливаем реакцию
    available_reactions = await get_available_reactions(bot, chat_id, chat_reactions_cache)
    if available_reactions and random.randint(0, 100) <= frequency:
        reaction = random.choice(available_reactions)
        try:
            await bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji=reaction)],
                is_big=False
            )
            logger.debug(f"Установлена реакция {reaction} на сообщение {message_id} в чате {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при установке реакции {reaction} в чате {chat_id}: {e}")

    # Отправляем случайное сообщение с учетом интеллекта
    if random.randint(0, 100) <= frequency:
        msg_type, random_message = await BotMemory.get_random_message(chat_id)
        if random_message:
            try:
                if msg_type == "text":
                    modified_message = await text_modifier.modify_text(chat_id, random_message, intelligence)
                    await bot.send_message(chat_id=chat_id, text=modified_message)
                    logger.debug(f"Отправлен модифицированный текст '{modified_message}' в чате {chat_id}")
                elif msg_type == "sticker":
                    await bot.send_sticker(chat_id=chat_id, sticker=random_message)
                    logger.debug(f"Отправлен стикер '{random_message}' в чате {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке ответа в чате {chat_id}: {e}")
        else:
            try:
                await bot.send_message(chat_id=chat_id, text=MESSAGES[lang]["no_messages"])
                logger.debug(f"Нет сохраненных сообщений для чата {chat_id}, отправлено стандартное сообщение")
            except Exception as e:
                logger.error(f"Ошибка при отправке 'no_messages' в чате {chat_id}: {e}")

@group_router.message(Command("start"))
async def start_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await BotMemory.get_language(chat_id)
    logger.info(f"Команда /start в чате {chat_id} от пользователя {user_id}")

    if not await is_admin(bot, chat_id, user_id):
        await message.reply(MESSAGES[lang]["only_admins"])
        return

    buttons = [
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data=f"lang_{chat_id}_ru")],
        [InlineKeyboardButton(text="Українська 🇺🇦", callback_data=f"lang_{chat_id}_uk")],
        [InlineKeyboardButton(text="English 🇺🇸", callback_data=f"lang_{chat_id}_en")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.reply(MESSAGES[lang]["start"], reply_markup=keyboard)

@group_router.callback_query(lambda c: c.data.startswith("lang_"))
async def process_language_selection(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    chat_id = int(parts[1])
    lang = parts[2]
    user_id = callback.from_user.id

    if not await is_admin(bot, chat_id, user_id):
        await callback.answer(MESSAGES[lang]["only_admins"], show_alert=True)
        return

    try:
        if await BotMemory.set_language(chat_id, lang):
            await callback.message.edit_text(
                f"Language set to {lang}!" if lang == "en" else
                f"Мова встановлена на {lang}!" if lang == "uk" else
                f"Язык установлен на {lang}!"
            )
        else:
            await callback.message.edit_text("Error setting language!")
    except Exception as e:
        logger.error(f"Ошибка при установке языка в чате {chat_id}: {e}")
        await callback.message.edit_text("Error setting language!")
    await callback.answer()

@group_router.message(Command("settings"))
async def settings_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await BotMemory.get_language(chat_id)
    logger.info(f"Команда /settings в чате {chat_id} от пользователя {user_id}")

    if not await is_admin(bot, chat_id, user_id):
        await message.reply(MESSAGES[lang]["only_admins"])
        return

    if chat_id in active_settings_user and active_settings_user[chat_id] != user_id:
        await message.reply(MESSAGES[lang]["settings_in_use"])
        return

    active_settings_user[chat_id] = user_id
    intelligence = await BotMemory.get_intelligence(chat_id)
    frequency = await BotMemory.get_response_frequency(chat_id)

    buttons = [
        [InlineKeyboardButton(
            text=translate_button("intel", intelligence, lang),
            callback_data=f"set_intel_menu_{chat_id}"
        )],
        [InlineKeyboardButton(
            text=translate_button("freq", frequency, lang),
            callback_data=f"set_freq_menu_{chat_id}"
        )]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.reply("Settings:", reply_markup=keyboard)

@group_router.callback_query(lambda c: c.data.startswith("set_intel_menu_"))
async def intel_menu(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await BotMemory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    intelligence = await BotMemory.get_intelligence(chat_id)
    buttons = [
        [InlineKeyboardButton(text="0", callback_data=f"set_intel_{chat_id}_0"),
         InlineKeyboardButton(text="50", callback_data=f"set_intel_{chat_id}_50"),
         InlineKeyboardButton(text="100", callback_data=f"set_intel_{chat_id}_100")],
        [InlineKeyboardButton(text=translate_button("custom", intelligence, lang), callback_data=f"custom_intel_{chat_id}")],
        [InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back_to_settings_{chat_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(translate_button("intel", intelligence, lang), reply_markup=keyboard)
    await callback.answer()

@group_router.callback_query(lambda c: c.data.startswith("set_intel_"))
async def process_intelligence_selection(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    level = int(parts[3])
    user_id = callback.from_user.id
    lang = await BotMemory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    try:
        if await BotMemory.set_intelligence(chat_id, level):
            await callback.message.edit_text(f"{translate_button('intel', level, lang)} set!")
        else:
            await callback.message.edit_text("Error setting intelligence!")
    except Exception as e:
        logger.error(f"Ошибка при установке интеллекта в чате {chat_id}: {e}")
        await callback.message.edit_text("Error setting intelligence!")
    await callback.answer()

@group_router.callback_query(lambda c: c.data.startswith("custom_intel_"))
async def process_custom_intelligence(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await BotMemory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    await state.set_state(SettingsState.CustomIntel)
    await state.update_data(chat_id=chat_id, user_id=user_id, message_id=callback.message.message_id)
    await callback.message.edit_text(MESSAGES[lang]["intel_prompt"])
    await callback.answer()

@group_router.message(SettingsState.CustomIntel, lambda m: m.text and m.text.isdigit() and m.reply_to_message)
async def set_custom_intelligence(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await BotMemory.get_language(chat_id)
    data = await state.get_data()

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await message.reply(MESSAGES[lang]["settings_in_use"])
        return

    if "message_id" not in data or message.reply_to_message.message_id != data["message_id"]:
        return

    level = int(message.text)
    if 0 <= level <= 100:
        try:
            await BotMemory.set_intelligence(chat_id, level)
            await message.reply(f"{translate_button('intel', level, lang)} set!")
            await state.clear()
            if chat_id in active_settings_user:
                del active_settings_user[chat_id]
        except Exception as e:
            logger.error(f"Ошибка при установке интеллекта в чате {chat_id}: {e}")
            await message.reply("Error setting intelligence!")
    else:
        await message.reply(MESSAGES[lang]["invalid_range"])

@group_router.callback_query(lambda c: c.data.startswith("set_freq_menu_"))
async def freq_menu(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await BotMemory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    frequency = await BotMemory.get_response_frequency(chat_id)
    buttons = [
        [InlineKeyboardButton(text="0%", callback_data=f"set_freq_{chat_id}_0"),
         InlineKeyboardButton(text="50%", callback_data=f"set_freq_{chat_id}_50"),
         InlineKeyboardButton(text="100%", callback_data=f"set_freq_{chat_id}_100")],
        [InlineKeyboardButton(text=translate_button("custom", frequency, lang), callback_data=f"custom_freq_{chat_id}")],
        [InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back_to_settings_{chat_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(translate_button("freq", frequency, lang), reply_markup=keyboard)
    await callback.answer()

@group_router.callback_query(lambda c: c.data.startswith("set_freq_"))
async def process_frequency_selection(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    freq = int(parts[3])
    user_id = callback.from_user.id
    lang = await BotMemory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    try:
        if await BotMemory.set_response_frequency(chat_id, freq):
            await callback.message.edit_text(f"{translate_button('freq', freq, lang)} set!")
        else:
            await callback.message.edit_text("Error setting frequency!")
    except Exception as e:
        logger.error(f"Ошибка при установке частоты в чате {chat_id}: {e}")
        await callback.message.edit_text("Error setting frequency!")
    await callback.answer()

@group_router.callback_query(lambda c: c.data.startswith("custom_freq_"))
async def process_custom_frequency(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await BotMemory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    await state.set_state(SettingsState.CustomFreq)
    await state.update_data(chat_id=chat_id, user_id=user_id, message_id=callback.message.message_id)
    await callback.message.edit_text(MESSAGES[lang]["freq_prompt"])
    await callback.answer()

@group_router.message(SettingsState.CustomFreq, lambda m: m.text and m.text.isdigit() and m.reply_to_message)
async def set_custom_frequency(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await BotMemory.get_language(chat_id)
    data = await state.get_data()

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await message.reply(MESSAGES[lang]["settings_in_use"])
        return

    if "message_id" not in data or message.reply_to_message.message_id != data["message_id"]:
        return

    freq = int(message.text)
    if 0 <= freq <= 100:
        try:
            await BotMemory.set_response_frequency(chat_id, freq)
            await message.reply(f"{translate_button('freq', freq, lang)} set!")
            await state.clear()
            if chat_id in active_settings_user:
                del active_settings_user[chat_id]
        except Exception as e:
            logger.error(f"Ошибка при установке частоты в чате {chat_id}: {e}")
            await message.reply("Error setting frequency!")
    else:
        await message.reply(MESSAGES[lang]["invalid_range"])

@group_router.callback_query(lambda c: c.data.startswith("back_to_settings_"))
async def back_to_settings(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await BotMemory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    intelligence = await BotMemory.get_intelligence(chat_id)
    frequency = await BotMemory.get_response_frequency(chat_id)
    buttons = [
        [InlineKeyboardButton(
            text=translate_button("intel", intelligence, lang),
            callback_data=f"set_intel_menu_{chat_id}"
        )],
        [InlineKeyboardButton(
            text=translate_button("freq", frequency, lang),
            callback_data=f"set_freq_menu_{chat_id}"
        )]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Settings:", reply_markup=keyboard)
    await callback.answer()

@group_router.message(Command("help"))
async def help_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    lang = await BotMemory.get_language(chat_id)
    logger.info(f"Команда /help вызвана в чате {chat_id}")
    await message.reply(MESSAGES[lang]["help"], parse_mode="Markdown")

@group_router.message(Command("forget_me"))
async def forget_me_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await BotMemory.get_language(chat_id)
    logger.info(f"Команда /forget_me в чате {chat_id} от пользователя {user_id}")

    if not await is_admin(bot, chat_id, user_id):
        await message.reply(MESSAGES[lang]["only_admins"])
        return

    buttons = [
        [InlineKeyboardButton(text="Yes" if lang == "en" else "Так" if lang == "uk" else "Да",
                              callback_data=f"forget_confirm_{chat_id}")],
        [InlineKeyboardButton(text="No" if lang == "en" else "Ні" if lang == "uk" else "Нет",
                              callback_data=f"forget_cancel_{chat_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.reply(MESSAGES[lang]["forget_confirm"], reply_markup=keyboard)

@group_router.callback_query(lambda c: c.data.startswith("forget_confirm_"))
async def process_forget_confirm(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    text_modifier = TextModifier(BotMemory)
    lang = await BotMemory.get_language(chat_id)

    if not await is_admin(bot, chat_id, user_id):
        await callback.answer(MESSAGES[lang]["only_admins"], show_alert=True)
        return

    try:
        await BotMemory.clear_chat_data(chat_id)
        await text_modifier.clear_cache(chat_id)
        if chat_id in chat_reactions_cache:
            del chat_reactions_cache[chat_id]
        if chat_id in active_settings_user:
            del active_settings_user[chat_id]
        logger.info(f"Все данные чата {chat_id} удалены пользователем {user_id}")
        await callback.message.edit_text(MESSAGES[lang]["forget_success"])
    except Exception as e:
        logger.error(f"Ошибка при удалении данных чата {chat_id}: {e}")
        await callback.message.edit_text(MESSAGES[lang]["forget_error"])
    await callback.answer()

@group_router.callback_query(lambda c: c.data.startswith("forget_cancel_"))
async def process_forget_cancel(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    lang = await BotMemory.get_language(chat_id)
    await callback.message.edit_text("Operation cancelled." if lang == "en" else
                                     "Операцію скасовано." if lang == "uk" else
                                     "Операция отменена.")
    await callback.answer()