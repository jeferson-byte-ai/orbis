"""Database session management"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as AsyncSessionMaker, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from backend.config import settings

# Create synchronous engine for regular operations
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,  # Disable SQL query logging (too verbose)
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=300,  # Recycle connections every 5 minutes (Neon idle timeout)
    pool_size=5,  # Connection pool size
    max_overflow=10  # Max overflow connections
)

# Create asynchronous engine for async operations
# Convert postgresql:// to postgresql+asyncpg:// for async support
async_database_url = settings.database_url
if async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif async_database_url.startswith("sqlite:///"):
    async_database_url = async_database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

async_engine = create_async_engine(
    async_database_url,
    echo=False,  # Disable SQL query logging (too verbose)
)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
