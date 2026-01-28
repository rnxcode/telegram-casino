from __future__ import annotations

import json
from typing import Iterable

from database.db import db
from config import (
    CHANNELS as DEFAULT_CHANNELS,
    ROCKET_BOT as DEFAULT_ROCKET_BOT,
    CRYPTO_BOT as DEFAULT_CRYPTO_BOT,
    DUEL_LOG_CHANNEL as DEFAULT_DUEL_LOG,
    GAME_LOG_CHANNEL as DEFAULT_GAME_LOG,
    SUPPORT_URL as DEFAULT_SUPPORT_URL,
)


async def get_channels() -> list[str]:
    raw = await db.get_setting("channels")
    if not raw:
        return DEFAULT_CHANNELS
    try:
        return json.loads(raw)
    except Exception:
        return DEFAULT_CHANNELS


async def set_channels(channels: Iterable[str]) -> None:
    cleaned = [c.strip() for c in channels if c and c.strip()]
    await db.set_setting("channels", json.dumps(cleaned, ensure_ascii=False))


async def get_requisite(name: str, default: str | None = None) -> str | None:
    mapping = {
        "rocket_bot": DEFAULT_ROCKET_BOT,
        "crypto_bot": DEFAULT_CRYPTO_BOT,
    }
    raw = await db.get_setting(name)
    if raw is not None:
        return raw
    if default is not None:
        return default
    return mapping.get(name)


async def set_requisite(name: str, value: str) -> None:
    await db.set_setting(name, value)


async def get_duel_log_channel() -> int | None:
    raw = await db.get_setting("duel_log_channel")
    if raw:
        try:
            return int(raw)
        except Exception:
            return DEFAULT_DUEL_LOG
    return DEFAULT_DUEL_LOG


async def set_duel_log_channel(chat_id: int | None) -> None:
    await db.set_setting("duel_log_channel", str(chat_id) if chat_id is not None else "")


async def get_support_url() -> str | None:
    raw = await db.get_setting("support_url")
    return raw if raw is not None else DEFAULT_SUPPORT_URL


async def set_support_url(value: str | None) -> None:
    await db.set_setting("support_url", value or "")


async def get_game_log_channel() -> int | None:
    raw = await db.get_setting("game_log_channel")
    if raw:
        try:
            return int(raw)
        except Exception:
            return DEFAULT_GAME_LOG
    return DEFAULT_GAME_LOG
