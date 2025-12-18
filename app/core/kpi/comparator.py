# app/core/kpi/comparator.py
"""
Comparateur de KPIs entre périodes.

Compare les KPIs d'une période actuelle avec une période précédente
pour détecter les variations et tendances.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Tuple
import logging

from app.domain.models import KPIData, KPIComparison
from app.core.kpi.calculator import KPICalculator

logger = logging.getLogger(__name__)


class KPIComparator:
    """
    Comparateur de KPIs entre deux périodes.
    
    Calcule les variations en pourcentage et en valeur absolue
    pour identifier les tendances.
    """
    
    def __init__(self, calculator: KPICalculator):
        """
        Initialise le comparateur.
        
        Args:
            calculator: Instance de KPICalculator
        """
        self.calculator = calculator
    
    def _calculate_previous_period_dates(
        self,
        start_date: date,
        end_date: date
    ) -> Tuple[date, date]:
        """
        Calcule les dates de la période précédente.
        
        La période précédente a la même durée que la période actuelle
        et se termine juste avant le début de la période actuelle.
        
        Args:
            start_date: Date de début période actuelle
            end_date: Date de fin période actuelle
        
        Returns:
            Tuple (prev_start_date, prev_end_date)
        
        Example:
            >>> # Période actuelle: 1-31 juillet
            >>> prev_start, prev_end = _calculate_previous_period_dates(
            ...     date(2025, 7, 1), date(2025, 7, 31)
            ... )
            >>> # Résultat: 1-30 juin (même durée)
        """
        period_duration = (end_date - start_date).days + 1
        
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_duration - 1)
        
        return prev_start_date, prev_end_date
    
    @staticmethod
    def _calculate_variation_percentage(
        current: Decimal,
        previous: Decimal
    ) -> float:
        """
        Calcule la variation en pourcentage.
        
        Args:
            current: Valeur actuelle
            previous: Valeur précédente
        
        Returns:
            Variation en % (positive si hausse, négative si baisse)
        
        Example:
            >>> _calculate_variation_percentage(Decimal("150"), Decimal("100"))
            50.0  # Hausse de 50%
        """
        if previous == 0:
            # Si valeur précédente = 0 et actuelle > 0 → +100%
            # Si les deux = 0 → 0%
            return 100.0 if current > 0 else 0.0
        
        variation = ((current - previous) / previous) * 100
        return float(variation)
    
    async def compare(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> KPIComparison:
        """
        Compare les KPIs avec la période précédente.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début période actuelle
            end_date: Date de fin période actuelle
        
        Returns:
            KPIComparison avec toutes les variations
        
        Example:
            >>> comparator = KPIComparator(calculator)
            >>> comparison = await comparator.compare(
            ...     "company_123",
            ...     date(2025, 7, 1),
            ...     date(2025, 7, 31)
            ... )
            >>> print(f"CA variation: {comparison.revenue_variation}%")
        """
        
        logger.info(
            "Comparing KPIs with previous period",
            extra={
                "company_id": company_id,
                "start_date": str(start_date),
                "end_date": str(end_date)
            }
        )
        
        try:
            # Calculer les dates de la période précédente
            prev_start_date, prev_end_date = self._calculate_previous_period_dates(
                start_date, end_date
            )
            
            logger.debug(
                "Previous period calculated",
                extra={
                    "prev_start": str(prev_start_date),
                    "prev_end": str(prev_end_date)
                }
            )
            
            # Calculer les KPIs des deux périodes
            current_kpis = await self.calculator.calculate(
                company_id, start_date, end_date
            )
            
            previous_kpis = await self.calculator.calculate(
                company_id, prev_start_date, prev_end_date
            )
            
            # Calculer les variations
            revenue_variation = self._calculate_variation_percentage(
                current_kpis.total_revenue,
                previous_kpis.total_revenue
            )
            
            sales_variation = self._calculate_variation_percentage(
                Decimal(current_kpis.total_sales),
                Decimal(previous_kpis.total_sales)
            )
            
            expenses_variation = self._calculate_variation_percentage(
                current_kpis.total_expenses,
                previous_kpis.total_expenses
            )
            
            # Variation clients récurrents (en valeur absolue, pas en %)
            returning_customers_variation = (
                current_kpis.returning_customers - 
                previous_kpis.returning_customers
            )
            
            comparison = KPIComparison(
                revenue_variation=revenue_variation,
                sales_variation=sales_variation,
                returning_customers_variation=returning_customers_variation,
                expenses_variation=expenses_variation
            )
            
            logger.info(
                "KPI comparison completed",
                extra={
                    "company_id": company_id,
                    "revenue_var": revenue_variation,
                    "sales_var": sales_variation,
                    "expenses_var": expenses_variation
                }
            )
            
            return comparison
            
        except Exception as e:
            logger.error(
                "Failed to compare KPIs",
                extra={"company_id": company_id, "error": str(e)},
                exc_info=True
            )
            raise
    
    async def detect_significant_changes(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        threshold: float = 20.0
    ) -> dict[str, float]:
        """
        Détecte les changements significatifs (> threshold%).
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
            threshold: Seuil en % pour considérer un changement significatif
        
        Returns:
            Dictionnaire des métriques avec changements significatifs
        
        Example:
            >>> changes = await comparator.detect_significant_changes(
            ...     "company_123",
            ...     date(2025, 7, 1),
            ...     date(2025, 7, 31),
            ...     threshold=15.0
            ... )
            >>> # {'revenue': -25.3, 'expenses': +85.2}
        """
        comparison = await self.compare(company_id, start_date, end_date)
        
        significant_changes = {}
        
        if abs(comparison.revenue_variation) >= threshold:
            significant_changes['revenue'] = comparison.revenue_variation
        
        if abs(comparison.sales_variation) >= threshold:
            significant_changes['sales'] = comparison.sales_variation
        
        if abs(comparison.expenses_variation) >= threshold:
            significant_changes['expenses'] = comparison.expenses_variation
        
        if significant_changes:
            logger.warning(
                "Significant KPI changes detected",
                extra={
                    "company_id": company_id,
                    "changes": significant_changes
                }
            )
        
        return significant_changes