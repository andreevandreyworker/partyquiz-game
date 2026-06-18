import random
import time

from sqlalchemy import text

from app.db import engine as _engine

_TTL = 60.0
_cache: dict[str, tuple[float, object]] = {}


def _fresh(key: str) -> object | None:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    return None


def _store(key: str, value: object) -> object:
    _cache[key] = (time.monotonic(), value)
    return value


async def get_categories() -> list[dict]:
    cached = _fresh("categories")
    if cached is not None:
        return cached
    async with _engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT id, ru, en, premium, icon, video "
                "FROM game_categories "
                "WHERE enabled = true ORDER BY sort, id"
            )
        )
        data = [
            {
                "id": r.id,
                "ru": r.ru,
                "en": r.en,
                "premium": bool(r.premium),
                "icon": r.icon,
                "video": str(r.video) if r.video else None,
            }
            for r in rows
        ]
    return _store("categories", data)


async def get_premium_ids() -> set[int]:
    cats = await get_categories()
    return {c["id"] for c in cats if c["premium"]}


async def get_bank() -> dict[int, list[str]]:
    cached = _fresh("bank")
    if cached is not None:
        return cached
    async with _engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT category_id, text FROM question_bank "
                "WHERE enabled = true"
            )
        )
        data: dict[int, list[str]] = {}
        for r in rows:
            data.setdefault(r.category_id, []).append(r.text)
    return _store("bank", data)


async def _config() -> dict[str, str]:
    cached = _fresh("config")
    if cached is not None:
        return cached
    async with _engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT key, value FROM app_config")
        )
        data = {r.key: r.value for r in rows}
    return _store("config", data)


async def get_int(key: str, default: int) -> int:
    raw = (await _config()).get(key)
    try:
        return int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


async def random_statement(categories: list[int]) -> str:
    bank = await get_bank()
    pool: list[str] = []
    for cat in categories:
        pool.extend(bank.get(cat, []))
    if not pool:
        pool = [s for items in bank.values() for s in items]
    return random.choice(pool)
