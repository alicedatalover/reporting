# app/infrastructure/repositories/order_repo.py
"""
Repository pour les commandes (orders).

Gère toutes les requêtes liées aux ventes et commandes.
"""

from typing import Dict, List, Optional, Any
from datetime import date
from decimal import Decimal
import logging

from app.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository):
    """Repository pour les opérations sur les orders"""
    
    async def get_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une commande par son ID.
        
        Args:
            order_id: ID de la commande
        
        Returns:
            Dictionnaire avec les données de la commande ou None
        """
        query = """
            SELECT 
                id,
                company_id,
                customer_id,
                reference,
                status,
                currency,
                amount,
                source,
                created_at,
                updated_at,
                deleted_at
            FROM orders
            WHERE id = :order_id
        """
        
        return await self._fetch_one(query, {"order_id": order_id})
    
    async def exists(self, order_id: str) -> bool:
        """Vérifie si une commande existe"""
        query = "SELECT COUNT(*) FROM orders WHERE id = :order_id"
        count = await self._execute_scalar(query, {"order_id": order_id})
        return count > 0
    
    async def fetch_orders_for_period(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Récupère toutes les commandes d'une entreprise pour une période.
        
        Exclut les commandes supprimées (soft delete) et annulées.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début (incluse)
            end_date: Date de fin (incluse)
        
        Returns:
            Liste de commandes
        """
        query = """
            SELECT 
                o.id,
                o.company_id,
                o.customer_id,
                o.reference,
                o.amount,
                o.status,
                o.source,
                o.created_at
            FROM orders o
            WHERE o.company_id = :company_id
              AND DATE(o.created_at) BETWEEN :start_date AND :end_date
              AND o.deleted_at IS NULL
              AND o.status != 'cancelled'
            ORDER BY o.created_at DESC
        """
        
        orders = await self._execute_query(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        logger.debug(
            "Fetched orders for period",
            extra={
                "company_id": company_id,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "count": len(orders)
            }
        )
        
        return orders
    
    async def calculate_revenue_for_period(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> Decimal:
        """
        Calcule le chiffre d'affaires pour une période.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Montant total des ventes (Decimal)
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total_revenue
            FROM orders
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
              AND deleted_at IS NULL
              AND status != 'cancelled'
        """
        
        result = await self._execute_scalar(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        return Decimal(str(result)) if result else Decimal("0")
    
    async def count_sales_for_period(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> int:
        """
        Compte le nombre de ventes pour une période.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Nombre de commandes
        """
        query = """
            SELECT COUNT(*) as total_sales
            FROM orders
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
              AND deleted_at IS NULL
              AND status != 'cancelled'
        """
        
        return await self._execute_scalar(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ) or 0
    
    async def get_order_items(
        self,
        order_id: str
    ) -> List[Dict[str, Any]]:
        """
        Récupère les lignes d'une commande.
        
        Args:
            order_id: ID de la commande
        
        Returns:
            Liste des produits commandés
        """
        query = """
            SELECT 
                op.id,
                op.order_id,
                op.product_variant_id,
                op.quantity,
                op.price,
                op.title as product_title
            FROM order_product op
            WHERE op.order_id = :order_id
        """
        
        return await self._execute_query(query, {"order_id": order_id})
    
    async def get_top_selling_products(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Récupère les produits les plus vendus pour une période.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
            limit: Nombre de produits à retourner
        
        Returns:
            Liste de produits avec quantités vendues
        """
        query = """
            SELECT 
                op.product_variant_id,
                op.title as product_name,
                SUM(op.quantity) as total_quantity,
                SUM(op.price * op.quantity) as total_revenue,
                COUNT(DISTINCT o.id) as order_count
            FROM order_product op
            INNER JOIN orders o ON op.order_id = o.id
            WHERE o.company_id = :company_id
              AND DATE(o.created_at) BETWEEN :start_date AND :end_date
              AND o.deleted_at IS NULL
              AND o.status != 'cancelled'
            GROUP BY op.product_variant_id, op.title
            ORDER BY total_quantity DESC
            LIMIT :limit
        """
        
        return await self._execute_query(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        )