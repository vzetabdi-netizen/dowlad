import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import Database
from handlers import start, downloader, admin, payment, stats
from middlewares.throttle import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Init DB
    db = Database()
    await db.connect()

    # Attach db to dispatcher
    dp["db"] = db

    # Middlewares
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.5))

    # Routers
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(downloader.router)
    dp.include_router(admin.router)
    dp.include_router(stats.router)

    logger.info("Bot started!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
