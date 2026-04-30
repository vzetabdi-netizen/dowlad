# 🎬 All-in-One Video Downloader Bot

A powerful Telegram bot that downloads videos from TikTok, YouTube, Instagram, Facebook, X/Twitter, and Pinterest — with a Free/Pro subscription system powered by Telegram Stars.

---

## ✨ Features

### User Features
| Feature | Free | Pro |
|---------|------|-----|
| Daily downloads | 5/day | 100/day |
| Video quality | SD (480p) | HD (1080p) |
| TikTok (no watermark) | ✅ | ✅ |
| YouTube | ✅ | ✅ |
| Instagram | ✅ | ✅ |
| Facebook | ✅ | ✅ |
| X / Twitter | ✅ | ✅ |
| Pinterest | ✅ | ✅ |

### Admin Features
- 📊 Global stats dashboard
- 👑 Top 10 users leaderboard
- 🚫 Ban / unban users
- 💎 Grant/revoke premium manually
- 📢 Broadcast (text, photo, video, document)
- 💰 Change Pro price (Telegram Stars)
- 🛡️ `/rpremiumall` with confirmation — skips paid users

---

## 🚀 Quick Start

### 1. Clone
```bash
git clone https://github.com/yourname/downloader-bot.git
cd downloader-bot
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Run with Docker (recommended)
```bash
docker-compose up -d
```

### 4. Run locally
```bash
pip install -r requirements.txt
sudo apt install ffmpeg          # or: brew install ffmpeg
python bot.py
```

---

## ⚙️ Configuration

Edit `.env`:

```env
BOT_TOKEN=your_bot_token        # From @BotFather
ADMIN_IDS=123456789             # Comma-separated admin user IDs
MONGO_URI=mongodb://localhost:27017
DB_NAME=downloader_bot
```

Edit `config.py` to change:
- `FREE_DAILY_LIMIT` — default: 5
- `PRO_DAILY_LIMIT` — default: 100 (set 0 for unlimited)
- `DEFAULT_PRO_PRICE_STARS` — default: 100 Stars
- `PRO_DAYS` in `handlers/payment.py` — default: 30 days

---

## 🌐 Deployment

### Render.com (Free tier)
1. Push code to GitHub
2. Create a new **Background Worker** on Render
3. Connect your repo
4. Set environment variables in Render dashboard
5. Deploy!

> ⚠️ Render free tier sleeps after inactivity. Use a paid plan or keep-alive ping for 24/7 uptime.

### Railway / Fly.io
Same approach — use `Dockerfile` for containerized deployment.

### MongoDB
Use [MongoDB Atlas](https://www.mongodb.com/atlas) free tier (512 MB) — works perfectly for this bot.

---

## 📋 Commands

### User Commands
```
/start      — Welcome screen + plan info
/myplan     — Your plan, quota, expiry
/mystats    — Download statistics
/upgrade    — Upgrade to Pro (Telegram Stars)
/help       — Usage guide
```

### Admin Commands
```
/stats                  — Global bot statistics
/topusers               — Top 10 downloaders
/ban [user_id]          — Ban a user
/unban [user_id]        — Unban a user
/premium [id] [days]    — Grant premium
/rpremium [id]          — Remove premium (skips paid users)
/premiumall [days]      — Give all users premium
/rpremiumall            — Remove all non-paid premium (with confirm)
/broadcast              — Send message to all users
/setprice [stars]       — Change Pro price
```

---

## 🏗️ Architecture

```
downloader_bot/
├── bot.py                  # Entry point
├── config.py               # All settings
├── database.py             # MongoDB operations
├── handlers/
│   ├── start.py            # /start, /myplan, /help
│   ├── downloader.py       # Link detection + download
│   ├── payment.py          # Telegram Stars payment
│   ├── admin.py            # All admin commands
│   └── stats.py            # /mystats
├── keyboards/
│   └── kb.py               # Inline + reply keyboards
├── middlewares/
│   └── throttle.py         # Rate limiting
└── utils/
    └── downloader.py       # yt-dlp wrapper
```

---

## 🔧 Tech Stack

- **Framework**: [aiogram 3](https://docs.aiogram.dev/) — async, modern
- **Database**: [MongoDB](https://www.mongodb.com/) via Motor (async driver)
- **Downloader**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) — supports all platforms
- **Payments**: Telegram Stars (native, no external gateway)
- **Hosting**: Render / Railway / Docker

---

## 💡 Notes

- Telegram has a **50 MB file size limit** for bots. Very long YouTube videos may fail.
- Instagram private content requires cookies — set up `cookies.txt` with yt-dlp if needed.
- Facebook videos must be **publicly accessible**.
- yt-dlp is updated frequently. Run `pip install -U yt-dlp` to stay current.

---

## 📄 License

MIT License. Use freely, modify as needed.
