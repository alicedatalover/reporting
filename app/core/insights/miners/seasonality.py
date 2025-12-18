# app/core/insights/miners/seasonality.py
"""
Insight Miner pour les variations saisonnières.

Détecte les hausses ou baisses significatives de CA par rapport à la période précédente.
"""

from datetime import date, timedelta
from typing import Optional, Dict, Any
from decimal import Decimal

from app.core.insights.base import AbstractInsightMiner
from app.domain.models import InsightModel
from app.domain.enums import InsightType
from app.infrastructure.repositories.order_repo import OrderRepository


class SeasonalityMiner(AbstractInsightMiner):
    """
    Détecte les variations saisonnières de revenus.
    
    Compare le CA actuel avec la période précédente.
    Seuil: ±20% de variation
    
    Priorité: 3/5 (moyenne)
    """
    
    def __init__(
        self,
        order_repo: OrderRepository,
        threshold_percentage: float = 20.0
    ):
        """
        Initialise le miner.
        
        Args:
            order_repo: Repository des commandes
            threshold_percentage: Seuil de variation en % pour déclencher un insight
        """
        self.order_repo = order_repo
        self.threshold_percentage = threshold_percentage
    
    @property
    def name(self) -> str:
        return "SeasonalityMiner"
    
    def _calculate_previous_period(
        self,
        start_date: date,
        end_date: date
    ) -> tuple[date, date]:
        """
        Calcule les dates de la période précédente.
        
        Args:
            start_date: Date de début période actuelle
            end_date: Date de fin période actuelle
        
        Returns:
            Tuple (prev_start_date, prev_end_date)
        """
        period_duration = (end_date - start_date).days + 1
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_duration - 1)
        
        return prev_start_date, prev_end_date
    
    async def mine(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[InsightModel]:
        """
        Détecte les variations saisonnières.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début période actuelle
            end_date: Date de fin période actuelle
            context: Contexte avec KPIs pré-calculés (optionnel)
        
        Returns:
            InsightModel si variation significative détectée, None sinon
        """
        
        # Calculer les dates de la période précédente
        prev_start_date, prev_end_date = self._calculate_previous_period(
            start_date, end_date
        )
        
        # Récupérer le CA actuel
        if context and 'total_revenue' in context:
            current_revenue = Decimal(str(context['total_revenue']))
        else:
            current_revenue = await self.order_repo.calculate_revenue_for_period(
                company_id, start_date, end_date
            )
        
        # Récupérer le CA de la période précédente
        previous_revenue = await self.order_repo.calculate_revenue_for_period(
            company_id, prev_start_date, prev_end_date
        )
        
        # Calculer la variation
        if previous_revenue == 0:
            # Pas de comparaison possible
            if current_revenue > 0:
                # Première période avec des ventes
                self._log_no_insight(
                    company_id,
                    "No previous period data for comparison"
                )
            return None
        
        variation_percentage = float(
            ((current_revenue - previous_revenue) / previous_revenue) * 100
        )
        
        # Vérifier si la variation dépasse le seuil
        if abs(variation_percentage) < self.threshold_percentage:
            self._log_no_insight(
                company_id,
                f"Variation {variation_percentage:.1f}% below threshold"
            )
            return None
        
        # Déterminer le type de variation
        is_increase = variation_percentage > 0
        
        if is_increase:
            title = "📈 Hausse Saisonnière"
            emoji = "📈"
            verb = "augmenté"
        else:
            title = "📉 Baisse Saisonnière"
            emoji = "📉"
            verb = "baissé"
        
        # Impact financier (delta)
        financial_impact = abs(current_revenue - previous_revenue)
        
        # Description
        description = (
            f"Vos ventes ont {verb} de {abs(variation_percentage):.0f}% "
            f"vs {self._format_period(prev_start_date, prev_end_date)}. "
            f"{'Capitalisez sur cette dynamique' if is_increase else 'Anticipez cette tendance'}."
        )
        
        insight = InsightModel(
            type=InsightType.SEASONALITY,
            title=title,
            description=description,
            priority=3,  # Moyenne
            financial_impact=financial_impact if not is_increase else None,
            actionable=True,
            metadata={
                "variation_percentage": variation_percentage,
                "current_revenue": float(current_revenue),
                "previous_revenue": float(previous_revenue),
                "delta": float(financial_impact),
                "is_increase": is_increase,
                "current_period": f"{start_date} to {end_date}",
                "previous_period": f"{prev_start_date} to {prev_end_date}"
            }
        )
        
        self._log_insight_detected(company_id, insight)
        
        return insight
    
    @staticmethod
    def _format_period(start_date: date, end_date: date) -> str:
        """
        Formate une période pour affichage.
        
        Args:
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Période formatée (ex: "le mois dernier", "la période précédente")
        """
        duration = (end_date - start_date).days + 1
        
        if 6 <= duration <= 8:
            return "la semaine dernière"
        elif 28 <= duration <= 31:
            return "le mois dernier"
        elif 88 <= duration <= 92:
            return "le trimestre dernier"
        else:
            return "la période précédente"