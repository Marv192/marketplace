import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase


DUMMY_DB_URL = 'postgresql+asyncpg://user:pass@localhost:5432/testdb'
DATABASE_URL = os.getenv("DATABASE_URL", DUMMY_DB_URL)
MIGRATION_DATABASE_URL = os.getenv("MIGRATION_DATABASE_URL", DUMMY_DB_URL)

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
engine_for_migrations = create_engine(MIGRATION_DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False, autocommit=False,
                                         autoflush=False, class_=AsyncSession)

async def get_async_session():
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
