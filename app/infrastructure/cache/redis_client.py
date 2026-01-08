# app/infrastructure/cache/redis_client.py
"""
Client Redis pour cache et idempotence.

Fournit une instance Redis partagée pour l'application.
"""

import redis.asyncio as redis
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Instance globale du client Redis
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Obtient ou crée le client Redis global.

    Returns:
        Client Redis async

    Example:
        >>> redis_client = await get_redis_client()
        >>> await redis_client.set("key", "value")
    """
    global _redis_client

    if _redis_client is None:
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
    Ferme le client Redis global.

    À appeler lors de l'arrêt de l'application.
    """
    global _redis_client

    if _redis_client:
        logger.info("Closing Redis client")
        await _redis_client.close()
        _redis_client = None


def get_redis_client_sync() -> redis.Redis:
    """
    Obtient le client Redis en mode synchrone (pour Celery workers).

    Returns:
        Client Redis sync

    Note:
        Utilise redis-py standard (non-async) pour compatibilité Celery
    """
    import redis as redis_sync

    logger.info(
        "Creating sync Redis client",
        extra={
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB
        }
    )

    client = redis_sync.Redis(
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
        client.ping()
        logger.info("Sync Redis client connected successfully")
    except Exception as e:
        logger.error(
            "Failed to connect to Redis (sync)",
            extra={"error": str(e)},
            exc_info=True
        )
        raise

    return client
