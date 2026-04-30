from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Download"), KeyboardButton(text="💎 My Plan")],
            [KeyboardButton(text="📊 My Stats"), KeyboardButton(text="🆙 Upgrade")],
            [KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Paste a video link or use the menu…"
    )


def upgrade_kb(price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐ Pay {price} Stars — Go Pro",
            callback_data=f"pay_stars:{price}"
        )],
        [InlineKeyboardButton(text="ℹ️ What is Pro?", callback_data="pro_info")],
    ])


def confirm_kb(action: str, target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, confirm", callback_data=f"confirm:{action}:{target}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel"),
        ]
    ])


def admin_stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_stats_refresh")],
        [InlineKeyboardButton(text="👑 Top Users", callback_data="admin_top_users")],
    ])
