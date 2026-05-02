from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.migrate import LATEST_DATA_MODEL_VERSION
from app.migrate.migrate import Migration
from app.models.version import AppVersion



class MigrationManager:
    """Manage lightweight data migrations outside Alembic."""

    def __init__(self, engine: AsyncEngine, current_version: int):
        self.latest_version = LATEST_DATA_MODEL_VERSION
        self.current_version = current_version
        self.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    @classmethod
    async def create(cls, engine: AsyncEngine) -> "MigrationManager":
        """Initialize the manager by reading the current data model version."""
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            result = await session.execute(select(AppVersion).where(AppVersion.id == 1))
            app_version = result.scalar_one_or_none()
            if app_version is None:
                app_version = AppVersion(id=1, data_model_version=0)
                session.add(app_version)
                await session.commit()
                current_version = 0
            else:
                current_version = app_version.data_model_version

        logger.info("Current data model version: {}", current_version)
        return cls(engine, current_version)

    async def migrate(self):
        async with self.session_factory() as session:
            async with session.begin():
                await self._run_migrations(session)
                await self._update_data_model_version(session)

        self.current_version = self.latest_version

    async def _update_data_model_version(self, session: AsyncSession) -> None:
        """Update the singleton version row after migrations complete."""
        await session.execute(
            update(AppVersion)
            .where(AppVersion.id == 1)
            .values(data_model_version=self.latest_version)
        )

    async def _run_migrations(self, session: AsyncSession) -> None:
        await Migration(self.current_version).run(session)

