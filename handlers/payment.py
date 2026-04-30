import logging
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    PreCheckoutQuery, SuccessfulPayment, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command

from database import Database
from keyboards.kb import upgrade_kb

router = Router()
logger = logging.getLogger(__name__)

PRO_DAYS = 30  # days granted per payment


@router.message(Command("upgrade"))
@router.message(F.text == "🆙 Upgrade")
async def cmd_upgrade(message: Message, db: Database):
    user_id = message.from_user.id
    is_pro = await db.is_pro(user_id)

    if is_pro:
        user = await db.get_user(user_id)
        expiry = user.get("pro_expires")
        expiry_str = expiry.strftime("%Y-%m-%d") if expiry else "lifetime"
        await message.answer(
            f"✅ You already have <b>Pro</b> until <code>{expiry_str}</code>!\n\n"
            f"You can still pay again to extend by another {PRO_DAYS} days."
        )

    price = await db.get_price()
    text = (
        "💎 <b>Upgrade to Pro</b>\n\n"
        f"✅ <b>100 downloads/day</b> (vs 5 free)\n"
        f"✅ <b>HD quality</b> videos\n"
        f"✅ <b>Priority processing</b>\n"
        f"✅ Valid for <b>{PRO_DAYS} days</b>\n\n"
        f"💰 Price: <b>{price} ⭐ Telegram Stars</b>"
    )
    await message.answer(text, reply_markup=upgrade_kb(price))


@router.callback_query(F.data.startswith("pay_stars:"))
async def handle_pay_callback(callback: CallbackQuery, db: Database):
    price = int(callback.data.split(":")[1])
    await callback.answer()
    await send_invoice(callback.message, price)


async def send_invoice(message: Message, price: int):
    await message.answer_invoice(
        title="💎 Pro Plan — 30 Days",
        description=f"100 downloads/day · HD quality · {PRO_DAYS} days access",
        payload=f"pro_upgrade_{PRO_DAYS}d",
        currency="XTR",  # Telegram Stars currency
        prices=[LabeledPrice(label="Pro Plan", amount=price)],
    )


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Always approve
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, db: Database):
    payment: SuccessfulPayment = message.successful_payment
    user_id = message.from_user.id
    stars_paid = payment.total_amount

    new_expiry = await db.set_premium(user_id, PRO_DAYS)
    await db.record_payment(user_id, stars_paid, PRO_DAYS)

    expiry_str = new_expiry.strftime("%Y-%m-%d")
    await message.answer(
        f"🎉 <b>Payment successful!</b>\n\n"
        f"⭐ Stars paid: <b>{stars_paid}</b>\n"
        f"💎 Pro plan activated for <b>{PRO_DAYS} days</b>\n"
        f"📅 Expires: <code>{expiry_str}</code>\n\n"
        f"Enjoy your Pro features! 🚀"
    )
    logger.info(f"User {user_id} upgraded to Pro. Stars: {stars_paid}, Expires: {expiry_str}")


@router.callback_query(F.data == "pro_info")
async def pro_info(callback: CallbackQuery):
    await callback.answer(
        "Pro gives you 100 downloads/day, HD quality and priority speed!",
        show_alert=True
    )
