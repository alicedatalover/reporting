# app/core/insights/miners/churn_risk.py
"""
Insight Miner pour le risque de churn (perte de clients).

Identifie les clients fidèles devenus inactifs et estime le risque financier.
"""

from datetime import date
from typing import Optional, Dict, Any
from decimal import Decimal

from app.core.insights.base import AbstractInsightMiner
from app.domain.models import InsightModel
from app.domain.enums import InsightType
from app.infrastructure.repositories.customer_repo import CustomerRepository
from app.config import settings


class ChurnRiskMiner(AbstractInsightMiner):
    """
    Détecte les clients fidèles à risque de churn.
    
    Critères:
    - Au moins 3 commandes (client fidèle)
    - Inactif depuis 45+ jours
    
    Priorité: 4/5 (urgence élevée)
    """
    
    def __init__(
        self,
        customer_repo: CustomerRepository,
        min_orders: int = 3,
        inactive_days: Optional[int] = None
    ):
        """
        Initialise le miner.

        Args:
            customer_repo: Repository des clients
            min_orders: Nombre min de commandes pour être "fidèle"
            inactive_days: Jours d'inactivité pour être "à risque" (défaut: depuis config)
        """
        self.customer_repo = customer_repo
        self.min_orders = min_orders
        self.inactive_days = inactive_days or settings.CHURN_INACTIVE_DAYS
    
    @property
    def name(self) -> str:
        return "ChurnRiskMiner"
    
    async def mine(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[InsightModel]:
        """
        Détecte les clients à risque de churn.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début (non utilisée)
            end_date: Date de fin (non utilisée)
            context: Contexte (optionnel)
        
        Returns:
            InsightModel si clients à risque détectés, None sinon
        """
        
        # Récupérer les clients à risque
        at_risk_customers = await self.customer_repo.get_customers_at_churn_risk(
            company_id=company_id,
            min_orders=self.min_orders,
            inactive_days=self.inactive_days,
            limit=20
        )
        
        if not at_risk_customers:
            self._log_no_insight(company_id, "No customers at churn risk")
            return None
        
        # Calculer le risque financier total (CLV cumulée)
        total_clv_at_risk = sum(
            Decimal(str(customer.get('lifetime_value', 0)))
            for customer in at_risk_customers
        )
        
        # Nombre de clients à risque
        customer_count = len(at_risk_customers)
        
        # Construire le message
        title = "🚨 Clients Inactifs à Risque"
        
        if customer_count == 1:
            customer_name = at_risk_customers[0].get('customer_name', 'Client')
            days_inactive = at_risk_customers[0].get('days_inactive', self.inactive_days)
            description = (
                f"{customer_name} n'a pas commandé depuis {days_inactive} jours. "
                f"Risque de perte: {total_clv_at_risk:,.0f} XAF"
            )
        else:
            description = (
                f"{customer_count} clients fidèles n'ont pas commandé depuis "
                f"{self.inactive_days}+ jours. Risque de perte: {total_clv_at_risk:,.0f} XAF"
            )
        
        insight = InsightModel(
            type=InsightType.CHURN_RISK,
            title=title,
            description=description,
            priority=4,  # Haute priorité
            financial_impact=total_clv_at_risk,
            actionable=True,
            metadata={
                "customer_count": customer_count,
                "total_clv_at_risk": float(total_clv_at_risk),
                "min_orders_threshold": self.min_orders,
                "inactive_days_threshold": self.inactive_days,
                "top_customers": [
                    {
                        "name": c.get('customer_name'),
                        "email": c.get('email'),
                        "phone": c.get('phone'),
                        "lifetime_value": float(c.get('lifetime_value', 0)),
                        "days_inactive": c.get('days_inactive'),
                        "total_orders": c.get('total_orders')
                    }
                    for c in at_risk_customers[:5]  # Top 5
                ]
            }
        )
        
        self._log_insight_detected(company_id, insight)
        
        return insight