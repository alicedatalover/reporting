# app/utils/retry.py
"""
Utilitaires de retry avec backoff exponentiel.

Fournit des décorateurs pour réessayer automatiquement les appels échoués.
"""

import asyncio
import functools
import logging
from typing import Type, Tuple, Callable, Optional, Any
import random

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Décorateur pour retry automatique avec backoff exponentiel (async).

    Args:
        max_attempts: Nombre maximum de tentatives (défaut: 3)
        initial_delay: Délai initial en secondes (défaut: 1.0)
        max_delay: Délai maximum en secondes (défaut: 60.0)
        exponential_base: Base pour le calcul exponentiel (défaut: 2.0)
        jitter: Ajouter un jitter aléatoire pour éviter thundering herd (défaut: True)
        exceptions: Tuple d'exceptions à catcher (défaut: Exception)

    Returns:
        Décorateur

    Example:
        @async_retry(max_attempts=3, initial_delay=1.0)
        async def call_external_api():
            response = await httpx.get("https://api.example.com")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)

                    # Log success si ce n'est pas la première tentative
                    if attempt > 1:
                        logger.info(
                            f"Retry succeeded for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_attempts": max_attempts
                            }
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Si c'est la dernière tentative, on lève l'exception
                    if attempt == max_attempts:
                        logger.error(
                            f"All retry attempts failed for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "error": str(e)
                            },
                            exc_info=True
                        )
                        raise

                    # Calculer le délai avec backoff exponentiel
                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Ajouter jitter (±25% du délai)
                    if jitter:
                        jitter_range = delay * 0.25
                        delay = delay + random.uniform(-jitter_range, jitter_range)

                    logger.warning(
                        f"Retry attempt {attempt}/{max_attempts} for {func.__name__}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay_seconds": round(delay, 2),
                            "error": str(e)
                        }
                    )

                    # Attendre avant la prochaine tentative
                    await asyncio.sleep(delay)

            # Ne devrait jamais arriver ici, mais par sécurité
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def sync_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Décorateur pour retry automatique avec backoff exponentiel (sync).

    Args:
        max_attempts: Nombre maximum de tentatives (défaut: 3)
        initial_delay: Délai initial en secondes (défaut: 1.0)
        max_delay: Délai maximum en secondes (défaut: 60.0)
        exponential_base: Base pour le calcul exponentiel (défaut: 2.0)
        jitter: Ajouter un jitter aléatoire pour éviter thundering herd (défaut: True)
        exceptions: Tuple d'exceptions à catcher (défaut: Exception)

    Returns:
        Décorateur

    Example:
        @sync_retry(max_attempts=3, initial_delay=1.0)
        def call_external_api():
            response = requests.get("https://api.example.com")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import time
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)

                    # Log success si ce n'est pas la première tentative
                    if attempt > 1:
                        logger.info(
                            f"Retry succeeded for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_attempts": max_attempts
                            }
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Si c'est la dernière tentative, on lève l'exception
                    if attempt == max_attempts:
                        logger.error(
                            f"All retry attempts failed for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "error": str(e)
                            },
                            exc_info=True
                        )
                        raise

                    # Calculer le délai avec backoff exponentiel
                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Ajouter jitter (±25% du délai)
                    if jitter:
                        jitter_range = delay * 0.25
                        delay = delay + random.uniform(-jitter_range, jitter_range)

                    logger.warning(
                        f"Retry attempt {attempt}/{max_attempts} for {func.__name__}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay_seconds": round(delay, 2),
                            "error": str(e)
                        }
                    )

                    # Attendre avant la prochaine tentative
                    time.sleep(delay)

            # Ne devrait jamais arriver ici, mais par sécurité
            if last_exception:
                raise last_exception

        return wrapper
    return decorator
