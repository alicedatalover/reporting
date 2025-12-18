# app/core/insights/selector.py
"""
Sélecteur d'insights.

Classe les insights par importance et sélectionne les top N les plus pertinents.
"""

from typing import List
import logging

from app.domain.models import InsightModel

logger = logging.getLogger(__name__)


class InsightSelector:
    """
    Sélectionne les insights les plus pertinents selon un score composite.
    
    Formule de scoring:
    Score = (Priorité/5 × 40) + (Impact Financier/1M × 30) + (Actionable × 30)
    """
    
    def __init__(
        self,
        priority_weight: float = 40.0,
        financial_impact_weight: float = 30.0,
        actionable_weight: float = 30.0
    ):
        """
        Initialise le sélecteur avec des poids personnalisables.
        
        Args:
            priority_weight: Poids de la priorité (0-100)
            financial_impact_weight: Poids de l'impact financier (0-100)
            actionable_weight: Poids du caractère actionnable (0-100)
        """
        self.priority_weight = priority_weight
        self.financial_impact_weight = financial_impact_weight
        self.actionable_weight = actionable_weight
        
        # Normaliser les poids pour qu'ils totalisent 100
        total_weight = priority_weight + financial_impact_weight + actionable_weight
        self.priority_weight = (priority_weight / total_weight) * 100
        self.financial_impact_weight = (financial_impact_weight / total_weight) * 100
        self.actionable_weight = (actionable_weight / total_weight) * 100
    
    def calculate_score(self, insight: InsightModel) -> float:
        """
        Calcule le score d'un insight.
        
        Args:
            insight: Insight à scorer
        
        Returns:
            Score entre 0 et 100
        
        Example:
            >>> selector = InsightSelector()
            >>> score = selector.calculate_score(insight)
            >>> print(f"Score: {score:.2f}")
        """
        
        # Composante priorité (0-100)
        priority_score = (insight.priority / 5.0) * self.priority_weight
        
        # Composante impact financier (0-100)
        # Normalisation: 1M XAF = score max
        if insight.financial_impact:
            impact_normalized = min(
                float(insight.financial_impact) / 1_000_000.0,
                1.0
            )
            financial_score = impact_normalized * self.financial_impact_weight
        else:
            financial_score = 0.0
        
        # Composante actionnable (0-100)
        actionable_score = (1.0 if insight.actionable else 0.0) * self.actionable_weight
        
        # Score total
        total_score = priority_score + financial_score + actionable_score
        
        logger.debug(
            "Insight scored",
            extra={
                "insight_type": insight.type.value,
                "priority_score": priority_score,
                "financial_score": financial_score,
                "actionable_score": actionable_score,
                "total_score": total_score
            }
        )
        
        return total_score
    
    def select_top_insights(
        self,
        insights: List[InsightModel],
        max_count: int = 3
    ) -> List[InsightModel]:
        """
        Sélectionne les top N insights les plus pertinents.
        
        Args:
            insights: Liste de tous les insights détectés
            max_count: Nombre maximum d'insights à retourner
        
        Returns:
            Liste des top insights, triés par score décroissant
        
        Example:
            >>> selector = InsightSelector()
            >>> top_insights = selector.select_top_insights(all_insights, max_count=3)
        """
        
        if not insights:
            logger.info("No insights to select from")
            return []
        
        # Calculer le score de chaque insight
        scored_insights = [
            (insight, self.calculate_score(insight))
            for insight in insights
        ]
        
        # Trier par score décroissant
        scored_insights.sort(key=lambda x: x[1], reverse=True)
        
        # Sélectionner les top N
        top_insights = [
            insight for insight, score in scored_insights[:max_count]
        ]
        
        logger.info(
            "Top insights selected",
            extra={
                "total_insights": len(insights),
                "selected_count": len(top_insights),
                "top_scores": [
                    score for _, score in scored_insights[:max_count]
                ]
            }
        )
        
        return top_insights
    
    def filter_by_priority(
        self,
        insights: List[InsightModel],
        min_priority: int = 3
    ) -> List[InsightModel]:
        """
        Filtre les insights par priorité minimale.
        
        Args:
            insights: Liste d'insights
            min_priority: Priorité minimale (1-5)
        
        Returns:
            Insights avec priorité >= min_priority
        """
        filtered = [
            insight for insight in insights
            if insight.priority >= min_priority
        ]
        
        logger.debug(
            "Insights filtered by priority",
            extra={
                "input_count": len(insights),
                "filtered_count": len(filtered),
                "min_priority": min_priority
            }
        )
        
        return filtered
    
    def filter_by_financial_impact(
        self,
        insights: List[InsightModel],
        min_impact: float = 100_000.0
    ) -> List[InsightModel]:
        """
        Filtre les insights par impact financier minimum.
        
        Args:
            insights: Liste d'insights
            min_impact: Impact financier minimum en XAF
        
        Returns:
            Insights avec impact >= min_impact
        """
        filtered = [
            insight for insight in insights
            if insight.financial_impact and float(insight.financial_impact) >= min_impact
        ]
        
        logger.debug(
            "Insights filtered by financial impact",
            extra={
                "input_count": len(insights),
                "filtered_count": len(filtered),
                "min_impact": min_impact
            }
        )
        
        return filtered