from decimal import Decimal

from aiocryptopay import AioCryptoPay, Networks

from config import settings
from database.db import db


crypto = AioCryptoPay(token=settings.CRYPTO_TOKEN or "", network=Networks.MAIN_NET)


async def create_crypto_invoice(user_id: int, amount: float):
    # создаём инвойс
    invoice = await crypto.create_invoice(
        asset="USDT",
        amount=amount
    )

    invoice_id = str(invoice.invoice_id)

    # idempotency record
    await db.upsert_pending_payment(
        user_id=user_id,
        method="crypto",
        amount=Decimal(str(amount)),
        external_id=invoice_id,
        status="pending",
    )

    # возвращаем ссылку на оплату
    return invoice.bot_invoice_url, invoice_id


async def check_crypto_payment(invoice_id: str):
    invoices = await crypto.get_invoices(invoice_ids=[invoice_id])

    # aiocryptopay returns an object with .invoices
    if not invoices or not getattr(invoices, "invoices", None):
        return {"status": "not_found"}

    inv = invoices.invoices[0]

    return {
        "status": (inv.status or "").lower(),
        "amount": float(inv.amount),
        "currency": inv.asset,
        "invoice_id": str(inv.invoice_id),
        "pay_url": inv.bot_invoice_url,
    }

