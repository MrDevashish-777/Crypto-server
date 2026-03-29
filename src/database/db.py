"""Database Connection and Session Management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from config.settings import settings
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Test connections before using
)

logger.info(f"Database URL: {settings.DATABASE_URL}")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    
    Usage in routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize database"""
    from scripts.init_db import init_database
    import asyncio
    
    # Run database initialization in thread pool
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, init_database)
    logger.info("Database initialized")


async def close_db():
    """Close database connection"""
    engine.dispose()
    logger.info("Database connection closed")


async def test_connection() -> bool:
    """Test database connectivity"""
    try:
        with engine.begin() as connection:
            connection.execute("SELECT 1")
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        return False
