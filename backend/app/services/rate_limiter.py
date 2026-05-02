"""IP-based in-memory rate limiting service."""

import asyncio
from collections import defaultdict, deque
from datetime import timedelta
from time import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig

# Default limits (used when no dynamic config exists)
DEFAULT_LIMITS: dict[str, int] = {
    "max_rooms_per_hour": 5,
    "max_joins_per_hour": 10,
    "max_messages_per_minute": 30,
}

_rate_limit_lock = asyncio.Lock()
_rate_limit_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


async def get_config_value(db: AsyncSession, key: str) -> int:
    """Fetch a dynamic config value, falling back to defaults."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if config:
        try:
            return int(config.value)
        except (ValueError, TypeError):
            pass
    return DEFAULT_LIMITS.get(key, 10)


async def check_rate_limit(
    db: AsyncSession,
    ip_address: str,
    action: str,
    config_key: str,
    window_hours: float = 1,
) -> tuple[bool, int]:
    """
    Check if an IP has exceeded the rate limit for an action.
    Returns (is_allowed, current_count).
    window_hours: use 1/60 for a 1-minute window, 1 for 1-hour window.
    """
    limit = await get_config_value(db, config_key)
    cutoff = time() - window_hours * 3600
    key = (ip_address, action)

    async with _rate_limit_lock:
        hits = _rate_limit_hits[key]
        while hits and hits[0] < cutoff:
            hits.popleft()
        count = len(hits)
        return count < limit, count


async def log_action(db: AsyncSession, ip_address: str, action: str) -> None:
    """Record an action in process memory for rate limiting."""
    _ = db
    async with _rate_limit_lock:
        _rate_limit_hits[(ip_address, action)].append(time())


async def cleanup_old_logs(db: AsyncSession, hours: int = 48) -> int:
    """Remove old in-memory rate limit entries."""
    _ = db
    cutoff = time() - timedelta(hours=hours).total_seconds()
    removed = 0

    async with _rate_limit_lock:
        empty_keys: list[tuple[str, str]] = []
        for key, hits in _rate_limit_hits.items():
            before = len(hits)
            while hits and hits[0] < cutoff:
                hits.popleft()
            removed += before - len(hits)
            if not hits:
                empty_keys.append(key)
        for key in empty_keys:
            del _rate_limit_hits[key]

    return removed
