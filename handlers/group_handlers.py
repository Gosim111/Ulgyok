from aiogram import Router, Bot, types
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
from aiogram.fsm.context import FSMContext
from storage.memory import BotMemory
from utils.helpers import is_admin, get_available_reactions, translate_button
from states.settings_states import SettingsState
import random
import logging
import aiosqlite

# Инициализация роутера и памяти
group_router = Router()
memory = BotMemory()
logger = logging.getLogger(__name__)

# Глобальные переменные
chat_reactions_cache = {}
active_settings_user = {}  # Хранит {chat_id: user_id}

# Сообщения на разных языках
MESSAGES = {
    "ru": {
        "start": "Привет всем, меня Углём звать. Настройте язык, позязя :)",
        "only_admins": "Только администраторы могут настраивать меня!",
        "settings_in_use": "Настройки уже использует другой пользователь!",
        "intel_prompt": "Ответьте числом (0-100) на это сообщение для уровня интеллекта:",
        "freq_prompt": "Ответьте числом (0-100) на это сообщение для частоты ответа:",
        "invalid_range": "Значение должно быть от 0 до 100!",
        "no_reactions": "Реакции в этом чате отключены или не настроены.",
        "no_messages": "Я еще не знаю, что сказать!",
        "back": "Назад"
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
        "back": "Назад"
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
        "back": "Back"
    }
}

# Обработчик добавления бота в группу
@group_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: types.ChatMemberUpdated, bot: Bot):
    if event.new_chat_member.user.id == event.bot.id:
        chat_id = event.chat.id
        chat_title = event.chat.title or "Unnamed Chat"
        await memory.add_chat(chat_id, chat_title)
        logger.info(f"Бот добавлен в чат {chat_id} с названием {chat_title}")
        if chat_id in chat_reactions_cache:
            del chat_reactions_cache[chat_id]  # Очищаем кэш реакций при добавлении

# Обработчик сообщений в группе (кроме команд /start и /settings)
@group_router.message(~Command(commands=["start", "settings"]))
async def handle_group_message(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    message_id = message.message_id
    logger.debug(f"Получено сообщение в чате {chat_id}, ID: {message_id}")

    # Регистрируем чат, если он новый
    async with aiosqlite.connect("uglyok.db") as db:
        cursor = await db.execute("SELECT COUNT(*) FROM chats WHERE chat_id = ?", (chat_id,))
        count = (await cursor.fetchone())[0]
        if count == 0:
            chat_title = message.chat.title or "Unnamed Chat"
            await memory.add_chat(chat_id, chat_title)
            logger.info(f"Чат {chat_id} зарегистрирован: {chat_title}")

    # Сохраняем сообщение, если оно уникально
    content = message.text if message.text else message.sticker.file_id if message.sticker else None
    msg_type = "text" if message.text else "sticker" if message.sticker else None
    if content and msg_type:
        if not await memory.message_exists(chat_id, msg_type, content):
            await memory.add_message(chat_id, msg_type, content)
            logger.debug(f"Сохранено сообщение типа {msg_type}: {content}")
        else:
            logger.debug(f"Сообщение типа {msg_type} '{content}' уже существует, пропускаем")

    # Проверяем частоту ответа
    frequency = await memory.get_response_frequency(chat_id)
    logger.debug(f"Частота ответа для чата {chat_id}: {frequency}%")
    lang = await memory.get_language(chat_id)

    # Шанс поставить реакцию
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

    # Шанс отправить текстовый ответ (независимо от реакции)
    if random.randint(0, 100) <= frequency:
        random_message = await memory.get_random_message(chat_id)
        if random_message:
            await message.reply(random_message)
            logger.debug(f"Отправлен текстовый ответ '{random_message}' в чате {chat_id}")
        else:
            await message.reply(MESSAGES[lang]["no_messages"])
            logger.debug(f"Нет сохраненных сообщений для чата {chat_id}, отправлено стандартное сообщение")

# Обработчик reply для кастомного интеллекта
@group_router.message(SettingsState.CustomIntel, lambda m: m.text and m.text.isdigit() and m.reply_to_message)
async def set_custom_intelligence(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await memory.get_language(chat_id)
    data = await state.get_data()

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await message.reply(MESSAGES[lang]["settings_in_use"])
        return

    if "message_id" not in data or message.reply_to_message.message_id != data["message_id"]:
        return  # Игнорируем, если это не ответ на нужное сообщение

    level = int(message.text)
    if 0 <= level <= 100:
        await memory.set_intelligence(chat_id, level)
        await message.reply(f"{translate_button('intel', level, lang)} set!")
        await state.clear()
        if chat_id in active_settings_user:
            del active_settings_user[chat_id]  # Освобождаем настройки
    else:
        await message.reply(MESSAGES[lang]["invalid_range"])

# Обработчик reply для кастомной частоты
@group_router.message(SettingsState.CustomFreq, lambda m: m.text and m.text.isdigit() and m.reply_to_message)
async def set_custom_frequency(message: types.Message, bot: Bot, state: FSMContext):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await memory.get_language(chat_id)
    data = await state.get_data()

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await message.reply(MESSAGES[lang]["settings_in_use"])
        return

    if "message_id" not in data or message.reply_to_message.message_id != data["message_id"]:
        return  # Игнорируем, если это не ответ на нужное сообщение

    freq = int(message.text)
    if 0 <= freq <= 100:
        await memory.set_response_frequency(chat_id, freq)
        await message.reply(f"{translate_button('freq', freq, lang)} set!")
        await state.clear()
        if chat_id in active_settings_user:
            del active_settings_user[chat_id]  # Освобождаем настройки
    else:
        await message.reply(MESSAGES[lang]["invalid_range"])

# Обработчик команды /start
@group_router.message(Command("start"))
async def start_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await memory.get_language(chat_id)
    logger.info(f"Команда /start в чате {chat_id} от пользователя {user_id}")

    if not await is_admin(bot, chat_id, user_id):
        await message.reply(MESSAGES[lang]["only_admins"])
        return

    buttons = [
        InlineKeyboardButton(text="Русский 🇷🇺", callback_data=f"lang_{chat_id}_ru"),
        InlineKeyboardButton(text="Українська 🇺🇦", callback_data=f"lang_{chat_id}_uk"),
        InlineKeyboardButton(text="English 🇺🇸", callback_data=f"lang_{chat_id}_en")
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    await message.reply(MESSAGES[lang]["start"], reply_markup=keyboard)

# Обработчик выбора языка
@group_router.callback_query(lambda c: c.data.startswith("lang_"))
async def process_language_selection(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    chat_id = int(parts[1])
    lang = parts[2]
    user_id = callback.from_user.id

    if not await is_admin(bot, chat_id, user_id):
        await callback.answer(MESSAGES[lang]["only_admins"], show_alert=True)
        return

    if await memory.set_language(chat_id, lang):
        await callback.message.edit_text(
            f"Language set to {lang}!" if lang == "en" else
            f"Мова встановлена на {lang}!" if lang == "uk" else
            f"Язык установлен на {lang}!"
        )
    else:
        await callback.message.edit_text("Error setting language!")
    await callback.answer()

# Обработчик команды /settings
@group_router.message(Command("settings"))
async def settings_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await memory.get_language(chat_id)
    logger.info(f"Команда /settings в чате {chat_id} от пользователя {user_id}")

    if not await is_admin(bot, chat_id, user_id):
        await message.reply(MESSAGES[lang]["only_admins"])
        return

    if chat_id in active_settings_user and active_settings_user[chat_id] != user_id:
        await message.reply(MESSAGES[lang]["settings_in_use"])
        return

    active_settings_user[chat_id] = user_id
    intelligence = await memory.get_intelligence(chat_id)
    frequency = await memory.get_response_frequency(chat_id)

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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    await message.reply("Settings:", reply_markup=keyboard)

# Обработчик меню интеллекта
@group_router.callback_query(lambda c: c.data.startswith("set_intel_menu_"))
async def intel_menu(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await memory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    intelligence = await memory.get_intelligence(chat_id)
    buttons = [
        [InlineKeyboardButton(text="0", callback_data=f"set_intel_{chat_id}_0"),
         InlineKeyboardButton(text="50", callback_data=f"set_intel_{chat_id}_50"),
         InlineKeyboardButton(text="100", callback_data=f"set_intel_{chat_id}_100")],
        [InlineKeyboardButton(text=translate_button("custom", intelligence, lang), callback_data=f"custom_intel_{chat_id}")],
        [InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back_to_settings_{chat_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    await callback.message.edit_text(translate_button("intel", intelligence, lang), reply_markup=keyboard)
    await callback.answer()

# Обработчик выбора интеллекта
@group_router.callback_query(lambda c: c.data.startswith("set_intel_"))
async def process_intelligence_selection(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    level = int(parts[3])
    user_id = callback.from_user.id
    lang = await memory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    if await memory.set_intelligence(chat_id, level):
        await callback.message.edit_text(f"{translate_button('intel', level, lang)} set!")
    else:
        await callback.message.edit_text("Error setting intelligence!")
    await callback.answer()

# Обработчик кастомного интеллекта
@group_router.callback_query(lambda c: c.data.startswith("custom_intel_"))
async def process_custom_intelligence(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await memory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    await state.set_state(SettingsState.CustomIntel)
    await state.update_data(chat_id=chat_id, user_id=user_id, message_id=callback.message.message_id)
    await callback.message.edit_text(MESSAGES[lang]["intel_prompt"])
    await callback.answer()

# Обработчик меню частоты ответа
@group_router.callback_query(lambda c: c.data.startswith("set_freq_menu_"))
async def freq_menu(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await memory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    frequency = await memory.get_response_frequency(chat_id)
    buttons = [
        [InlineKeyboardButton(text="0%", callback_data=f"set_freq_{chat_id}_0"),
         InlineKeyboardButton(text="50%", callback_data=f"set_freq_{chat_id}_50"),
         InlineKeyboardButton(text="100%", callback_data=f"set_freq_{chat_id}_100")],
        [InlineKeyboardButton(text=translate_button("custom", frequency, lang), callback_data=f"custom_freq_{chat_id}")],
        [InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back_to_settings_{chat_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    await callback.message.edit_text(translate_button("freq", frequency, lang), reply_markup=keyboard)
    await callback.answer()

# Обработчик выбора частоты
@group_router.callback_query(lambda c: c.data.startswith("set_freq_"))
async def process_frequency_selection(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    freq = int(parts[3])
    user_id = callback.from_user.id
    lang = await memory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    if await memory.set_response_frequency(chat_id, freq):
        await callback.message.edit_text(f"{translate_button('freq', freq, lang)} set!")
    else:
        await callback.message.edit_text("Error setting frequency!")
    await callback.answer()

# Обработчик кастомной частоты
@group_router.callback_query(lambda c: c.data.startswith("custom_freq_"))
async def process_custom_frequency(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await memory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    await state.set_state(SettingsState.CustomFreq)
    await state.update_data(chat_id=chat_id, user_id=user_id, message_id=callback.message.message_id)
    await callback.message.edit_text(MESSAGES[lang]["freq_prompt"])
    await callback.answer()

# Обработчик кнопки "Назад"
@group_router.callback_query(lambda c: c.data.startswith("back_to_settings_"))
async def back_to_settings(callback: types.CallbackQuery, bot: Bot):
    chat_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await memory.get_language(chat_id)

    if chat_id not in active_settings_user or active_settings_user[chat_id] != user_id:
        await callback.answer(MESSAGES[lang]["settings_in_use"], show_alert=True)
        return

    intelligence = await memory.get_intelligence(chat_id)
    frequency = await memory.get_response_frequency(chat_id)
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    await callback.message.edit_text("Settings:", reply_markup=keyboard)
    await callback.answer()