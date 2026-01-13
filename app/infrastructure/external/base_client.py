# app/infrastructure/external/base_client.py
"""
Classe de base abstraite pour tous les clients externes.

Factorise la logique commune de gestion d'erreurs, logging et retry.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
import logging
import httpx
from app.utils.logger import get_logger


class ExternalClientBase(ABC):
    """
    Classe de base pour tous les clients API externes.

    Factorise:
    - Logging structuré
    - Gestion d'erreurs HTTP
    - Pattern d'initialisation
    - Validation de configuration
    """

    def __init__(self, service_name: str):
        """
        Initialise le client de base.

        Args:
            service_name: Nom du service (pour logging)
        """
        self.service_name = service_name
        self.logger = get_logger(f"{__name__}.{service_name}")
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False

    @abstractmethod
    async def _validate_config(self) -> bool:
        """
        Valide la configuration requise.

        Returns:
            True si configuration valide, False sinon
        """
        pass

    @abstractmethod
    async def _test_connection(self) -> bool:
        """
        Teste la connexion au service externe.

        Returns:
            True si connexion OK, False sinon
        """
        pass

    async def initialize(self) -> bool:
        """
        Initialise le client et teste la connexion.

        Returns:
            True si initialisation réussie, False sinon
        """
        if self._initialized:
            return True

        self.logger.info(f"Initializing {self.service_name} client")

        # Valider config
        if not await self._validate_config():
            self.logger.warning(f"{self.service_name} configuration incomplete")
            return False

        # Tester connexion
        try:
            if await self._test_connection():
                self._initialized = True
                self.logger.info(f"{self.service_name} client initialized successfully")
                return True
            else:
                self.logger.error(f"{self.service_name} connection test failed")
                return False
        except Exception as e:
            self.logger.error(
                f"{self.service_name} initialization failed",
                extra={"error": str(e)},
                exc_info=True
            )
            return False

    def is_initialized(self) -> bool:
        """Vérifie si le client est initialisé."""
        return self._initialized

    async def _handle_http_error(
        self,
        error: Exception,
        context: dict[str, Any]
    ) -> None:
        """
        Gère les erreurs HTTP de manière standardisée.

        Args:
            error: Exception levée
            context: Contexte supplémentaire pour logging
        """
        error_details = {
            **context,
            "service": self.service_name,
            "error_type": type(error).__name__,
            "error": str(error)
        }

        if isinstance(error, httpx.TimeoutException):
            self.logger.error(
                f"{self.service_name} request timeout",
                extra=error_details
            )
        elif isinstance(error, httpx.HTTPStatusError):
            error_details["status_code"] = error.response.status_code
            self.logger.error(
                f"{self.service_name} HTTP error",
                extra=error_details
            )
        elif isinstance(error, httpx.NetworkError):
            self.logger.error(
                f"{self.service_name} network error",
                extra=error_details
            )
        else:
            self.logger.error(
                f"{self.service_name} unexpected error",
                extra=error_details,
                exc_info=True
            )

    async def close(self) -> None:
        """Ferme le client HTTP proprement."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        self.logger.info(f"{self.service_name} client closed")
