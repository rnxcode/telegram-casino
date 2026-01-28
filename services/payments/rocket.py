from __future__ import annotations

from decimal import Decimal

import httpx

from config import settings
from database.db import db

async def check_rocket_receipt(receipt: str) -> dict:
    """Validates a Rocket receipt.

    Returns a dict response from Rocket API.
    """
    if not settings.ROCKET_API_KEY:
        return {"valid": False, "error": "ROCKET_API_KEY not configured"}

    timeout = httpx.Timeout(10.0, read=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            "https://pay.rocket.online/api/check",
            json={"receipt": receipt},
            headers={"Authorization": f"Bearer {settings.ROCKET_API_KEY}"},
        )
        r.raise_for_status()
        return r.json()


async def process_rocket_payment(user_id: int, amount: float, *, receipt: str | None = None) -> None:
    await db.change_balance_atomic(
        user_id,
        Decimal(str(amount)),
        tx_type="deposit",
        method="rocket",
        meta=receipt,
    )
