from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Sequence

import aiosqlite

logger = logging.getLogger(__name__)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BalanceChange:
    before: Decimal
    after: Decimal


class DB:
    """SQLite access layer.

    Key guarantees:
    - No silent failures (exceptions bubble up with context).
    - Atomic balance changes (UPDATE + transaction log in one transaction).
    - Idempotency-friendly payment tables (unique external_id).
    """

    def __init__(self, path: str = "database/casino.db"):
        self.path = path
        self.db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL;")
        await self.db.execute("PRAGMA synchronous=NORMAL;")
        await self.db.execute("PRAGMA foreign_keys=ON;")
        await self.db.execute("PRAGMA busy_timeout=5000;")
        await self.create_tables()

    async def close(self) -> None:
        if self.db is not None:
            await self.db.close()
            self.db = None

    def _conn(self) -> aiosqlite.Connection:
        if self.db is None:
            raise RuntimeError("Database is not connected")
        return self.db

    @asynccontextmanager
    async def transaction(self):
        conn = self._conn()
        try:
            await conn.execute("BEGIN")
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    async def create_tables(self) -> None:
        conn = self._conn()
        await conn.executescript(
            """
-- USERS
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    bonus REAL DEFAULT 0,
    lang TEXT DEFAULT 'ru',

    refs_total INTEGER DEFAULT 0,
    refs_earned REAL DEFAULT 0,
    referred_by INTEGER,

    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    games_lost INTEGER DEFAULT 0,

    rr_played INTEGER DEFAULT 0,
    rr_won INTEGER DEFAULT 0,
    rr_lost INTEGER DEFAULT 0,

    dice_played INTEGER DEFAULT 0,
    dice_won INTEGER DEFAULT 0,
    dice_lost INTEGER DEFAULT 0,

    bj_played INTEGER DEFAULT 0,
    bj_won INTEGER DEFAULT 0,
    bj_lost INTEGER DEFAULT 0,

    mines_played INTEGER DEFAULT 0,
    mines_won INTEGER DEFAULT 0,
    mines_lost INTEGER DEFAULT 0,

    roulette_played INTEGER DEFAULT 0,
    roulette_won INTEGER DEFAULT 0,
    roulette_lost INTEGER DEFAULT 0,

    profit_won REAL DEFAULT 0,
    profit_lost REAL DEFAULT 0,

    created_at TEXT,
    updated_at TEXT
);

-- TRANSACTIONS (ledger)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    method TEXT,
    before REAL,
    after REAL,
    meta TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);

-- PENDING PAYMENTS (idempotency)
CREATE TABLE IF NOT EXISTS pending_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    amount REAL NOT NULL,
    external_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    UNIQUE(method, external_id)
);

CREATE INDEX IF NOT EXISTS idx_pending_payments_user ON pending_payments(user_id);

-- WITHDRAWALS
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    wallet TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    processed_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id);

-- REFERRALS
CREATE TABLE IF NOT EXISTS referrals (
    user_id INTEGER PRIMARY KEY,
    referred_by INTEGER,
    created_at TEXT
);

-- GAMES
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    game_type TEXT,
    bet REAL,
    result REAL,
    stage TEXT,
    created_at TEXT
);

-- DUELS
CREATE TABLE IF NOT EXISTS duels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL,
    opponent_id INTEGER,
    bet REAL NOT NULL,
    pot REAL NOT NULL,
    game TEXT DEFAULT 'dice',
    status TEXT NOT NULL,
    winner_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_duels_status ON duels(status);

-- RAFFLES
CREATE TABLE IF NOT EXISTS raffles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL,
    entry_amount REAL NOT NULL,
    pot REAL NOT NULL,
    status TEXT NOT NULL,
    winner_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raffle_participants (
    raffle_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TEXT NOT NULL,
    UNIQUE(raffle_id, user_id),
    FOREIGN KEY(raffle_id) REFERENCES raffles(id),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_raffles_status ON raffles(status);

-- SETTINGS (key-value)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""
        )
        # Backward-compatible schema bumps
        try:
            await conn.execute("ALTER TABLE duels ADD COLUMN game TEXT DEFAULT 'dice';")
        except Exception:
            pass
        try:
            await conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);")
        except Exception:
            pass
        await conn.commit()

    # ------------------------
    # low-level helpers
    # ------------------------
    async def execute(self, query: str, params: Sequence[Any] = ()) -> None:
        conn = self._conn()
        try:
            await conn.execute(query, params)
            await conn.commit()
        except Exception as e:
            logger.exception("DB.execute failed: %s | %s", e, query)
            raise

    async def execute_returning_id(self, query: str, params: Sequence[Any] = ()) -> int:
        conn = self._conn()
        try:
            cur = await conn.execute(query, params)
            await conn.commit()
            return int(cur.lastrowid)
        except Exception as e:
            logger.exception("DB.execute_returning_id failed: %s | %s", e, query)
            raise

    async def fetchone(self, query: str, params: Sequence[Any] = ()) -> aiosqlite.Row | None:
        conn = self._conn()
        cur = await conn.execute(query, params)
        return await cur.fetchone()

    async def fetchall(self, query: str, params: Sequence[Any] = ()) -> list[aiosqlite.Row]:
        conn = self._conn()
        cur = await conn.execute(query, params)
        return await cur.fetchall()

    # ------------------------
    # user APIs
    # ------------------------
    async def ensure_user(self, user_id: int, referred_by: int | None = None) -> None:
        now = _utc()
        conn = self._conn()
        await conn.execute(
            "INSERT OR IGNORE INTO users (user_id, created_at, updated_at) VALUES (?, ?, ?)",
            (user_id, now, now),
        )
        if referred_by:
            await conn.execute(
                "INSERT OR IGNORE INTO referrals (user_id, referred_by, created_at) VALUES (?, ?, ?)",
                (user_id, referred_by, now),
            )
            await conn.execute(
                "UPDATE users SET referred_by = COALESCE(referred_by, ?) WHERE user_id = ?",
                (referred_by, user_id),
            )
        await conn.commit()

    async def get_user_lang(self, user_id: int) -> str:
        row = await self.fetchone("SELECT lang FROM users WHERE user_id=?", (user_id,))
        return str(row[0]) if row and row[0] else "ru"

    async def set_user_lang(self, user_id: int, lang: str) -> None:
        await self.execute(
            "UPDATE users SET lang=?, updated_at=? WHERE user_id=?",
            (lang, _utc(), user_id),
        )

    async def get_balance(self, user_id: int) -> Decimal:
        row = await self.fetchone("SELECT balance FROM users WHERE user_id=?", (user_id,))
        return Decimal(str(row[0])) if row else Decimal("0")

    async def change_balance_atomic(
        self,
        user_id: int,
        delta: Decimal,
        *,
        tx_type: str,
        method: str | None = None,
        meta: dict[str, Any] | str | None = None,
        allow_negative: bool = False,
    ) -> BalanceChange:
        now = _utc()
        meta_str: str | None
        if isinstance(meta, dict):
            meta_str = json.dumps(meta, ensure_ascii=False)
        else:
            meta_str = meta

        async with self.transaction() as conn:
            cur = await conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            before = Decimal(str(row[0])) if row else Decimal("0")
            after = before + delta
            if (after < 0) and not allow_negative:
                raise ValueError("Insufficient balance")

            await conn.execute(
                "UPDATE users SET balance=?, updated_at=? WHERE user_id=?",
                (float(after), now, user_id),
            )
            await conn.execute(
                """
                INSERT INTO transactions (user_id, amount, type, method, before, after, meta, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, float(delta), tx_type, method, float(before), float(after), meta_str, now),
            )
            return BalanceChange(before=before, after=after)

    # ------------------------
    # duel APIs
    # ------------------------
    async def create_duel(self, creator_id: int, bet: Decimal, game: str) -> int:
        now = _utc()
        async with self.transaction() as conn:
            cur = await conn.execute(
                """
                INSERT INTO duels (creator_id, bet, pot, game, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'waiting', ?, ?)
                """,
                (creator_id, float(bet), float(bet), game, now, now),
            )
            return int(cur.lastrowid)

    async def get_duel(self, duel_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM duels WHERE id=?", (duel_id,))

    async def join_duel(self, duel_id: int, opponent_id: int) -> tuple[str, float]:
        """Returns (status, pot). status: joined | not_found | busy."""
        now = _utc()
        async with self.transaction() as conn:
            cur = await conn.execute(
                "SELECT bet, pot, status FROM duels WHERE id=?",
                (duel_id,),
            )
            row = await cur.fetchone()
            if not row:
                return "not_found", 0.0
            if row["status"] != "waiting":
                return "busy", float(row["pot"])

            new_pot = float(row["pot"]) + float(row["bet"])
            cur = await conn.execute(
                """
                UPDATE duels
                SET opponent_id=?, pot=?, status='active', updated_at=?
                WHERE id=? AND status='waiting'
                """,
                (opponent_id, new_pot, now, duel_id),
            )
            if cur.rowcount == 0:
                return "busy", float(row["pot"])
            return "joined", new_pot

    async def finish_duel(self, duel_id: int, winner_id: int) -> None:
        now = _utc()
        await self.execute(
            "UPDATE duels SET status='finished', winner_id=?, updated_at=? WHERE id=?",
            (winner_id, now, duel_id),
        )

    async def cancel_duel(self, duel_id: int, user_id: int) -> float:
        """Cancel waiting duel. Returns bet to refund or 0 if nothing to do."""
        now = _utc()
        async with self.transaction() as conn:
            cur = await conn.execute(
                "SELECT bet, status FROM duels WHERE id=? AND creator_id=?",
                (duel_id, user_id),
            )
            row = await cur.fetchone()
            if not row or row["status"] != "waiting":
                return 0.0

            await conn.execute(
                "UPDATE duels SET status='cancelled', updated_at=? WHERE id=?",
                (now, duel_id),
            )
            return float(row["bet"])

    # ------------------------
    # raffle APIs
    # ------------------------
    async def create_raffle(self, creator_id: int, entry_amount: Decimal) -> int:
        now = _utc()
        async with self.transaction() as conn:
            cur = await conn.execute(
                """
                INSERT INTO raffles (creator_id, entry_amount, pot, status, created_at, updated_at)
                VALUES (?, ?, ?, 'open', ?, ?)
                """,
                (creator_id, float(entry_amount), float(entry_amount), now, now),
            )
            raffle_id = int(cur.lastrowid)
            await conn.execute(
                """
                INSERT OR IGNORE INTO raffle_participants (raffle_id, user_id, joined_at)
                VALUES (?, ?, ?)
                """,
                (raffle_id, creator_id, now),
            )
            return raffle_id

    async def get_raffle(self, raffle_id: int) -> aiosqlite.Row | None:
        return await self.fetchone(
            "SELECT * FROM raffles WHERE id=?",
            (raffle_id,),
        )

    async def add_raffle_participant(self, raffle_id: int, user_id: int) -> tuple[str, float]:
        """Return status: joined/closed/already/missing and current pot."""
        now = _utc()
        async with self.transaction() as conn:
            cur = await conn.execute(
                "SELECT entry_amount, pot, status FROM raffles WHERE id=?",
                (raffle_id,),
            )
            row = await cur.fetchone()
            if not row:
                return "missing", 0.0
            if row["status"] != "open":
                return "closed", float(row["pot"])

            cur_ins = await conn.execute(
                """
                INSERT OR IGNORE INTO raffle_participants (raffle_id, user_id, joined_at)
                VALUES (?, ?, ?)
                """,
                (raffle_id, user_id, now),
            )
            if cur_ins.rowcount == 0:
                return "already", float(row["pot"])

            new_pot = float(row["pot"]) + float(row["entry_amount"])
            await conn.execute(
                "UPDATE raffles SET pot=?, updated_at=? WHERE id=?",
                (new_pot, now, raffle_id),
            )
            return "joined", new_pot

    async def raffle_participants(self, raffle_id: int) -> list[int]:
        rows = await self.fetchall(
            "SELECT user_id FROM raffle_participants WHERE raffle_id=?",
            (raffle_id,),
        )
        return [int(r[0]) for r in rows]

    async def finish_raffle(self, raffle_id: int, winner_id: int) -> None:
        now = _utc()
        await self.execute(
            "UPDATE raffles SET status='closed', winner_id=?, updated_at=? WHERE id=?",
            (winner_id, now, raffle_id),
        )

    # ------------------------
    # settings APIs
    # ------------------------
    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )

    async def get_setting(self, key: str) -> str | None:
        row = await self.fetchone("SELECT value FROM settings WHERE key=?", (key,))
        return row[0] if row else None

    # ------------------------
    # payments APIs
    # ------------------------
    async def upsert_pending_payment(
        self,
        *,
        user_id: int,
        method: str,
        amount: Decimal,
        external_id: str,
        status: str = "pending",
    ) -> None:
        now = _utc()
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO pending_payments (user_id, method, amount, external_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(method, external_id) DO UPDATE SET
                    amount=excluded.amount,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (user_id, method, float(amount), external_id, status, now, now),
            )

    async def mark_pending_paid(self, *, method: str, external_id: str) -> bool:
        """Marks pending payment as paid. Returns True if state changed."""
        now = _utc()
        async with self.transaction() as conn:
            cur = await conn.execute(
                "SELECT status FROM pending_payments WHERE method=? AND external_id=?",
                (method, external_id),
            )
            row = await cur.fetchone()
            if not row:
                return False
            if row[0] == "paid":
                return False
            await conn.execute(
                "UPDATE pending_payments SET status='paid', updated_at=? WHERE method=? AND external_id=?",
                (now, method, external_id),
            )
            return True


db = DB()
