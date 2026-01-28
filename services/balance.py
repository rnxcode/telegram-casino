from __future__ import annotations

from decimal import Decimal

from database.db import db


async def get_balance(user_id: int) -> float:
    """Legacy helper (returns float for UI)."""
    return float(await db.get_balance(user_id))


async def change_balance(
    user_id: int,
    amount: float,
    balance_type: str = "balance",
    *,
    tx_type: str | None = None,
    method: str | None = "system",
    meta: dict | str | None = None,
) -> bool:
    """Change user balance safely.

    - Prevents SQL injection by not interpolating column names.
    - Uses atomic ledger update for the main balance.

    Note: only "balance" is supported as a real money balance.
    """

    if balance_type != "balance":
        # If you later add "bonus" operations, implement a separate atomic method in DB.
        raise ValueError("Only 'balance' is supported for change_balance")

    delta = Decimal(str(amount))
    await db.change_balance_atomic(
        user_id,
        delta,
        tx_type=tx_type or balance_type,
        method=method,
        meta=meta,
    )
    return True
