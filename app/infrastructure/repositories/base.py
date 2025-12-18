# app/infrastructure/repositories/base.py
"""
Interface abstraite pour les repositories.

Définit le contrat que tous les repositories doivent respecter.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession


class AbstractRepository(ABC):
    """
    Classe abstraite pour les repositories.
    
    Tous les repositories doivent hériter de cette classe et implémenter
    les méthodes nécessaires pour leur domaine.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialise le repository avec une session DB.
        
        Args:
            session: Session SQLAlchemy async
        """
        self.session = session
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une entité par son ID.
        
        Args:
            id: Identifiant de l'entité
        
        Returns:
            Dictionnaire avec les données ou None
        """
        pass
    
    @abstractmethod
    async def exists(self, id: str) -> bool:
        """
        Vérifie si une entité existe.
        
        Args:
            id: Identifiant de l'entité
        
        Returns:
            True si existe, False sinon
        """
        pass


class BaseRepository(AbstractRepository):
    """
    Repository de base avec méthodes utilitaires communes.
    
    Fournit des helpers pour l'exécution de requêtes SQL et la gestion
    des résultats.
    """
    
    async def _execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Exécute une requête SQL et retourne les résultats.
        
        Args:
            query: Requête SQL (avec paramètres nommés :param)
            params: Dictionnaire des paramètres
        
        Returns:
            Liste de dictionnaires (un par ligne)
        
        Example:
            >>> await self._execute_query(
            ...     "SELECT * FROM users WHERE id = :id",
            ...     {"id": "123"}
            ... )
        """
        from sqlalchemy import text
        
        result = await self.session.execute(
            text(query),
            params or {}
        )
        
        return [dict(row._mapping) for row in result.all()]
    
    async def _execute_scalar(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Exécute une requête et retourne un seul résultat scalaire.
        
        Args:
            query: Requête SQL
            params: Paramètres
        
        Returns:
            Valeur scalaire ou None
        
        Example:
            >>> count = await self._execute_scalar(
            ...     "SELECT COUNT(*) FROM users WHERE active = :active",
            ...     {"active": True}
            ... )
        """
        from sqlalchemy import text
        
        result = await self.session.execute(
            text(query),
            params or {}
        )
        
        return result.scalar()
    
    async def _fetch_one(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Exécute une requête et retourne la première ligne.
        
        Args:
            query: Requête SQL
            params: Paramètres
        
        Returns:
            Dictionnaire ou None si pas de résultat
        """
        from sqlalchemy import text
        
        result = await self.session.execute(
            text(query),
            params or {}
        )
        
        row = result.first()
        return dict(row._mapping) if row else None
    
    def _apply_collation_cast(self, column: str) -> str:
        """
        Applique un CAST pour uniformiser la collation (fix problème MySQL).
        
        Args:
            column: Nom de la colonne
        
        Returns:
            Expression SQL avec CAST
        
        Example:
            >>> self._apply_collation_cast("company_id")
            'CAST(company_id AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_unicode_520_ci'
        """
        return (
            f"CAST({column} AS CHAR CHARACTER SET utf8mb4) "
            f"COLLATE utf8mb4_unicode_520_ci"
        )