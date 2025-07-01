"""
Файл настраивает подключение к базе данных и
предоставляет сессию для взаимодействия с базой данных.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

Base = declarative_base()
engine = create_async_engine(
    settings.DB_URL,
    echo=True  # Логирование SQL запросов для отладки
)

AsyncSessionLocal = sessionmaker(
        engine,
        class_= AsyncSession,
        expire_on_commit = False,
        autocommit = False,
        autoflush=  False)

async def get_db():
    """Генератор сессий для зависимостей"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()