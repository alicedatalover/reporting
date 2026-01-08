# app/utils/idempotency.py
"""
Utilitaires pour garantir l'idempotence des tâches.

Empêche l'exécution multiple de la même tâche via Redis locks.
"""

import hashlib
import logging
from typing import Optional, Callable, Any
from datetime import timedelta
import functools

logger = logging.getLogger(__name__)


def generate_idempotency_key(*args, **kwargs) -> str:
    """
    Génère une clé d'idempotence unique basée sur les arguments.

    Args:
        *args: Arguments positionnels
        **kwargs: Arguments nommés

    Returns:
        Clé MD5 hash unique

    Example:
        >>> generate_idempotency_key("company_123", "monthly", "2024-01-31")
        "abc123def456..."
    """
    # Convertir les args en string
    args_str = ":".join(str(arg) for arg in args)
    kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

    # Combiner
    combined = f"{args_str}:{kwargs_str}"

    # Hasher
    return hashlib.md5(combined.encode()).hexdigest()


class IdempotencyManager:
    """
    Gestionnaire d'idempotence utilisant Redis.

    Garantit qu'une tâche avec les mêmes paramètres ne s'exécute pas plusieurs fois
    dans une fenêtre de temps donnée.
    """

    def __init__(self, redis_client, prefix: str = "idempotency"):
        """
        Initialise le manager.

        Args:
            redis_client: Client Redis (redis.Redis ou redis.asyncio.Redis)
            prefix: Préfixe pour les clés Redis
        """
        self.redis = redis_client
        self.prefix = prefix

    def _make_key(self, task_name: str, idempotency_key: str) -> str:
        """
        Construit la clé Redis complète.

        Args:
            task_name: Nom de la tâche
            idempotency_key: Clé d'idempotence

        Returns:
            Clé Redis
        """
        return f"{self.prefix}:{task_name}:{idempotency_key}"

    async def is_duplicate(
        self,
        task_name: str,
        idempotency_key: str,
        ttl_seconds: int = 3600
    ) -> bool:
        """
        Vérifie si cette tâche a déjà été exécutée récemment.

        Args:
            task_name: Nom de la tâche
            idempotency_key: Clé d'idempotence unique
            ttl_seconds: Durée de vie du lock en secondes (défaut: 1h)

        Returns:
            True si la tâche est un duplicata, False sinon
        """
        key = self._make_key(task_name, idempotency_key)

        try:
            # SET NX (set if not exists) avec expiration
            # Retourne True si la clé n'existait pas (première exécution)
            # Retourne False si la clé existe déjà (duplicata)
            is_new = await self.redis.set(key, "1", ex=ttl_seconds, nx=True)

            if is_new:
                logger.debug(
                    f"Idempotency key created",
                    extra={
                        "task": task_name,
                        "key": idempotency_key,
                        "ttl": ttl_seconds
                    }
                )
                return False  # Pas un duplicata
            else:
                logger.warning(
                    f"Duplicate task detected",
                    extra={
                        "task": task_name,
                        "key": idempotency_key
                    }
                )
                return True  # Duplicata détecté

        except Exception as e:
            logger.error(
                f"Failed to check idempotency",
                extra={
                    "task": task_name,
                    "error": str(e)
                },
                exc_info=True
            )
            # En cas d'erreur Redis, on laisse passer pour ne pas bloquer
            return False

    async def mark_completed(
        self,
        task_name: str,
        idempotency_key: str,
        ttl_seconds: int = 86400
    ) -> None:
        """
        Marque une tâche comme complétée.

        Stocke le résultat dans Redis pour éviter les ré-exécutions.

        Args:
            task_name: Nom de la tâche
            idempotency_key: Clé d'idempotence
            ttl_seconds: Durée de vie (défaut: 24h)
        """
        key = self._make_key(task_name, idempotency_key)

        try:
            await self.redis.set(key, "completed", ex=ttl_seconds)

            logger.info(
                f"Task marked as completed",
                extra={
                    "task": task_name,
                    "key": idempotency_key,
                    "ttl": ttl_seconds
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to mark task as completed",
                extra={
                    "task": task_name,
                    "error": str(e)
                },
                exc_info=True
            )

    async def clear(self, task_name: str, idempotency_key: str) -> None:
        """
        Supprime une clé d'idempotence (pour forcer ré-exécution).

        Args:
            task_name: Nom de la tâche
            idempotency_key: Clé d'idempotence
        """
        key = self._make_key(task_name, idempotency_key)

        try:
            await self.redis.delete(key)

            logger.info(
                f"Idempotency key cleared",
                extra={
                    "task": task_name,
                    "key": idempotency_key
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to clear idempotency key",
                extra={
                    "task": task_name,
                    "error": str(e)
                },
                exc_info=True
            )


def idempotent_task(
    redis_client,
    task_name: str,
    ttl_seconds: int = 3600,
    key_func: Optional[Callable[..., str]] = None
):
    """
    Décorateur pour rendre une tâche idempotente.

    Args:
        redis_client: Client Redis
        task_name: Nom de la tâche (pour les logs)
        ttl_seconds: Durée de validité de l'idempotence (défaut: 1h)
        key_func: Fonction personnalisée pour générer la clé (défaut: hash des args)

    Returns:
        Décorateur

    Example:
        @idempotent_task(redis_client, "generate_report", ttl_seconds=3600)
        async def generate_report(company_id, frequency, end_date):
            # Cette fonction ne s'exécutera qu'une fois par combinaison d'arguments
            # dans une fenêtre de 1 heure
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            manager = IdempotencyManager(redis_client)

            # Générer la clé d'idempotence
            if key_func:
                idempotency_key = key_func(*args, **kwargs)
            else:
                idempotency_key = generate_idempotency_key(*args, **kwargs)

            # Vérifier si c'est un duplicata
            is_dup = await manager.is_duplicate(task_name, idempotency_key, ttl_seconds)

            if is_dup:
                logger.warning(
                    f"Skipping duplicate task execution",
                    extra={
                        "task": task_name,
                        "idempotency_key": idempotency_key
                    }
                )
                return {"status": "skipped", "reason": "duplicate"}

            # Exécuter la fonction
            result = await func(*args, **kwargs)

            # Marquer comme complété
            await manager.mark_completed(task_name, idempotency_key, ttl_seconds * 24)

            return result

        return wrapper
    return decorator


class SyncIdempotencyManager:
    """
    Gestionnaire d'idempotence synchrone utilisant Redis.

    Version synchrone pour les tâches Celery et autres contextes non-async.
    """

    def __init__(self, redis_client, prefix: str = "idempotency"):
        """
        Initialise le manager.

        Args:
            redis_client: Client Redis synchrone (redis.Redis)
            prefix: Préfixe pour les clés Redis
        """
        self.redis = redis_client
        self.prefix = prefix

    def _make_key(self, task_name: str, idempotency_key: str) -> str:
        """
        Construit la clé Redis complète.

        Args:
            task_name: Nom de la tâche
            idempotency_key: Clé d'idempotence

        Returns:
            Clé Redis
        """
        return f"{self.prefix}:{task_name}:{idempotency_key}"

    def is_duplicate(
        self,
        task_name: str,
        idempotency_key: str,
        ttl_seconds: int = 3600
    ) -> bool:
        """
        Vérifie si cette tâche a déjà été exécutée récemment (synchrone).

        Args:
            task_name: Nom de la tâche
            idempotency_key: Clé d'idempotence unique
            ttl_seconds: Durée de vie du lock en secondes (défaut: 1h)

        Returns:
            True si la tâche est un duplicata, False sinon
        """
        key = self._make_key(task_name, idempotency_key)

        try:
            # SET NX (set if not exists) avec expiration
            is_new = self.redis.set(key, "1", ex=ttl_seconds, nx=True)

            if is_new:
                logger.debug(
                    f"Idempotency key created (sync)",
                    extra={
                        "task": task_name,
                        "key": idempotency_key,
                        "ttl": ttl_seconds
                    }
                )
                return False  # Pas un duplicata
            else:
                logger.warning(
                    f"Duplicate task detected (sync)",
                    extra={
                        "task": task_name,
                        "key": idempotency_key
                    }
                )
                return True  # Duplicata détecté

        except Exception as e:
            logger.error(
                f"Failed to check idempotency (sync)",
                extra={
                    "task": task_name,
                    "error": str(e)
                },
                exc_info=True
            )
            # En cas d'erreur Redis, on laisse passer pour ne pas bloquer
            return False

    def mark_completed(
        self,
        task_name: str,
        idempotency_key: str,
        ttl_seconds: int = 86400
    ) -> None:
        """
        Marque une tâche comme complétée (synchrone).

        Args:
            task_name: Nom de la tâche
            idempotency_key: Clé d'idempotence
            ttl_seconds: Durée de vie (défaut: 24h)
        """
        key = self._make_key(task_name, idempotency_key)

        try:
            self.redis.set(key, "completed", ex=ttl_seconds)

            logger.info(
                f"Task marked as completed (sync)",
                extra={
                    "task": task_name,
                    "key": idempotency_key,
                    "ttl": ttl_seconds
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to mark task as completed (sync)",
                extra={
                    "task": task_name,
                    "error": str(e)
                },
                exc_info=True
            )
