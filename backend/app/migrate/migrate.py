from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.migrate import LATEST_DATA_MODEL_VERSION


class Migration:

    def __init__(self, current_version: int):
        self.latest_version = LATEST_DATA_MODEL_VERSION
        self.current_version = current_version

    async def run(self, session: AsyncSession) -> None:
        """Run all necessary migrations in sequence."""
        if self.current_version >= self.latest_version:
            logger.info("No migrations needed, current version {} is up to date", self.current_version)
            return
        await self.drop_rate_limit_logs_table(session)

    async def drop_rate_limit_logs_table(self, session: AsyncSession) -> None:
        """Remove the old database-backed rate limit table."""
        version = 1
        if version <= self.current_version:
            return
        await session.execute(text("DROP TABLE IF EXISTS rate_limit_logs"))
        logger.info("Old rate_limit_logs table removed")
        logger.info("Migration to version 1 completed")
