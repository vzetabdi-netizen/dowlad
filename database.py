import logging
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME, FREE_DAILY_LIMIT, PRO_DAILY_LIMIT

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def today_str() -> str:
    return utcnow().strftime("%Y-%m-%d")


class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        # Indexes
        await self.db.users.create_index("user_id", unique=True)
        await self.db.downloads.create_index("user_id")
        await self.db.downloads.create_index("created_at")
        logger.info("Connected to MongoDB")

    # ─── Users ─────────────────────────────────────────

    async def get_user(self, user_id: int) -> dict | None:
        return await self.db.users.find_one({"user_id": user_id})

    async def ensure_user(self, user_id: int, username: str = None, full_name: str = None) -> dict:
        user = await self.get_user(user_id)
        if not user:
            user = {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "plan": "free",
                "pro_expires": None,
                "is_banned": False,
                "joined_at": utcnow(),
                "daily_downloads": {},
                "total_downloads": 0,
                "total_success": 0,
                "total_failed": 0,
            }
            await self.db.users.insert_one(user)
        else:
            # Update name on each interaction
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"username": username, "full_name": full_name}}
            )
        return user

    async def is_banned(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return user.get("is_banned", False) if user else False

    async def ban_user(self, user_id: int):
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_banned": True}},
            upsert=True
        )

    async def unban_user(self, user_id: int):
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_banned": False}}
        )

    # ─── Premium ───────────────────────────────────────

    async def set_premium(self, user_id: int, days: int):
        user = await self.get_user(user_id)
        now = utcnow()

        # If already pro, extend from expiry; else from now
        current_expiry = user.get("pro_expires") if user else None
        if current_expiry and current_expiry > now:
            base = current_expiry
        else:
            base = now

        new_expiry = base + timedelta(days=days)
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"plan": "pro", "pro_expires": new_expiry}},
            upsert=True
        )
        return new_expiry

    async def remove_premium(self, user_id: int):
        """Only for manually assigned premium — does NOT affect paid users."""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"plan": "free", "pro_expires": None}}
        )

    async def set_premium_all(self, days: int, paid_only: bool = False):
        """Grant premium to all users. paid_only=True skips free accounts that never paid."""
        now = utcnow()
        new_expiry = now + timedelta(days=days)
        query = {}
        if paid_only:
            query["plan"] = {"$ne": "free"}
        await self.db.users.update_many(
            query,
            {"$set": {"plan": "pro", "pro_expires": new_expiry}}
        )

    async def remove_premium_all(self, skip_paid: bool = True):
        """
        Remove premium from all users.
        skip_paid=True → only removes manually-set premium,
        NOT users who paid via Telegram Stars.
        """
        query = {}
        if skip_paid:
            query["paid"] = {"$ne": True}
        await self.db.users.update_many(
            query,
            {"$set": {"plan": "free", "pro_expires": None}}
        )

    async def is_pro(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False
        if user.get("plan") == "pro":
            expiry = user.get("pro_expires")
            if expiry is None or expiry > utcnow():
                return True
            # Expired — downgrade
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"plan": "free"}}
            )
        return False

    # ─── Download limits ───────────────────────────────

    async def check_limit(self, user_id: int) -> tuple[bool, int, int]:
        """Returns (can_download, used_today, daily_limit)"""
        user = await self.get_user(user_id)
        if not user:
            return False, 0, FREE_DAILY_LIMIT

        pro = await self.is_pro(user_id)
        limit = PRO_DAILY_LIMIT if pro else FREE_DAILY_LIMIT
        if PRO_DAILY_LIMIT == 0 and pro:
            return True, 0, 0  # Unlimited

        today = today_str()
        used = user.get("daily_downloads", {}).get(today, 0)

        return used < limit, used, limit

    async def increment_download(self, user_id: int, success: bool):
        today = today_str()
        inc = {
            f"daily_downloads.{today}": 1,
            "total_downloads": 1,
        }
        if success:
            inc["total_success"] = 1
        else:
            inc["total_failed"] = 1
        await self.db.users.update_one({"user_id": user_id}, {"$inc": inc})

    # ─── Stats ─────────────────────────────────────────

    async def get_global_stats(self) -> dict:
        total_users = await self.db.users.count_documents({})
        pro_users = await self.db.users.count_documents({"plan": "pro"})
        banned_users = await self.db.users.count_documents({"is_banned": True})

        # Sum all downloads
        pipeline = [
            {"$group": {
                "_id": None,
                "total_dl": {"$sum": "$total_downloads"},
                "total_ok": {"$sum": "$total_success"},
                "total_fail": {"$sum": "$total_failed"},
            }}
        ]
        agg = await self.db.users.aggregate(pipeline).to_list(1)
        totals = agg[0] if agg else {"total_dl": 0, "total_ok": 0, "total_fail": 0}

        # Stars earned
        stars_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$stars_paid"}}}
        ]
        stars_agg = await self.db.payments.aggregate(stars_pipeline).to_list(1)
        stars = stars_agg[0]["total"] if stars_agg else 0

        return {
            "total_users": total_users,
            "pro_users": pro_users,
            "banned_users": banned_users,
            "total_downloads": totals["total_dl"],
            "total_success": totals["total_ok"],
            "total_failed": totals["total_fail"],
            "stars_earned": stars,
        }

    async def get_top_users(self, limit: int = 10) -> list[dict]:
        cursor = self.db.users.find(
            {"total_downloads": {"$gt": 0}},
            {"user_id": 1, "username": 1, "full_name": 1,
             "total_downloads": 1, "plan": 1}
        ).sort("total_downloads", -1).limit(limit)
        return await cursor.to_list(limit)

    async def get_all_user_ids(self) -> list[int]:
        cursor = self.db.users.find(
            {"is_banned": False},
            {"user_id": 1}
        )
        docs = await cursor.to_list(None)
        return [d["user_id"] for d in docs]

    # ─── Payments ──────────────────────────────────────

    async def record_payment(self, user_id: int, stars: int, days: int):
        await self.db.payments.insert_one({
            "user_id": user_id,
            "stars_paid": stars,
            "days_granted": days,
            "paid_at": utcnow(),
        })
        # Mark user as paid
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"paid": True}}
        )

    # ─── Price ─────────────────────────────────────────

    async def get_price(self) -> int:
        doc = await self.db.settings.find_one({"_id": "price"})
        from config import DEFAULT_PRO_PRICE_STARS
        return doc["value"] if doc else DEFAULT_PRO_PRICE_STARS

    async def set_price(self, stars: int):
        await self.db.settings.update_one(
            {"_id": "price"},
            {"$set": {"value": stars}},
            upsert=True
        )
