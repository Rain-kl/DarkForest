"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.rooms import router as rooms_router
from app.api.websocket import router as ws_router
from app.config import get_settings
from app.database import async_session_factory
from app.models.base import Base
from app.database import engine

settings = get_settings()


async def _init_admin() -> None:
    """Create the default admin user if no admin exists."""
    from sqlalchemy import select

    from app.models.user import User
    from app.services.auth import hash_password

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.role == "admin"))
        if result.scalar_one_or_none():
            return
        admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            nickname="Administrator",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        logger.info("Default admin user created: {}", settings.ADMIN_USERNAME)


async def _init_default_configs() -> None:
    """Seed default system configurations if they don't exist."""
    from sqlalchemy import select

    from app.models.system_config import SystemConfig

    defaults = {
        "room_timeout_minutes": {
            "value": str(settings.DEFAULT_ROOM_TIMEOUT_MINUTES),
            "description": "Room auto-destroy timeout in minutes of inactivity",
        },
        "message_retention_hours": {
            "value": str(settings.DEFAULT_MESSAGE_RETENTION_HOURS),
            "description": "Hours to retain messages after room destruction",
        },
        "max_rooms_per_hour": {
            "value": str(settings.DEFAULT_MAX_ROOMS_PER_HOUR),
            "description": "Max rooms an IP can create per hour",
        },
        "max_joins_per_hour": {
            "value": str(settings.DEFAULT_MAX_JOINS_PER_HOUR),
            "description": "Max rooms an IP can join per hour",
        },
        "max_messages_per_minute": {
            "value": str(settings.DEFAULT_MAX_MESSAGES_PER_MINUTE),
            "description": "Max messages an IP can send per minute",
        },
        "passcode_min_length": {
            "value": "4",
            "description": "Minimum length for room passcode",
        },
    }

    async with async_session_factory() as db:
        for key, config in defaults.items():
            result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
            if not result.scalar_one_or_none():
                db.add(
                    SystemConfig(
                        key=key,
                        value=config["value"],
                        description=config["description"],
                    )
                )
        await db.commit()
        logger.info("Default configs initialized")


async def _background_cleanup() -> None:
    """Background task that periodically cleans up inactive rooms."""
    from app.services.rate_limiter import cleanup_old_logs
    from app.services.room_service import cleanup_inactive_rooms, destroy_pending_rooms

    while True:
        try:
            async with async_session_factory() as db:
                inactive = await cleanup_inactive_rooms(db)
                destroyed = await destroy_pending_rooms(db)
                cleaned_logs = await cleanup_old_logs(db)
                await db.commit()
                if inactive or destroyed or cleaned_logs:
                    logger.info(
                        "Cleanup: {} inactive rooms, {} destroyed, {} old logs removed",
                        inactive,
                        destroyed,
                        cleaned_logs,
                    )
        except Exception as e:
            logger.error("Background cleanup error: {}", e)
        await asyncio.sleep(60)  # Run every 60 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    logger.info("Starting {} v{}", settings.APP_NAME, settings.APP_VERSION)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Initialize admin and configs
    await _init_admin()
    await _init_default_configs()

    # Start background cleanup task
    cleanup_task = asyncio.create_task(_background_cleanup())

    yield

    # Shutdown
    cleanup_task.cancel()
    logger.info("Shutting down {}...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api")
app.include_router(rooms_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(ws_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
