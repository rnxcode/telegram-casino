from decimal import Decimal, ROUND_DOWN
from database.db import db


async def process_stars_payment(user_id: int, stars_amount: int) -> float:
    """
    Автоматическая обработка оплаты звёздами
    Возвращает сумму в USD, которая будет зачислена
    """
    # Невыгодный курс: 0.005 вместо 0.01
    conversion_rate = Decimal('0.005')
    usd_amount = Decimal(str(stars_amount)) * conversion_rate
    usd_amount = usd_amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

    # Обновляем баланс
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (float(usd_amount), user_id)
    )

    # Записываем транзакцию
    await db.execute(
        "INSERT INTO transactions (user_id, amount, type, method) VALUES (?, ?, 'deposit', 'stars')",
        (user_id, float(usd_amount))
    )

    return float(usd_amount)