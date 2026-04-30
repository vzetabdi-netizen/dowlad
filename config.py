import os
from dotenv import load_dotenv

load_dotenv()

# ─── Bot ───────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ─── Webhook (Render Web Service) ──────────────────────
# Render automatically sets RENDER_EXTERNAL_URL to the public service URL,
# e.g. https://my-bot.onrender.com — so prefer that and fall back to a
# manually provided WEBHOOK_HOST. This avoids the #1 source of "bot is silent"
# bugs: forgetting to set WEBHOOK_HOST or leaving it as the placeholder.
WEBHOOK_HOST: str = (
    os.getenv("WEBHOOK_HOST")
    or os.getenv("RENDER_EXTERNAL_URL")
    or ""
).rstrip("/")

# Use a non-guessable path that includes the bot token for basic security.
WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", f"/webhook/{BOT_TOKEN}")
WEBAPP_HOST: str = "0.0.0.0"
WEBAPP_PORT: int = int(os.getenv("PORT", 8080))  # Render sets PORT automatically

# ─── Admin ─────────────────────────────────────────────
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# ─── MongoDB ───────────────────────────────────────────
MONGO_URI: str = os.getenv("MONGO_URI", "")
DB_NAME: str = os.getenv("DB_NAME", "downloader_bot")

# ─── Plans ─────────────────────────────────────────────
FREE_DAILY_LIMIT: int = 5
PRO_DAILY_LIMIT: int = 100          # set 0 = unlimited
DEFAULT_PRO_PRICE_STARS: int = 100  # Telegram Stars

# ─── Downloader ────────────────────────────────────────
DOWNLOAD_TIMEOUT: int = 60          # seconds
MAX_FILE_SIZE_MB: int = 50          # Telegram bot upload limit is 50 MB

# ─── Supported platforms ───────────────────────────────
SUPPORTED_DOMAINS = {
    "tiktok.com":    "tiktok",
    "vm.tiktok.com": "tiktok",
    "youtube.com":   "youtube",
    "youtu.be":      "youtube",
    "instagram.com": "instagram",
    "facebook.com":  "facebook",
    "fb.watch":      "facebook",
    "twitter.com":   "twitter",
    "x.com":         "twitter",
    "pinterest.com": "pinterest",
    "pin.it":        "pinterest",
}


def validate_config() -> list[str]:
    """Return a list of fatal config problems. Empty list = OK."""
    problems: list[str] = []
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        problems.append("BOT_TOKEN is missing. Set it in Render → Environment.")
    if not WEBHOOK_HOST:
        problems.append(
            "WEBHOOK_HOST is missing and RENDER_EXTERNAL_URL is not set. "
            "Set WEBHOOK_HOST to your full Render URL, e.g. https://my-bot.onrender.com"
        )
    elif WEBHOOK_HOST.startswith("http://"):
        problems.append("WEBHOOK_HOST must use https:// (Telegram requires HTTPS).")
    elif "your-app" in WEBHOOK_HOST or "your-app-name" in WEBHOOK_HOST:
        problems.append(
            f"WEBHOOK_HOST is still the placeholder ({WEBHOOK_HOST}). "
            "Replace it with your real Render URL."
        )
    if not MONGO_URI:
        problems.append("MONGO_URI is missing. Set it to your MongoDB Atlas connection string.")
    if not ADMIN_IDS:
        problems.append("ADMIN_IDS is missing. Set it to your Telegram user ID (number).")
    return problems
