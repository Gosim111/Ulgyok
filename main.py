import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers.group_handlers import group_router
from storage.memory import BotMemory

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(group_router)

    memory = BotMemory()
    await memory.init_db()

    logger.info("Бот Углёк запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())