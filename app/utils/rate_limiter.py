# app/utils/rate_limiter.py
"""
Rate limiting pour les API endpoints.

Utilise Redis pour limiter le nombre de requêtes par IP/utilisateur
et prévenir les abus (DoS, brute force, etc.).
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import Request, HTTPException, status

from app.infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Limiteur de débit basé sur Redis.

    Utilise l'algorithme "sliding window" pour un contrôle précis.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration_seconds: int = 300  # 5 minutes
    ):
        """
        Initialise le rate limiter.

        Args:
            requests_per_minute: Limite par minute
            requests_per_hour: Limite par heure
            block_duration_seconds: Durée du blocage en cas de dépassement
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.block_duration_seconds = block_duration_seconds

    def _get_client_id(self, request: Request) -> str:
        """
        Extrait un identifiant unique du client (IP + User-Agent).

        Args:
            request: Requête FastAPI

        Returns:
            Hash unique du client
        """
        # Extraire l'IP réelle (supporte proxies/load balancers)
        client_ip = request.client.host if request.client else "unknown"

        # Vérifier les headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Prendre la première IP (client réel)
            client_ip = forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()

        # Combiner IP + User-Agent pour plus de précision
        user_agent = request.headers.get("User-Agent", "unknown")

        # Hash pour anonymisation
        client_data = f"{client_ip}:{user_agent}"
        client_hash = hashlib.sha256(client_data.encode()).hexdigest()[:16]

        return client_hash

    async def check_rate_limit(
        self,
        request: Request,
        endpoint: str,
        custom_limit: Optional[int] = None
    ) -> None:
        """
        Vérifie si le client dépasse les limites de débit.

        Args:
            request: Requête FastAPI
            endpoint: Nom de l'endpoint (pour logs et clés Redis)
            custom_limit: Limite personnalisée pour cet endpoint (optionnel)

        Raises:
            HTTPException 429 si limite dépassée
        """
        redis_client = await get_redis_client()
        client_id = self._get_client_id(request)

        # Clés Redis
        minute_key = f"ratelimit:{endpoint}:minute:{client_id}"
        hour_key = f"ratelimit:{endpoint}:hour:{client_id}"
        block_key = f"ratelimit:block:{client_id}"

        # Vérifier si le client est bloqué
        is_blocked = await redis_client.get(block_key)
        if is_blocked:
            logger.warning(
                "Blocked client attempted access",
                extra={
                    "client_id": client_id,
                    "endpoint": endpoint,
                    "ip": request.client.host if request.client else "unknown"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Blocked for {self.block_duration_seconds}s. Please try again later."
            )

        # Incrémenter les compteurs
        minute_count = await redis_client.incr(minute_key)
        hour_count = await redis_client.incr(hour_key)

        # Définir TTL si c'est la première requête
        if minute_count == 1:
            await redis_client.expire(minute_key, 60)  # 1 minute

        if hour_count == 1:
            await redis_client.expire(hour_key, 3600)  # 1 heure

        # Vérifier les limites
        limit_per_minute = custom_limit if custom_limit else self.requests_per_minute

        if minute_count > limit_per_minute:
            # Bloquer le client temporairement
            await redis_client.setex(
                block_key,
                self.block_duration_seconds,
                "blocked"
            )

            logger.warning(
                "Rate limit exceeded - client blocked",
                extra={
                    "client_id": client_id,
                    "endpoint": endpoint,
                    "minute_count": minute_count,
                    "limit": limit_per_minute,
                    "ip": request.client.host if request.client else "unknown"
                }
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit_per_minute} requests per minute. Blocked for {self.block_duration_seconds}s."
            )

        if hour_count > self.requests_per_hour:
            logger.warning(
                "Hourly rate limit exceeded",
                extra={
                    "client_id": client_id,
                    "endpoint": endpoint,
                    "hour_count": hour_count,
                    "limit": self.requests_per_hour
                }
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Hourly rate limit exceeded: {self.requests_per_hour} requests per hour."
            )

        # Logs pour monitoring (optionnel, seulement si proche de la limite)
        if minute_count > limit_per_minute * 0.8:
            logger.info(
                "Client approaching rate limit",
                extra={
                    "client_id": client_id,
                    "endpoint": endpoint,
                    "minute_count": minute_count,
                    "limit": limit_per_minute
                }
            )


# Instances pré-configurées pour différents types d'endpoints
standard_limiter = RateLimiter(
    requests_per_minute=60,
    requests_per_hour=1000
)

strict_limiter = RateLimiter(
    requests_per_minute=10,  # Endpoints intensifs (génération, preview)
    requests_per_hour=100
)

permissive_limiter = RateLimiter(
    requests_per_minute=120,
    requests_per_hour=2000
)
