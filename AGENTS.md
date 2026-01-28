# Repository Guidelines

## Project Structure & Module Organization
- `main.py` wires the aiogram bot, middleware stack, and routers; it is the single entry point.
- `handlers/` holds routers grouped by domain (`start.py`, `menu.py`, `deposit.py`, `games/*`, `withdraw.py`, etc.); keep new handlers small and async-safe.
- `services/` contains business logic helpers; prefer adding cross-cutting helpers here instead of bloating handlers.
- `database/db.py` is the SQLite access layer; schema is created at startup with WAL mode enabled. Keep migrations compatible with existing `casino.db`.
- `keyboards/`, `locales/` (YAML translations), `states/`, and `middlewares/` support UI/UX, i18n, FSM, and guardrails.

## Setup, Build, and Run
- Use Python 3.11+ and an isolated env: `python -m venv .venv && source .venv/bin/activate`.
- Install deps (aiogram, aiosqlite, python-dotenv expected): `pip install -r requirements.txt` if present, otherwise `pip install aiogram aiosqlite python-dotenv`.
- Provide configuration via `.env` (see `config.py`): `BOT_TOKEN`, `ADMIN_ID`, optional `CHANNELS`, `CRYPTO_TOKEN`, `ROCKET_API_KEY`, `START_BALANCE`, `START_BONUS`.
- Run the bot locally: `python main.py`. The DB (`database/casino.db`) will initialize tables on first start.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep functions async/await-friendly and side-effect light.
- Prefer type hints and `dataclass`/`TypedDict` for structured data; log with context (`logger.exception` is already used in `database/db.py`).
- Router files: name routers `router` and register in `main.py` in execution order. New keyboards go in `keyboards/` with clear, snake_case filenames.
- Keep localization keys mirrored across `locales/en.yml` and `locales/ru.yml`; avoid hardcoded user-facing strings in code.

## Testing Guidelines
- No automated tests currently; add `tests/` with `pytest` for new logic (e.g., balance changes, subscription gating, referral math).
- Use in-memory SQLite for unit tests when possible; seed deterministic data and assert on transaction logs.
- Run `pytest` (or `pytest tests/path/test_file.py`) before shipping changes; target coverage for new modules even if legacy code is uncovered.

## Commit & Pull Request Guidelines
- Git history is not present here; default to concise, action-oriented commit messages (e.g., `feat: add blackjack payout audit` or `fix: handle missing channel config`).
- PRs should describe behavior changes, include screenshots/terminal logs for admin flows, and link any tracking task/issue.
- Call out DB schema changes and required env vars explicitly; include upgrade steps if migrations are needed.

## Security & Configuration Tips
- Never commit `.env` or database files with real data; use redacted examples in descriptions.
- Validate env vars through `config.py`; fail fast on missing `BOT_TOKEN`/`ADMIN_ID`.
- Protect admin-only handlers and payment flows; keep unique `external_id` guarantees intact when touching payments logic.
