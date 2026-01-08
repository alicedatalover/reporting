# app/infrastructure/cache/redis_client.py
"""
Client Redis pour cache et idempotence.

Fournit une instance Redis partagée pour l'application.
"""

import redis.asyncio as redis
from typing import Optional
import logging
import asyncio
import threading

from app.config import settings

logger = logging.getLogger(__name__)

# Instance globale du client Redis
_redis_client: Optional[redis.Redis] = None
_redis_client_lock = asyncio.Lock()  # Lock pour éviter race condition

# Instance globale du client Redis sync (pour Celery)
_redis_client_sync: Optional[redis.Redis] = None
_redis_client_sync_lock = threading.Lock()  # Lock thread-safe pour sync


async def get_redis_client() -> redis.Redis:
    """
    Obtient ou crée le client Redis global (thread-safe).

    Utilise un double-check locking pattern pour éviter les race conditions
    lors de l'initialisation du client Redis partagé.

    Returns:
        Client Redis async

    Example:
        >>> redis_client = await get_redis_client()
        >>> await redis_client.set("key", "value")
    """
    global _redis_client

    # Premier check (sans lock pour performance)
    if _redis_client is not None:
        return _redis_client

    # Acquérir le lock pour initialisation
    async with _redis_client_lock:
        # Second check (avec lock) - un autre thread a pu créer le client
        if _redis_client is not None:
            return _redis_client

        logger.info(
            "Creating Redis client",
            extra={
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB
            }
        )

        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,  # Decode bytes to strings
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )

        # Tester la connexion
        try:
            await _redis_client.ping()
            logger.info("Redis client connected successfully")
        except Exception as e:
            logger.error(
                "Failed to connect to Redis",
                extra={"error": str(e)},
                exc_info=True
            )
            _redis_client = None
            raise

        return _redis_client


async def close_redis_client():
    """
    Ferme les clients Redis globaux (async et sync).

    À appeler lors de l'arrêt de l'application.
    """
    global _redis_client, _redis_client_sync

    if _redis_client:
        logger.info("Closing async Redis client")
        await _redis_client.close()
        _redis_client = None

    if _redis_client_sync:
        logger.info("Closing sync Redis client")
        _redis_client_sync.close()
        _redis_client_sync = None


def get_redis_client_sync():
    """
    Obtient ou crée le client Redis global en mode synchrone (thread-safe).

    Utilise un singleton avec double-check locking pour éviter de créer
    plusieurs clients Redis dans un environnement multi-thread (Celery).

    Returns:
        Client Redis sync

    Note:
        Utilise redis-py standard (non-async) pour compatibilité Celery
    """
    import redis as redis_sync
    global _redis_client_sync

    # Premier check (sans lock pour performance)
    if _redis_client_sync is not None:
        return _redis_client_sync

    # Acquérir le lock pour initialisation
    with _redis_client_sync_lock:
        # Second check (avec lock) - un autre thread a pu créer le client
        if _redis_client_sync is not None:
            return _redis_client_sync

        logger.info(
            "Creating sync Redis client",
            extra={
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB
            }
        )

        _redis_client_sync = redis_sync.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )

        # Tester la connexion
        try:
            _redis_client_sync.ping()
            logger.info("Sync Redis client connected successfully")
        except Exception as e:
            logger.error(
                "Failed to connect to Redis (sync)",
                extra={"error": str(e)},
                exc_info=True
            )
            _redis_client_sync = None
            raise

        return _redis_client_sync
