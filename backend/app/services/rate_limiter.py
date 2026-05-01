"""IP-based rate limiting service using database logs."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_limit_log import RateLimitLog
from app.models.system_config import SystemConfig

# Default limits (used when no dynamic config exists)
DEFAULT_LIMITS: dict[str, int] = {
    "max_rooms_per_hour": 5,
    "max_joins_per_hour": 10,
    "max_messages_per_minute": 30,
}


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
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)

    result = await db.execute(
        select(func.count())
        .select_from(RateLimitLog)
        .where(
            RateLimitLog.ip_address == ip_address,
            RateLimitLog.action == action,
            RateLimitLog.created_at >= cutoff,
        )
    )
    count = result.scalar() or 0
    return count < limit, count


async def log_action(db: AsyncSession, ip_address: str, action: str) -> None:
    """Record an action for rate limiting."""
    entry = RateLimitLog(
        ip_address=ip_address,
        action=action,
        created_at=datetime.now(UTC),
    )
    db.add(entry)


async def cleanup_old_logs(db: AsyncSession, hours: int = 48) -> int:
    """Remove rate limit logs older than the given hours."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    result = await db.execute(delete(RateLimitLog).where(RateLimitLog.created_at < cutoff))
    return result.rowcount
