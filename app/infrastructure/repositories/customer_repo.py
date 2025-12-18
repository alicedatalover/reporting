# app/infrastructure/repositories/customer_repo.py
"""
Repository pour les clients (customers).

Gère toutes les requêtes liées aux clients et à leur activité.
"""

from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging

from app.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CustomerRepository(BaseRepository):
    """Repository pour les opérations sur les customers"""
    
    async def get_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un client par son ID.
        
        Args:
            customer_id: ID du client
        
        Returns:
            Dictionnaire avec les données du client ou None
        """
        query = """
            SELECT 
                id,
                company_id,
                first_name,
                last_name,
                email,
                phone,
                created_at,
                last_activity,
                deleted_at
            FROM customers
            WHERE id = :customer_id
        """
        
        return await self._fetch_one(query, {"customer_id": customer_id})
    
    async def exists(self, customer_id: str) -> bool:
        """Vérifie si un client existe"""
        query = "SELECT COUNT(*) FROM customers WHERE id = :customer_id"
        count = await self._execute_scalar(query, {"customer_id": customer_id})
        return count > 0
    
    async def count_new_customers(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> int:
        """
        Compte les nouveaux clients créés pendant une période.
        
        Un nouveau client est un client dont la date de création (created_at)
        est dans la période spécifiée.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Nombre de nouveaux clients
        """
        query = """
            SELECT COUNT(DISTINCT id) as count
            FROM customers
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
              AND deleted_at IS NULL
        """
        
        count = await self._execute_scalar(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ) or 0
        
        logger.debug(
            "Counted new customers",
            extra={
                "company_id": company_id,
                "count": count,
                "period": f"{start_date} to {end_date}"
            }
        )
        
        return count
    
    async def count_returning_customers(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> int:
        """
        Compte les clients récurrents pour une période.
        
        Un client récurrent est un client qui :
        - A passé une commande pendant la période
        - ET avait déjà passé au moins une commande AVANT cette période
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Nombre de clients récurrents
        """
        query = """
            SELECT COUNT(DISTINCT o.customer_id) as count
            FROM orders o
            WHERE o.company_id = :company_id
              AND DATE(o.created_at) BETWEEN :start_date AND :end_date
              AND o.deleted_at IS NULL
              AND o.status != 'cancelled'
              AND o.customer_id IN (
                  SELECT customer_id
                  FROM orders
                  WHERE company_id = :company_id
                    AND DATE(created_at) < :start_date
                    AND deleted_at IS NULL
              )
        """
        
        count = await self._execute_scalar(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ) or 0
        
        logger.debug(
            "Counted returning customers",
            extra={
                "company_id": company_id,
                "count": count
            }
        )
        
        return count
    
    async def get_customers_at_churn_risk(
        self,
        company_id: str,
        min_orders: int = 3,
        inactive_days: int = 45,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Identifie les clients fidèles inactifs (à risque de churn).
        
        Critères:
        - Au moins X commandes au total
        - Pas commandé depuis Y jours
        
        Args:
            company_id: ID de l'entreprise
            min_orders: Nombre minimum de commandes (fidélité)
            inactive_days: Jours d'inactivité minimum
            limit: Nombre max de clients à retourner
        
        Returns:
            Liste de clients à risque avec leur CLV
        """
        query = """
            SELECT 
                c.id as customer_id,
                CONCAT(c.first_name, ' ', c.last_name) as customer_name,
                c.email,
                c.phone,
                MAX(o.created_at) as last_order_date,
                COUNT(o.id) as total_orders,
                SUM(o.amount) as lifetime_value,
                DATEDIFF(NOW(), MAX(o.created_at)) as days_inactive
            FROM customers c
            INNER JOIN orders o ON c.id = o.customer_id
            WHERE c.company_id = :company_id
              AND o.deleted_at IS NULL
              AND o.status != 'cancelled'
              AND c.deleted_at IS NULL
            GROUP BY c.id, c.first_name, c.last_name, c.email, c.phone
            HAVING 
                total_orders >= :min_orders
                AND DATEDIFF(NOW(), last_order_date) > :inactive_days
            ORDER BY lifetime_value DESC
            LIMIT :limit
        """
        
        customers = await self._execute_query(
            query,
            {
                "company_id": company_id,
                "min_orders": min_orders,
                "inactive_days": inactive_days,
                "limit": limit
            }
        )
        
        logger.info(
            "Identified customers at churn risk",
            extra={
                "company_id": company_id,
                "count": len(customers),
                "total_clv": sum(c.get('lifetime_value', 0) for c in customers)
            }
        )
        
        return customers
    
    async def get_customer_lifetime_value(
        self,
        customer_id: str
    ) -> Decimal:
        """
        Calcule la valeur vie client (CLV).
        
        Args:
            customer_id: ID du client
        
        Returns:
            Montant total dépensé (Decimal)
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as clv
            FROM orders
            WHERE customer_id = :customer_id
              AND deleted_at IS NULL
              AND status != 'cancelled'
        """
        
        result = await self._execute_scalar(query, {"customer_id": customer_id})
        return Decimal(str(result)) if result else Decimal("0")
    
    async def get_customer_order_history(
        self,
        customer_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des commandes d'un client.
        
        Args:
            customer_id: ID du client
            limit: Nombre max de commandes
        
        Returns:
            Liste des commandes
        """
        query = """
            SELECT 
                id,
                reference,
                amount,
                status,
                created_at
            FROM orders
            WHERE customer_id = :customer_id
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT :limit
        """
        
        return await self._execute_query(
            query,
            {"customer_id": customer_id, "limit": limit}
        )