# app/infrastructure/repositories/order_repo.py
"""
Repository pour les commandes (orders).

Gère toutes les requêtes liées aux ventes et commandes.
"""

from typing import Dict, List, Optional, Any
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
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
        end_date: date,
        limit: Optional[int] = 10000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Récupère les commandes d'une entreprise pour une période.

        Exclut les commandes supprimées (soft delete) et annulées.

        NOTE: Cette méthode n'est actuellement pas utilisée dans le code.
        Les KPIs sont calculés via calculate_sales_kpis() qui utilise des agrégations SQL.

        Args:
            company_id: ID de l'entreprise
            start_date: Date de début (incluse)
            end_date: Date de fin (incluse)
            limit: Nombre max de résultats (défaut: 10000, None = pas de limite)
            offset: Décalage pour pagination (défaut: 0)

        Returns:
            Liste de commandes (paginée si limit fourni)
        """
        # Convertir dates en timestamps pour utiliser les index
        # created_at >= start_date (00:00:00) ET created_at < end_date + 1 jour (00:00:00)
        end_date_exclusive = end_date + timedelta(days=1)

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
              AND o.created_at >= :start_date
              AND o.created_at < :end_date_exclusive
              AND o.deleted_at IS NULL
              AND o.status != 'cancelled'
            ORDER BY o.created_at DESC
        """

        params = {
            "company_id": company_id,
            "start_date": start_date,
            "end_date_exclusive": end_date_exclusive,
        }

        # Ajouter pagination si limit fourni
        if limit is not None:
            query += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

        orders = await self._execute_query(query, params)
        
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
        end_date_exclusive = end_date + timedelta(days=1)

        query = """
            SELECT COALESCE(SUM(amount), 0) as total_revenue
            FROM orders
            WHERE company_id = :company_id
              AND created_at >= :start_date
              AND created_at < :end_date_exclusive
              AND deleted_at IS NULL
              AND status != 'cancelled'
        """

        result = await self._execute_scalar(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date_exclusive": end_date_exclusive
            }
        )

        # Conversion robuste avec gestion d'erreurs
        if not result:
            return Decimal("0")

        try:
            return Decimal(str(result))
        except (TypeError, ValueError, InvalidOperation) as e:
            logger.error(
                "Failed to convert revenue to Decimal",
                extra={
                    "company_id": company_id,
                    "result": result,
                    "error": str(e)
                }
            )
            return Decimal("0")
    
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
        end_date_exclusive = end_date + timedelta(days=1)

        query = """
            SELECT COUNT(*) as total_sales
            FROM orders
            WHERE company_id = :company_id
              AND created_at >= :start_date
              AND created_at < :end_date_exclusive
              AND deleted_at IS NULL
              AND status != 'cancelled'
        """

        return await self._execute_scalar(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date_exclusive": end_date_exclusive
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
        end_date_exclusive = end_date + timedelta(days=1)

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
              AND o.created_at >= :start_date
              AND o.created_at < :end_date_exclusive
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
                "end_date_exclusive": end_date_exclusive,
                "limit": limit
            }
        )

    async def calculate_sales_kpis(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Calcule les KPIs de vente (revenue + count) en une seule requête optimisée.

        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin

        Returns:
            Dict avec 'total_revenue' (Decimal) et 'total_sales' (int)
        """
        end_date_exclusive = end_date + timedelta(days=1)

        query = """
            SELECT
                COALESCE(SUM(amount), 0) as total_revenue,
                COUNT(*) as total_sales
            FROM orders
            WHERE company_id = :company_id
              AND created_at >= :start_date
              AND created_at < :end_date_exclusive
              AND deleted_at IS NULL
              AND status != 'cancelled'
        """

        result = await self._fetch_one(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date_exclusive": end_date_exclusive
            }
        )

        if not result:
            return {
                "total_revenue": Decimal("0"),
                "total_sales": 0
            }

        # Conversion robuste avec gestion d'erreurs
        try:
            revenue = Decimal(str(result['total_revenue']))
        except (TypeError, ValueError, InvalidOperation) as e:
            logger.error(
                "Failed to convert revenue to Decimal in calculate_sales_kpis",
                extra={
                    "company_id": company_id,
                    "revenue_value": result.get('total_revenue'),
                    "error": str(e)
                }
            )
            revenue = Decimal("0")

        try:
            sales_count = int(result['total_sales'])
        except (TypeError, ValueError) as e:
            logger.error(
                "Failed to convert sales count to int",
                extra={
                    "company_id": company_id,
                    "sales_value": result.get('total_sales'),
                    "error": str(e)
                }
            )
            sales_count = 0

        return {
            "total_revenue": revenue,
            "total_sales": sales_count
        }