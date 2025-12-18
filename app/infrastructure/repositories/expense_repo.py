# app/infrastructure/repositories/expense_repo.py
"""
Repository pour les dépenses (bills/expenses).

Gère toutes les requêtes liées aux dépenses et factures fournisseurs.
"""

from typing import Dict, List, Optional, Any
from datetime import date
from decimal import Decimal
import logging

from app.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ExpenseRepository(BaseRepository):
    """Repository pour les opérations sur les dépenses"""
    
    async def get_by_id(self, expense_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une dépense par son ID.
        
        Note: Dans Genuka, les dépenses sont dans la table 'bills'
        
        Args:
            expense_id: ID de la dépense
        
        Returns:
            Dictionnaire avec les données de la dépense ou None
        """
        query = """
            SELECT 
                id,
                company_id,
                supplier_id,
                reference,
                status,
                amount,
                expense_type,
                due_date,
                paid_at,
                created_at,
                deleted_at
            FROM bills
            WHERE id = :expense_id
        """
        
        return await self._fetch_one(query, {"expense_id": expense_id})
    
    async def exists(self, expense_id: str) -> bool:
        """Vérifie si une dépense existe"""
        query = "SELECT COUNT(*) FROM bills WHERE id = :expense_id"
        count = await self._execute_scalar(query, {"expense_id": expense_id})
        return count > 0
    
    async def fetch_expenses_for_period(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Récupère toutes les dépenses d'une entreprise pour une période.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Liste de dépenses
        """
        query = """
            SELECT 
                id,
                company_id,
                supplier_id,
                reference,
                amount,
                expense_type,
                status,
                created_at,
                paid_at
            FROM bills
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
              AND deleted_at IS NULL
            ORDER BY created_at DESC
        """
        
        expenses = await self._execute_query(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        logger.debug(
            "Fetched expenses for period",
            extra={
                "company_id": company_id,
                "count": len(expenses)
            }
        )
        
        return expenses
    
    async def calculate_total_expenses(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> Decimal:
        """
        Calcule le total des dépenses pour une période.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Montant total des dépenses
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total_expenses
            FROM bills
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
              AND deleted_at IS NULL
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
    
    async def get_expenses_by_type(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Récupère les dépenses groupées par type.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Liste avec types et montants
        """
        query = """
            SELECT 
                expense_type,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM bills
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
              AND deleted_at IS NULL
            GROUP BY expense_type
            ORDER BY total_amount DESC
        """
        
        return await self._execute_query(
            query,
            {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )
    
    async def detect_expense_anomalies(
        self,
        company_id: str,
        current_period_start: date,
        current_period_end: date,
        comparison_period_start: date,
        comparison_period_end: date,
        threshold_percentage: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Détecte les anomalies de dépenses par rapport à une période de référence.
        
        Une anomalie est détectée si les dépenses ont augmenté de plus de X%.
        
        Args:
            company_id: ID de l'entreprise
            current_period_start: Début période actuelle
            current_period_end: Fin période actuelle
            comparison_period_start: Début période de comparaison
            comparison_period_end: Fin période de comparaison
            threshold_percentage: Seuil d'alerte en %
        
        Returns:
            Liste des types de dépenses avec anomalies
        """
        query = """
            WITH current_expenses AS (
                SELECT 
                    expense_type,
                    SUM(amount) as current_amount
                FROM bills
                WHERE company_id = :company_id
                  AND DATE(created_at) BETWEEN :current_start AND :current_end
                  AND deleted_at IS NULL
                GROUP BY expense_type
            ),
            previous_expenses AS (
                SELECT 
                    expense_type,
                    SUM(amount) as previous_amount
                FROM bills
                WHERE company_id = :company_id
                  AND DATE(created_at) BETWEEN :previous_start AND :previous_end
                  AND deleted_at IS NULL
                GROUP BY expense_type
            )
            SELECT 
                c.expense_type,
                c.current_amount,
                COALESCE(p.previous_amount, 0) as previous_amount,
                CASE 
                    WHEN COALESCE(p.previous_amount, 0) = 0 THEN 100
                    ELSE ((c.current_amount - p.previous_amount) / p.previous_amount * 100)
                END as variation_percentage
            FROM current_expenses c
            LEFT JOIN previous_expenses p ON c.expense_type = p.expense_type
            HAVING variation_percentage >= :threshold
            ORDER BY variation_percentage DESC
        """
        
        anomalies = await self._execute_query(
            query,
            {
                "company_id": company_id,
                "current_start": current_period_start,
                "current_end": current_period_end,
                "previous_start": comparison_period_start,
                "previous_end": comparison_period_end,
                "threshold": threshold_percentage
            }
        )
        
        if anomalies:
            logger.warning(
                "Expense anomalies detected",
                extra={
                    "company_id": company_id,
                    "anomaly_count": len(anomalies)
                }
            )
        
        return anomalies
    
    async def get_top_expenses(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Récupère les plus grosses dépenses pour une période.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
            limit: Nombre max de résultats
        
        Returns:
            Liste des plus grosses dépenses
        """
        query = """
            SELECT 
                id,
                reference,
                expense_type,
                amount,
                supplier_id,
                created_at
            FROM bills
            WHERE company_id = :company_id
              AND DATE(created_at) BETWEEN :start_date AND :end_date
              AND deleted_at IS NULL
            ORDER BY amount DESC
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
    
    async def count_unpaid_expenses(
        self,
        company_id: str
    ) -> int:
        """
        Compte le nombre de factures impayées.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Nombre de factures avec status != 'paid'
        """
        query = """
            SELECT COUNT(*) as count
            FROM bills
            WHERE company_id = :company_id
              AND status != 'paid'
              AND deleted_at IS NULL
        """
        
        return await self._execute_scalar(query, {"company_id": company_id}) or 0