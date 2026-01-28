"""Project configuration.

Security notes:
- No secrets are hardcoded. Put tokens/keys in .env (or real env vars).
- All values are parsed into correct types.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal

from dotenv import load_dotenv


load_dotenv()


def _getenv(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v


def _require(name: str) -> str:
    v = _getenv(name)
    if not v:
        raise RuntimeError(
            f"Missing required env var: {name}. Add it to .env or the environment."
        )
    return v


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def _parse_int_list(raw: str | None, env_name: str) -> list[int]:
    if not raw:
        return []
    parts = re.split(r"[,\s]+", raw.strip())
    result: list[int] = []
    for part in parts:
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            raise RuntimeError(f"{env_name} must contain only integer IDs separated by comma or space")
    return result


@dataclass(frozen=True)
class Settings:
    # Telegram
    BOT_TOKEN: str
    ADMIN_ID: int
    ADMIN_IDS: list[int]
    DUEL_LOG_CHANNEL: int | None
    GAME_LOG_CHANNEL: int | None
    SUPPORT_URL: str | None

    # Subscription gate
    CHANNELS: list[str]

    # Payments
    CRYPTO_TOKEN: str | None
    ROCKET_API_KEY: str | None
    STARS_USD_RATE: Decimal

    # Defaults
    START_BALANCE: Decimal
    START_BONUS: Decimal

    # Links
    ROCKET_BOT: str
    CRYPTO_BOT: str


def load_settings() -> Settings:
    # Backward-compatible env names
    bot_token = _getenv("BOT_TOKEN") or _getenv("TOKEN")
    if not bot_token:
        bot_token = _require("BOT_TOKEN")  # raises

    crypto_token = _getenv("CRYPTO_TOKEN") or _getenv("CRYPTOBOT_TOKEN")

    admin_ids = _parse_int_list(_getenv("ADMIN_IDS"), "ADMIN_IDS")
    if not admin_ids:
        admin_ids = _parse_int_list(_getenv("ADMIN_ID"), "ADMIN_ID")
    if not admin_ids:
        raise RuntimeError("Provide at least one admin id via ADMIN_ID or ADMIN_IDS")

    # Keep backward-compatible single ADMIN_ID
    admin_id = admin_ids[0]

    duel_log_raw = _getenv("DUEL_LOG_CHANNEL", "-1003637771262")
    duel_log_channel: int | None
    if duel_log_raw:
        try:
            duel_log_channel = int(duel_log_raw)
        except ValueError:
            raise RuntimeError("DUEL_LOG_CHANNEL must be an integer chat id (e.g., -1001234567890)")
    else:
        duel_log_channel = None

    game_log_raw = _getenv("GAME_LOG_CHANNEL")
    game_log_channel: int | None
    if game_log_raw:
        try:
            game_log_channel = int(game_log_raw)
        except ValueError:
            raise RuntimeError("GAME_LOG_CHANNEL must be an integer chat id (e.g., -1001234567890)")
    else:
        game_log_channel = None

    support_url = _getenv("SUPPORT_URL")

    channels = _split_csv(_getenv("CHANNELS"))
    # Old style: CHANNELS could be stored as space-separated or json-like in env.
    if not channels:
        # Safe fallback: allow hardcoded list via env-less deployments.
        # Keep empty by default (no subscription wall).
        channels = []

    rocket_api_key = _getenv("ROCKET_API_KEY")

    stars_rate_raw = _getenv("STARS_USD_RATE", "0.01")
    try:
        stars_rate = Decimal(stars_rate_raw)
    except Exception:
        raise RuntimeError("STARS_USD_RATE must be a decimal number")

    start_balance = Decimal(_getenv("START_BALANCE", "0"))
    start_bonus = Decimal(_getenv("START_BONUS", "0"))

    return Settings(
        BOT_TOKEN=bot_token,
        ADMIN_ID=admin_id,
        ADMIN_IDS=admin_ids,
        DUEL_LOG_CHANNEL=duel_log_channel,
        GAME_LOG_CHANNEL=game_log_channel,
        SUPPORT_URL=support_url,
        CHANNELS=channels,
        CRYPTO_TOKEN=crypto_token,
        ROCKET_API_KEY=rocket_api_key,
        STARS_USD_RATE=stars_rate,
        START_BALANCE=start_balance,
        START_BONUS=start_bonus,
        ROCKET_BOT=_getenv("ROCKET_BOT", "https://t.me/rocket_bot") or "https://t.me/rocket_bot",
        CRYPTO_BOT=_getenv("CRYPTO_BOT", "https://t.me/CryptoBot") or "https://t.me/CryptoBot",
    )


settings = load_settings()

# Backward compatible names used throughout the project
TOKEN = settings.BOT_TOKEN
ADMIN_ID = settings.ADMIN_ID
ADMIN_IDS = settings.ADMIN_IDS
DUEL_LOG_CHANNEL = settings.DUEL_LOG_CHANNEL
GAME_LOG_CHANNEL = settings.GAME_LOG_CHANNEL
SUPPORT_URL = settings.SUPPORT_URL
CHANNELS = settings.CHANNELS
CRYPTO_TOKEN = settings.CRYPTO_TOKEN or ""
CRYPTOBOT_TOKEN = settings.CRYPTO_TOKEN or ""
ROCKET_API_KEY = settings.ROCKET_API_KEY or ""
START_BALANCE = float(settings.START_BALANCE)
START_BONUS = float(settings.START_BONUS)
ROCKET_BOT = settings.ROCKET_BOT
CRYPTO_BOT = settings.CRYPTO_BOT
