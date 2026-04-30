import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import Database
from keyboards.kb import admin_stats_kb, confirm_kb

router = Router()
logger = logging.getLogger(__name__)


# ─── Admin filter ──────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class BroadcastState(StatesGroup):
    waiting_content = State()


# ─── Stats ─────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return

    stats = await db.get_global_stats()
    text = _format_stats(stats)
    await message.answer(text, reply_markup=admin_stats_kb())


def _format_stats(s: dict) -> str:
    return (
        "📊 <b>Global Statistics</b>\n\n"
        f"👥 Total users: <b>{s['total_users']}</b>\n"
        f"💎 Pro users: <b>{s['pro_users']}</b>\n"
        f"🚫 Banned: <b>{s['banned_users']}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📥 Total downloads: <b>{s['total_downloads']}</b>\n"
        f"✅ Successful: <b>{s['total_success']}</b>\n"
        f"❌ Failed: <b>{s['total_failed']}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ Stars earned: <b>{s['stars_earned']}</b>"
    )


@router.callback_query(F.data == "admin_stats_refresh")
async def refresh_stats(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Not admin", show_alert=True)
        return
    stats = await db.get_global_stats()
    await callback.message.edit_text(_format_stats(stats), reply_markup=admin_stats_kb())
    await callback.answer("✅ Refreshed")


@router.callback_query(F.data == "admin_top_users")
async def top_users_callback(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await _send_top_users(callback.message, db)


@router.message(Command("topusers"))
async def cmd_topusers(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    await _send_top_users(message, db)


async def _send_top_users(message: Message, db: Database):
    users = await db.get_top_users(10)
    if not users:
        await message.answer("No downloads yet.")
        return

    lines = ["👑 <b>Top 10 Users</b>\n"]
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, u in enumerate(users):
        name = u.get("full_name") or u.get("username") or str(u["user_id"])
        plan = "💎" if u.get("plan") == "pro" else "🆓"
        lines.append(f"{medals[i]} {plan} <b>{name}</b> — {u['total_downloads']} downloads")
    await message.answer("\n".join(lines))


# ─── User control ──────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /ban [user_id]")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return

    await db.ban_user(target_id)
    await message.answer(f"🚫 User <code>{target_id}</code> has been banned.")


@router.message(Command("unban"))
async def cmd_unban(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /unban [user_id]")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return

    await db.unban_user(target_id)
    await message.answer(f"✅ User <code>{target_id}</code> has been unbanned.")


# ─── Premium control ───────────────────────────────────

@router.message(Command("premium"))
async def cmd_premium(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /premium [user_id] [days]")
        return
    try:
        target_id = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await message.answer("❌ Invalid arguments")
        return

    expiry = await db.set_premium(target_id, days)
    await message.answer(
        f"💎 Premium granted to <code>{target_id}</code>\n"
        f"📅 Expires: <code>{expiry.strftime('%Y-%m-%d')}</code>\n"
        f"⏳ Duration: <b>{days} days</b>"
    )


@router.message(Command("rpremium"))
async def cmd_rpremium(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /rpremium [user_id]")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return

    user = await db.get_user(target_id)
    if user and user.get("paid"):
        await message.answer(
            f"⚠️ User <code>{target_id}</code> has a <b>paid</b> subscription.\n"
            f"Use /rpremium_force {target_id} to override."
        )
        return

    await db.remove_premium(target_id)
    await message.answer(f"❌ Premium removed from <code>{target_id}</code>.")


@router.message(Command("premiumall"))
async def cmd_premiumall(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /premiumall [days]")
        return
    try:
        days = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid days")
        return

    await db.set_premium_all(days)
    await message.answer(f"💎 Premium granted to <b>ALL users</b> for <b>{days} days</b>.")


@router.message(Command("rpremiumall"))
async def cmd_rpremiumall(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    # Safety confirmation
    await state.set_data({"action": "rpremiumall"})
    await message.answer(
        "⚠️ <b>Danger!</b> This will remove premium from ALL non-paid users.\n"
        "Users who purchased via Stars will NOT be affected.\n\n"
        "Are you sure?",
        reply_markup=confirm_kb("rpremiumall", "all")
    )


@router.callback_query(F.data.startswith("confirm:rpremiumall:"))
async def confirm_rpremiumall(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("Not admin", show_alert=True)
        return
    await db.remove_premium_all(skip_paid=True)
    await callback.message.edit_text("✅ Premium removed from all non-paid users.")
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery):
    await callback.message.edit_text("❌ Action cancelled.")
    await callback.answer()


# ─── Price control ─────────────────────────────────────

@router.message(Command("setprice"))
async def cmd_setprice(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        current = await db.get_price()
        await message.answer(f"Current price: <b>{current} ⭐</b>\nUsage: /setprice [stars]")
        return
    try:
        stars = int(parts[1])
        if stars < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Invalid amount. Must be a positive integer.")
        return

    await db.set_price(stars)
    await message.answer(f"✅ Pro price updated to <b>{stars} ⭐ Stars</b>.")


# ─── Broadcast ─────────────────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(BroadcastState.waiting_content)
    await message.answer(
        "📢 <b>Broadcast Mode</b>\n\n"
        "Send the message you want to broadcast.\n"
        "Supports: text, photo, video, document.\n\n"
        "Send /cancel to stop."
    )


@router.message(Command("cancel"), BroadcastState.waiting_content)
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Broadcast cancelled.")


@router.message(BroadcastState.waiting_content)
async def handle_broadcast_content(message: Message, state: FSMContext, db: Database, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    user_ids = await db.get_all_user_ids()
    total = len(user_ids)

    status = await message.answer(f"📤 Broadcasting to <b>{total}</b> users…")

    sent = 0
    failed = 0

    for uid in user_ids:
        try:
            if message.content_type == ContentType.TEXT:
                await bot.send_message(uid, message.text or message.caption or "")
            elif message.content_type == ContentType.PHOTO:
                await bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == ContentType.VIDEO:
                await bot.send_video(uid, message.video.file_id, caption=message.caption)
            elif message.content_type == ContentType.DOCUMENT:
                await bot.send_document(uid, message.document.file_id, caption=message.caption)
            else:
                await bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # Avoid flood

    await status.edit_text(
        f"✅ <b>Broadcast complete</b>\n\n"
        f"📤 Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"👥 Total: <b>{total}</b>"
    )
