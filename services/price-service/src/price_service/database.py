"""
database.py — Async SQLAlchemy engine and session factory.

Three things are defined here:

1. Base       — The declarative base class. Every SQLAlchemy model you write
                must inherit from this. Alembic inspects Base.metadata to
                know which tables exist and generate migrations.

2. engine     — The async engine. It manages the connection pool to Postgres.
                There is one engine per process, created at startup.

3. get_db()   — A FastAPI dependency that yields a database session per
                request and guarantees the session is closed afterwards,
                even if the handler raises an exception.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from price_service.config import settings

# create_async_engine is the async equivalent of create_engine.
# echo=True logs every SQL statement — useful during development,
# should be False in production (controlled via config later).
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "dev",
)

# async_sessionmaker is the async equivalent of sessionmaker.
# expire_on_commit=False means SQLAlchemy won't expire ORM attributes after
# a commit — important for async code where re-fetching would require an
# extra await that's easy to forget.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Inherit from this in every model file:
        class Product(Base):
            __tablename__ = "products"
            ...
    """


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a database session for the duration of a request.

    Usage in a router:
        @router.get("/prices")
        async def list_prices(db: AsyncSession = Depends(get_db)):
            ...

    The `async with` block ensures the session is always closed, and rolls
    back any uncommitted transaction if an exception propagates out.
    """
    async with AsyncSessionLocal() as session:
        yield session
