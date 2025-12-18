# app/infrastructure/repositories/stock_repo.py
"""
Repository pour les stocks.

Gère toutes les requêtes liées aux stocks et aux alertes d'inventaire.
"""

from typing import Dict, List, Optional, Any
from datetime import date
from decimal import Decimal
import logging

from app.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class StockRepository(BaseRepository):
    """Repository pour les opérations sur les stocks"""
    
    async def get_by_id(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un stock par son ID.
        
        Args:
            stock_id: ID du stock
        
        Returns:
            Dictionnaire avec les données du stock ou None
        """
        query = """
            SELECT 
                s.id,
                s.company_id,
                s.product_variant_id,
                s.title,
                s.quantity_alert,
                s.price,
                s.created_at,
                COALESCE(SUM(sw.quantity), 0) as total_quantity
            FROM stocks s
            LEFT JOIN stock_warehouse sw ON s.id = sw.stock_id
            WHERE s.id = :stock_id
            GROUP BY s.id, s.company_id, s.product_variant_id, s.title, 
                     s.quantity_alert, s.price, s.created_at
        """
        
        return await self._fetch_one(query, {"stock_id": stock_id})
    
    async def exists(self, stock_id: str) -> bool:
        """Vérifie si un stock existe"""
        query = "SELECT COUNT(*) FROM stocks WHERE id = :stock_id"
        count = await self._execute_scalar(query, {"stock_id": stock_id})
        return count > 0
    
    async def get_stock_alerts(
        self,
        company_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Récupère les produits en alerte de stock.
        
        Un produit est en alerte si :
        - stock_total <= quantity_alert
        
        Args:
            company_id: ID de l'entreprise
            limit: Nombre max de résultats
        
        Returns:
            Liste de produits en alerte, triés par criticité (stock le plus bas)
        """
        query = """
            SELECT 
                s.id,
                s.title as product_name,
                s.product_variant_id,
                COALESCE(SUM(sw.quantity), 0) as stock_total,
                s.quantity_alert,
                s.price,
                CASE 
                    WHEN COALESCE(SUM(sw.quantity), 0) = 0 THEN 'critical'
                    WHEN COALESCE(SUM(sw.quantity), 0) <= s.quantity_alert * 0.5 THEN 'high'
                    ELSE 'medium'
                END as alert_level
            FROM stocks s
            LEFT JOIN stock_warehouse sw ON s.id = sw.stock_id
            WHERE s.company_id = :company_id
            GROUP BY s.id, s.title, s.product_variant_id, s.quantity_alert, s.price
            HAVING stock_total <= s.quantity_alert
            ORDER BY stock_total ASC
            LIMIT :limit
        """
        
        alerts = await self._execute_query(
            query,
            {"company_id": company_id, "limit": limit}
        )
        
        logger.info(
            "Fetched stock alerts",
            extra={
                "company_id": company_id,
                "count": len(alerts),
                "critical": sum(1 for a in alerts if a['alert_level'] == 'critical')
            }
        )
        
        return alerts
    
    async def count_stock_alerts(
        self,
        company_id: str
    ) -> int:
        """
        Compte le nombre de produits en alerte.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Nombre de produits en alerte
        """
        query = """
            SELECT COUNT(*) as alert_count
            FROM (
                SELECT s.id
                FROM stocks s
                LEFT JOIN stock_warehouse sw ON s.id = sw.stock_id
                WHERE s.company_id = :company_id
                GROUP BY s.id, s.quantity_alert
                HAVING COALESCE(SUM(sw.quantity), 0) <= s.quantity_alert
            ) as alerts
        """
        
        return await self._execute_scalar(query, {"company_id": company_id}) or 0
    
    async def get_stock_by_warehouse(
        self,
        company_id: str,
        warehouse_id: str
    ) -> List[Dict[str, Any]]:
        """
        Récupère les stocks d'un entrepôt spécifique.
        
        Args:
            company_id: ID de l'entreprise
            warehouse_id: ID de l'entrepôt
        
        Returns:
            Liste des stocks dans cet entrepôt
        """
        query = """
            SELECT 
                s.id,
                s.title as product_name,
                sw.quantity,
                s.quantity_alert,
                s.price
            FROM stocks s
            INNER JOIN stock_warehouse sw ON s.id = sw.stock_id
            WHERE s.company_id = :company_id
              AND sw.warehouse_id = :warehouse_id
            ORDER BY s.title
        """
        
        return await self._execute_query(
            query,
            {"company_id": company_id, "warehouse_id": warehouse_id}
        )
    
    async def get_total_inventory_value(
        self,
        company_id: str
    ) -> Decimal:
        """
        Calcule la valeur totale du stock.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Valeur totale (quantity * price)
        """
        query = """
            SELECT COALESCE(SUM(
                COALESCE(sw.quantity, 0) * COALESCE(s.price, 0)
            ), 0) as total_value
            FROM stocks s
            LEFT JOIN stock_warehouse sw ON s.id = sw.stock_id
            WHERE s.company_id = :company_id
        """
        
        result = await self._execute_scalar(query, {"company_id": company_id})
        return Decimal(str(result)) if result else Decimal("0")
    
    async def get_stock_movements(
        self,
        company_id: str,
        stock_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des mouvements de stock.
        
        Args:
            company_id: ID de l'entreprise
            stock_id: ID du stock (optionnel, tous si None)
            start_date: Date de début (optionnelle)
            end_date: Date de fin (optionnelle)
            limit: Nombre max de résultats
        
        Returns:
            Liste des mouvements de stock
        """
        conditions = ["sh.company_id = :company_id"]
        params: Dict[str, Any] = {"company_id": company_id, "limit": limit}
        
        if stock_id:
            conditions.append("sh.stock_id = :stock_id")
            params["stock_id"] = stock_id
        
        if start_date:
            conditions.append("DATE(sh.date) >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            conditions.append("DATE(sh.date) <= :end_date")
            params["end_date"] = end_date
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT 
                sh.id,
                sh.stock_id,
                s.title as product_name,
                sh.quantity,
                sh.date,
                sh.warehouse_id
            FROM stock_histories sh
            INNER JOIN stocks s ON sh.stock_id = s.id
            WHERE {where_clause}
            ORDER BY sh.date DESC
            LIMIT :limit
        """
        
        return await self._execute_query(query, params)
    
    async def get_low_stock_products_count(
        self,
        company_id: str,
        threshold_percentage: float = 0.5
    ) -> int:
        """
        Compte les produits dont le stock est en dessous d'un certain seuil.
        
        Args:
            company_id: ID de l'entreprise
            threshold_percentage: % du quantity_alert (ex: 0.5 = 50%)
        
        Returns:
            Nombre de produits concernés
        """
        query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT s.id
                FROM stocks s
                LEFT JOIN stock_warehouse sw ON s.id = sw.stock_id
                WHERE s.company_id = :company_id
                GROUP BY s.id, s.quantity_alert
                HAVING COALESCE(SUM(sw.quantity), 0) <= (s.quantity_alert * :threshold)
            ) as low_stock
        """
        
        return await self._execute_scalar(
            query,
            {"company_id": company_id, "threshold": threshold_percentage}
        ) or 0