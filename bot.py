import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.types import Update

from config import BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT
from database import Database
from handlers import start, downloader, admin, payment, stats
from middlewares.throttle import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"


def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # ── Database ────────────────────────────────────────
    db = Database()

    # Pass db to all handlers via workflow_data
    dp.workflow_data.update({"db": db})

    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.5))

    # ── Routers ─────────────────────────────────────────
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(downloader.router)
    dp.include_router(admin.router)
    dp.include_router(stats.router)

    # ── Startup / shutdown ──────────────────────────────
    async def on_startup():
        await db.connect()
        await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
        info = await bot.get_webhook_info()
        logger.info(f"Webhook set: {WEBHOOK_URL}")
        logger.info(f"Webhook info: url={info.url}, pending={info.pending_update_count}")

    async def on_shutdown():
        await bot.delete_webhook()
        logger.info("Webhook deleted")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── aiohttp app ─────────────────────────────────────
    app = web.Application()

    async def health(request):
        return web.Response(text="Bot is running!")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logger.info(f"Starting on {WEBAPP_HOST}:{WEBAPP_PORT}")
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


if __name__ == "__main__":
    main()
