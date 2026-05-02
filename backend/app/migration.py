from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from loguru import logger


class MigrationManager:

    def __init__(self, engine: AsyncEngine):
        self.version = 0
        self.db_engine = engine

    async def migrate(self):
        await self._drop_rate_limit_logs_table()

    async def _drop_rate_limit_logs_table(self) -> None:
        """Remove the old database-backed rate limit table."""
        async with self.db_engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS rate_limit_logs"))
        logger.info("Old rate_limit_logs table removed")
