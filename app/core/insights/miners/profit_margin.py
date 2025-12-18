# app/core/insights/miners/profit_margin.py
"""
Insight Miner pour la marge bénéficiaire.

Analyse la rentabilité et détecte les situations problématiques ou exceptionnelles.
"""

from datetime import date
from typing import Optional, Dict, Any
from decimal import Decimal

from app.core.insights.base import AbstractInsightMiner
from app.domain.models import InsightModel
from app.domain.enums import InsightType
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.repositories.expense_repo import ExpenseRepository


class ProfitMarginMiner(AbstractInsightMiner):
    """
    Analyse la marge bénéficiaire et détecte les anomalies.
    
    Seuils:
    - Marge < 0% → Perte (priorité 5)
    - Marge < 10% → Faible rentabilité (priorité 4)
    - Marge > 40% → Excellente performance (priorité 2)
    """
    
    def __init__(
        self,
        order_repo: OrderRepository,
        expense_repo: ExpenseRepository
    ):
        """
        Initialise le miner.
        
        Args:
            order_repo: Repository des commandes
            expense_repo: Repository des dépenses
        """
        self.order_repo = order_repo
        self.expense_repo = expense_repo
    
    @property
    def name(self) -> str:
        return "ProfitMarginMiner"
    
    async def mine(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[InsightModel]:
        """
        Analyse la marge bénéficiaire.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
            context: Contexte avec KPIs pré-calculés (optionnel)
        
        Returns:
            InsightModel si situation notable détectée, None sinon
        """
        
        # Récupérer CA et dépenses
        if context and 'total_revenue' in context and 'total_expenses' in context:
            total_revenue = Decimal(str(context['total_revenue']))
            total_expenses = Decimal(str(context['total_expenses']))
            net_result = Decimal(str(context.get('net_result', total_revenue - total_expenses)))
        else:
            total_revenue = await self.order_repo.calculate_revenue_for_period(
                company_id, start_date, end_date
            )
            total_expenses = await self.expense_repo.calculate_total_expenses(
                company_id, start_date, end_date
            )
            net_result = total_revenue - total_expenses
        
        # Si pas de revenus, pas d'insight
        if total_revenue == 0:
            self._log_no_insight(company_id, "No revenue for period")
            return None
        
        # Calculer la marge
        profit_margin = float((net_result / total_revenue) * 100)
        
        # Déterminer le type d'insight selon la marge
        if profit_margin < 0:
            # PERTE - Critique
            title = "🚨 Résultat Déficitaire"
            description = (
                f"Vos dépenses ({total_expenses:,.0f} XAF) dépassent votre CA "
                f"({total_revenue:,.0f} XAF). Perte: {abs(net_result):,.0f} XAF. "
                f"Réduisez d'urgence vos charges."
            )
            priority = 5
            actionable = True
            financial_impact = abs(net_result)
            
        elif profit_margin < 10:
            # FAIBLE RENTABILITÉ - Urgent
            title = "⚠️ Rentabilité Faible"
            description = (
                f"Votre marge bénéficiaire est de seulement {profit_margin:.1f}%. "
                f"Optimisez vos dépenses ou augmentez vos prix pour améliorer la rentabilité."
            )
            priority = 4
            actionable = True
            financial_impact = None
            
        elif profit_margin > 40:
            # EXCELLENTE PERFORMANCE - Informatif
            title = "🎉 Excellente Rentabilité"
            description = (
                f"Félicitations ! Votre marge bénéficiaire atteint {profit_margin:.1f}%. "
                f"Profitez de cette santé financière pour investir dans la croissance."
            )
            priority = 2
            actionable = True
            financial_impact = None
            
        else:
            # Marge normale (10-40%) - Pas d'insight
            self._log_no_insight(
                company_id,
                f"Profit margin {profit_margin:.1f}% is in normal range"
            )
            return None
        
        insight = InsightModel(
            type=InsightType.PROFIT_MARGIN,
            title=title,
            description=description,
            priority=priority,
            financial_impact=financial_impact,
            actionable=actionable,
            metadata={
                "profit_margin": profit_margin,
                "total_revenue": float(total_revenue),
                "total_expenses": float(total_expenses),
                "net_result": float(net_result),
                "expense_ratio": float((total_expenses / total_revenue) * 100)
            }
        )
        
        self._log_insight_detected(company_id, insight)
        
        return insight