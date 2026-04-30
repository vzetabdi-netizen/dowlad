from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database import Database

router = Router()


@router.message(Command("mystats"))
@router.message(F.text == "📊 My Stats")
async def cmd_mystats(message: Message, db: Database):
    user_id = message.from_user.id
    await db.ensure_user(user_id, message.from_user.username, message.from_user.full_name)

    user = await db.get_user(user_id)
    is_pro = await db.is_pro(user_id)
    can_dl, used_today, limit = await db.check_limit(user_id)

    total = user.get("total_downloads", 0)
    success = user.get("total_success", 0)
    failed = user.get("total_failed", 0)
    success_rate = f"{(success / total * 100):.1f}%" if total > 0 else "N/A"

    plan_str = "💎 Pro" if is_pro else "🆓 Free"
    remaining = "∞" if (is_pro and limit == 0) else str(max(0, limit - used_today))

    text = (
        f"📊 <b>Your Statistics</b>\n\n"
        f"👤 Plan: {plan_str}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📥 Today: <b>{used_today}/{limit if limit else '∞'}</b>\n"
        f"⏳ Remaining today: <b>{remaining}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📈 Total downloads: <b>{total}</b>\n"
        f"✅ Successful: <b>{success}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"📊 Success rate: <b>{success_rate}</b>\n"
    )
    await message.answer(text)
