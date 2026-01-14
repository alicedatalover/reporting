# app/infrastructure/database/connection.py
"""
Gestion de la connexion à la base de données MySQL avec SQLAlchemy async.

Utilise aiomysql comme driver asynchrone.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool
from typing import AsyncGenerator
import logging

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Engine global (sera initialisé au démarrage)
engine: AsyncEngine = None
AsyncSessionLocal: async_sessionmaker = None


def create_engine() -> AsyncEngine:
    """
    Crée et configure le moteur SQLAlchemy async.
    
    Returns:
        Moteur SQLAlchemy configuré
    """
    database_url = settings.DATABASE_URL
    
    logger.info(
        "Creating database engine",
        extra={
            "host": settings.DB_HOST,
            "database": settings.DB_NAME,
            "environment": settings.ENVIRONMENT
        }
    )
    
    # Configuration du pool de connexions
    # Pool augmenté pour gérer workers multiples (API + Celery)
    pool_config = {
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": 20,  # Augmenté de 10 à 20
        "max_overflow": 10,  # Augmenté de 5 à 10 (max 30 connexions)
        "pool_pre_ping": True,  # Activé pour détecter les connexions mortes
        "pool_recycle": 1800,
        "pool_timeout": 30,
        "echo": settings.DEBUG,
        "future": True,
        # Désactiver SSL pour connexion MySQL locale (Docker -> Windows host)
        "connect_args": {"ssl": None}
    }

    new_engine = create_async_engine(
        database_url,
        **pool_config
    )
    
    return new_engine


def init_database():
    """
    Initialise la connexion à la base de données.
    
    Appelé au démarrage de l'application.
    """
    global engine, AsyncSessionLocal
    
    engine = create_engine()
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    logger.info("Database connection initialized")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dépendance FastAPI pour obtenir une session de base de données.
    
    Yields:
        Session SQLAlchemy async
    
    Example:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    if AsyncSessionLocal is None:
        init_database()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """
    Vérifie que la connexion à la base de données fonctionne.

    Returns:
        True si la connexion fonctionne, False sinon
    """
    from sqlalchemy import text

    try:
        if engine is None:
            init_database()

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(
            "Database connection check failed",
            extra={"error": str(e)},
            exc_info=True
        )
        return False


async def close_database_connection():
    """
    Ferme proprement toutes les connexions à la base de données.
    
    Appelé lors de l'arrêt de l'application.
    """
    global engine
    
    if engine is not None:
        logger.info("Closing database connections")
        await engine.dispose()
        engine = None