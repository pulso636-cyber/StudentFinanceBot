"""
Database connection setup для async SQLAlchemy
Stack: aiogram + FastAPI + PostgreSQL + SQLAlchemy + Redis

Использование:
    from database import get_db, init_db, close_db

    # Инициализация при старте приложения
    await init_db()

    # Использование в handlers/routes
    async with get_db() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
"""

import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text
from dotenv import load_dotenv

from models import Base

# Загрузка переменных окружения
load_dotenv()

# ==================== Configuration ====================

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/filkin_bot"
)

# Если используете отдельные параметры
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "filkin_bot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# Если DATABASE_URL не задан, собираем из компонентов
if DATABASE_URL == "postgresql+asyncpg://postgres:password@localhost:5432/filkin_bot":
    DATABASE_URL = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

# Pool settings
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


# ==================== Engine & Session ====================

# Async engine
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,  # Логирование SQL запросов
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    poolclass=AsyncAdaptedQueuePool,
    # Для продакшена можно включить:
    # pool_use_lifo=True,  # Last In First Out
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Не сбрасывать объекты после commit
    autoflush=False,  # Ручной контроль flush
    autocommit=False,  # Ручной контроль commit
)


# ==================== Database Functions ====================


async def init_db() -> None:
    """
    Инициализация базы данных

    ВНИМАНИЕ: НЕ создаёт таблицы (используйте migrations)!
    Только проверяет соединение.

    Для создания таблиц используйте: python migrate.py up
    """
    async with engine.begin() as conn:
        # Проверка соединения
        await conn.execute(text("SELECT 1"))
        print("Database connection established")

        # Если нужно создать таблицы (только для разработки!)
        # await conn.run_sync(Base.metadata.create_all)
        # print("✅ Database tables created")


async def close_db() -> None:
    """
    Закрытие соединений с БД
    Вызывать при shutdown приложения
    """
    await engine.dispose()
    print("[OK] Database connections closed")


async def create_tables() -> None:
    """
    Создание таблиц (только для разработки!)

    В продакшене используйте migrations: python migrate.py up
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Database tables created")


async def drop_tables() -> None:
    """
    Удаление всех таблиц (ОСТОРОЖНО!)
    Только для разработки!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("[WARNING] Database tables dropped")


# ==================== Dependency Injection ====================


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager для получения сессии БД

    Использование:
        async with get_db() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI

    Использование в FastAPI routes:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_session)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==================== Utility Functions ====================


async def health_check() -> dict:
    """
    Проверка здоровья БД для health check endpoints

    Returns:
        dict: {"status": "ok/error", "message": "..."}
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database is healthy"}
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


async def get_db_stats() -> dict:
    """
    Получить статистику connection pool

    Returns:
        dict: Статистика пула соединений
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow(),
    }


# ==================== Testing Helper ====================


async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Сессия для тестов (с автоматическим rollback)

    Использование в pytest:
        @pytest.fixture
        async def db():
            async for session in get_test_db():
                yield session
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ==================== Example Usage ====================

if __name__ == "__main__":
    import asyncio
    from sqlalchemy import select
    from models import User

    async def main():
        """Пример использования"""

        # 1. Инициализация
        await init_db()

        # 2. Получение всех пользователей
        async with get_db() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            print(f"Found {len(users)} users")

        # 3. Создание нового пользователя
        async with get_db() as session:
            new_user = User(
                telegram_id=123456789,
                username="test_user",
                first_name="Test",
                last_name="User",
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            print(f"Created user: {new_user}")

        # 4. Поиск пользователя по telegram_id
        async with get_db() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == 123456789)
            )
            user = result.scalar_one_or_none()
            print(f"Found user: {user}")

        # 5. Health check
        health = await health_check()
        print(f"Health check: {health}")

        # 6. Stats
        stats = await get_db_stats()
        print(f"Pool stats: {stats}")

        # 7. Закрытие
        await close_db()

    # Запуск
    asyncio.run(main())
