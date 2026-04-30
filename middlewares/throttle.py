import asyncio
import time
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.5):
        self.rate_limit = rate_limit
        self._last_call: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id if event.from_user else None
        if user_id:
            now = time.time()
            last = self._last_call.get(user_id, 0)
            if now - last < self.rate_limit:
                return  # Drop silently
            self._last_call[user_id] = now
        return await handler(event, data)
