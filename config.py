import os
from dotenv import load_dotenv

load_dotenv()

# ─── Bot ───────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ─── Admin ─────────────────────────────────────────────
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x
]

# ─── MongoDB ───────────────────────────────────────────
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME: str = os.getenv("DB_NAME", "downloader_bot")

# ─── Plans ─────────────────────────────────────────────
FREE_DAILY_LIMIT: int = 5
PRO_DAILY_LIMIT: int = 100          # set 0 = unlimited
DEFAULT_PRO_PRICE_STARS: int = 100  # Telegram Stars

# ─── Downloader ────────────────────────────────────────
DOWNLOAD_TIMEOUT: int = 60          # seconds
MAX_FILE_SIZE_MB: int = 50          # Telegram limit = 50 MB bots

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
