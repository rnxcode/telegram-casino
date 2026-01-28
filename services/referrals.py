from __future__ import annotations

from decimal import Decimal

from database.db import db


async def award_loss_commission(user_id: int, loss_amount: float) -> None:
    """Add 10% of player's loss to their referrer balance and stats."""
    if loss_amount <= 0:
        return

    row = await db.fetchone(
        "SELECT referred_by FROM users WHERE user_id=?",
        (user_id,),
    )
    if not row or not row[0]:
        return

    ref_id = int(row[0])
    bonus = Decimal(str(loss_amount)) * Decimal("0.10")

    try:
        await db.change_balance_atomic(
            ref_id,
            bonus,
            tx_type="referral_loss_bonus",
            method="system",
            meta={"source_user": user_id, "loss": float(loss_amount)},
        )
        await db.execute(
            "UPDATE users SET refs_earned = COALESCE(refs_earned,0) + ? WHERE user_id=?",
            (float(bonus), ref_id),
        )
    except Exception:
        # Failing referral bonus should not break the main flow
        return
