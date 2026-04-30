import os
import logging
from aiogram import Router, F
from aiogram.types import Message, FSInputFile

from database import Database
from utils.downloader import download_video, extract_url, detect_platform, PLATFORM_EMOJI
from keyboards.kb import upgrade_kb

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "📥 Download")
async def prompt_download(message: Message):
    await message.answer("📎 Send me a video link and I'll download it for you!")


@router.message(F.text.regexp(r"https?://"))
async def handle_link(message: Message, db: Database):
    user_id = message.from_user.id
    await db.ensure_user(user_id, message.from_user.username, message.from_user.full_name)

    # Banned check
    if await db.is_banned(user_id):
        await message.answer("🚫 You are banned from using this bot.")
        return

    # Extract URL
    url = extract_url(message.text)
    if not url:
        await message.answer("❌ Couldn't extract a valid URL from your message.")
        return

    # Check platform
    platform = detect_platform(url)
    if not platform:
        await message.answer(
            "❌ <b>Unsupported link.</b>\n\n"
            "Supported: TikTok, YouTube, Instagram, Facebook, X/Twitter, Pinterest"
        )
        return

    # Check daily limit
    can_dl, used, limit = await db.check_limit(user_id)
    if not can_dl:
        price = await db.get_price()
        await message.answer(
            f"⛔ <b>Daily limit reached!</b>\n\n"
            f"You've used <b>{used}/{limit}</b> downloads today.\n"
            f"Upgrade to Pro for 100 downloads/day + HD quality!",
            reply_markup=upgrade_kb(price)
        )
        return

    is_pro = await db.is_pro(user_id)
    emoji = PLATFORM_EMOJI.get(platform, "🌐")
    plan_tag = "💎 HD" if is_pro else "🆓 SD"

    status_msg = await message.answer(
        f"{emoji} <b>Downloading...</b>\n"
        f"Platform: <b>{platform.capitalize()}</b> | {plan_tag}\n"
        f"⏳ Please wait…"
    )

    result = await download_video(url, is_pro=is_pro)
    success = result["success"]

    # Record stat
    await db.increment_download(user_id, success)

    if not success:
        await status_msg.edit_text(
            f"❌ <b>Download Failed</b>\n\n{result['error']}"
        )
        return

    filepath = result["path"]
    title = result["title"] or "video"

    try:
        await status_msg.edit_text(f"📤 Sending <b>{title[:60]}</b>…")
        video_file = FSInputFile(filepath)
        _, used_after, _ = await db.check_limit(user_id)
        remaining = max(0, limit - used_after)

        caption = (
            f"{emoji} <b>{title[:80]}</b>\n\n"
            f"📥 <i>Downloads today: {used_after}/{limit if limit else '∞'}</i>"
        )
        if not is_pro:
            caption += f"\n⚡ <i>Upgrade to Pro for HD + more quota</i>"

        await message.answer_video(
            video=video_file,
            caption=caption,
            supports_streaming=True,
        )
        await status_msg.delete()

    except Exception as e:
        logger.exception(f"Failed to send video: {e}")
        # Try sending as document as fallback
        try:
            await message.answer_document(
                document=FSInputFile(filepath),
                caption=f"{emoji} <b>{title[:80]}</b>"
            )
            await status_msg.delete()
        except Exception as e2:
            logger.exception(f"Document fallback also failed: {e2}")
            await status_msg.edit_text("❌ Failed to send the video. Please try again.")
    finally:
        # Cleanup temp file + its temp dir (best-effort)
        try:
            import shutil
            if filepath:
                tmpdir = os.path.dirname(filepath)
                if tmpdir and os.path.isdir(tmpdir):
                    shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
