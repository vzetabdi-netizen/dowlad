from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from database import Database
from keyboards.kb import main_menu_kb, upgrade_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    user = message.from_user
    await db.ensure_user(user.id, user.username, user.full_name)

    is_pro = await db.is_pro(user.id)
    plan_badge = "💎 <b>Pro</b>" if is_pro else "🆓 <b>Free</b>"

    text = (
        f"👋 <b>Welcome, {user.first_name}!</b>\n\n"
        f"I can download videos from:\n"
        f"🎵 TikTok  ▶️ YouTube  📸 Instagram\n"
        f"📘 Facebook  🐦 X/Twitter  📌 Pinterest\n\n"
        f"Your plan: {plan_badge}\n\n"
        f"<b>Just send me a video link to get started!</b>"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(Command("myplan"))
@router.message(F.text == "💎 My Plan")
async def cmd_myplan(message: Message, db: Database):
    user_id = message.from_user.id
    await db.ensure_user(user_id, message.from_user.username, message.from_user.full_name)

    is_pro = await db.is_pro(user_id)
    user = await db.get_user(user_id)

    if is_pro:
        expiry = user.get("pro_expires")
        expiry_str = expiry.strftime("%Y-%m-%d") if expiry else "♾ Lifetime"
        text = (
            "💎 <b>Your Plan: Pro</b>\n\n"
            f"📅 Expires: <code>{expiry_str}</code>\n"
            f"📥 Daily limit: <b>100 downloads</b>\n"
            f"✅ HD quality: Enabled\n"
            f"⚡ Fast processing: Enabled"
        )
    else:
        from config import FREE_DAILY_LIMIT
        can_dl, used, limit = await db.check_limit(user_id)
        remaining = max(0, limit - used)
        text = (
            "🆓 <b>Your Plan: Free</b>\n\n"
            f"📥 Daily limit: <b>{limit} downloads</b>\n"
            f"✅ Used today: <b>{used}/{limit}</b>\n"
            f"⏳ Remaining: <b>{remaining}</b>\n\n"
            f"⬆️ Upgrade to <b>Pro</b> for 100 downloads/day + HD quality!"
        )
    await message.answer(text)


@router.message(Command("help"))
@router.message(F.text == "❓ Help")
async def cmd_help(message: Message):
    text = (
        "📖 <b>How to use:</b>\n\n"
        "1️⃣ Copy a video link from any supported platform\n"
        "2️⃣ Paste it here and send\n"
        "3️⃣ I'll download and send the video to you!\n\n"
        "✅ <b>Supported platforms:</b>\n"
        "🎵 TikTok (no watermark)\n"
        "▶️ YouTube\n"
        "📸 Instagram (posts, reels)\n"
        "📘 Facebook (public videos)\n"
        "🐦 X / Twitter\n"
        "📌 Pinterest\n\n"
        "📋 <b>Commands:</b>\n"
        "/start — Main menu\n"
        "/myplan — Your plan & quota\n"
        "/mystats — Download statistics\n"
        "/upgrade — Upgrade to Pro\n"
        "/help — This message\n\n"
        "💎 <b>Pro plan:</b>\n"
        "• 100 downloads/day\n"
        "• HD quality\n"
        "• Priority processing"
    )
    await message.answer(text)
