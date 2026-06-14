import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

logger = logging.getLogger("app.database")

# Create asynchronous SQLAlchemy engine connecting to PostgreSQL
# pool_pre_ping=True verifies connections before execution, avoiding stale socket errors.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Async session factory
async_session_maker = async_sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an active async database session.
    Automatically handles rollback on exceptions and transaction closures.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.warning(f"Database transaction exception occurred; executing rollback: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def verify_connection() -> bool:
    """
    Performs a lightweight 'SELECT 1' test query.
    Returns True if connection succeeds, False otherwise.
    """
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.critical(f"Database connection check failed: {e}")
        return False
