import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import (
    BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PATH,
    WEBAPP_HOST, WEBAPP_PORT, validate_config,
)
from database import Database
from handlers import start, downloader, admin, payment, stats
from middlewares.throttle import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"


def main():
    # ── Validate environment up front ───────────────────
    problems = validate_config()
    if problems:
        logger.error("=" * 60)
        logger.error("CONFIGURATION ERRORS — bot will NOT work until you fix these:")
        for p in problems:
            logger.error("  • %s", p)
        logger.error("=" * 60)
        # Don't exit — keep the web server up so /info shows the error
        # and Render's health check still passes. This makes debugging easier.

    bot = Bot(
        token=BOT_TOKEN or "0:invalid",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # ── Database ────────────────────────────────────────
    db = Database()
    dp.workflow_data.update({"db": db})

    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.5))

    # ── Routers ─────────────────────────────────────────
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(downloader.router)
    dp.include_router(admin.router)
    dp.include_router(stats.router)

    startup_state = {"db_ok": False, "webhook_ok": False, "last_error": None}

    # ── Startup / shutdown ──────────────────────────────
    async def on_startup():
        if problems:
            logger.error("Skipping startup actions because of config errors above.")
            return
        try:
            await db.connect()
            startup_state["db_ok"] = True
            logger.info("MongoDB connected OK")
        except Exception as e:
            startup_state["last_error"] = f"MongoDB connect failed: {e}"
            logger.exception("MongoDB connect FAILED")

        try:
            await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
            info = await bot.get_webhook_info()
            startup_state["webhook_ok"] = (info.url == WEBHOOK_URL)
            logger.info("Webhook set to: %s", WEBHOOK_URL)
            logger.info(
                "Webhook info: url=%s, pending=%s, last_error=%s",
                info.url, info.pending_update_count, info.last_error_message,
            )
        except Exception as e:
            startup_state["last_error"] = f"set_webhook failed: {e}"
            logger.exception("set_webhook FAILED")

    async def on_shutdown():
        try:
            await bot.delete_webhook()
            logger.info("Webhook deleted")
        except Exception:
            logger.exception("delete_webhook failed")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── aiohttp app ─────────────────────────────────────
    app = web.Application()

    async def health(request):
        return web.Response(text="Bot is running!")

    async def info(request):
        # Useful diagnostic page — visit https://<your-render-url>/info
        try:
            wh = await bot.get_webhook_info()
            wh_data = {
                "url": wh.url,
                "pending_update_count": wh.pending_update_count,
                "last_error_date": str(wh.last_error_date) if wh.last_error_date else None,
                "last_error_message": wh.last_error_message,
                "ip_address": wh.ip_address,
            }
        except Exception as e:
            wh_data = {"error": str(e)}
        return web.json_response({
            "expected_webhook_url": WEBHOOK_URL,
            "config_problems": problems,
            "startup_state": startup_state,
            "telegram_webhook_info": wh_data,
        })

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/info", info)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logger.info("Starting web server on %s:%s", WEBAPP_HOST, WEBAPP_PORT)
    logger.info("Webhook URL: %s", WEBHOOK_URL)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


if __name__ == "__main__":
    main()
