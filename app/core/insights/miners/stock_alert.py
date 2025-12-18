# app/core/insights/miners/stock_alert.py
"""
Insight Miner pour les alertes de stock.

Détecte les produits en rupture ou en stock faible.
"""

from datetime import date
from typing import Optional, Dict, Any
from decimal import Decimal

from app.core.insights.base import AbstractInsightMiner
from app.domain.models import InsightModel
from app.domain.enums import InsightType
from app.infrastructure.repositories.stock_repo import StockRepository


class StockAlertMiner(AbstractInsightMiner):
    """
    Détecte les problèmes de stock.
    
    Priorité:
    - 5/5 si stock = 0 (rupture critique)
    - 3/5 si stock faible mais non nul
    """
    
    def __init__(self, stock_repo: StockRepository):
        """
        Initialise le miner.
        
        Args:
            stock_repo: Repository des stocks
        """
        self.stock_repo = stock_repo
    
    @property
    def name(self) -> str:
        return "StockAlertMiner"
    
    async def mine(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[InsightModel]:
        """
        Détecte les alertes de stock.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début (non utilisée pour stock)
            end_date: Date de fin (non utilisée pour stock)
            context: Contexte (optionnel)
        
        Returns:
            InsightModel si alertes détectées, None sinon
        """
        
        # Récupérer les alertes de stock
        alerts = await self.stock_repo.get_stock_alerts(company_id, limit=10)
        
        if not alerts:
            self._log_no_insight(company_id, "No stock alerts")
            return None
        
        # Compter les ruptures critiques (stock = 0)
        critical_alerts = [a for a in alerts if a['stock_total'] == 0]
        
        # Déterminer la priorité
        if critical_alerts:
            priority = 5  # Critique
            title = "🚨 Rupture de Stock"
            
            if len(critical_alerts) == 1:
                product_name = critical_alerts[0]['product_name']
                description = f"'{product_name}' est en rupture de stock totale."
            else:
                description = f"{len(critical_alerts)} produits sont en rupture de stock totale."
        else:
            priority = 3  # Moyenne
            title = "📉 Stock Faible"
            
            # Prendre le premier produit comme exemple
            first_alert = alerts[0]
            product_name = first_alert['product_name']
            stock_total = first_alert['stock_total']
            quantity_alert = first_alert['quantity_alert']
            
            description = f"'{product_name}' : {stock_total:.0f} unités restantes (seuil: {quantity_alert:.0f})"
        
        # Estimer l'impact financier (perte potentielle de ventes)
        # Hypothèse: 7 jours sans stock = perte de X ventes
        financial_impact = None
        if context and 'total_revenue' in context and 'total_sales' in context:
            avg_revenue_per_sale = (
                Decimal(context['total_revenue']) / Decimal(context['total_sales'])
                if context['total_sales'] > 0
                else Decimal("0")
            )
            # Estimer 5 ventes perdues par produit en rupture
            estimated_lost_sales = len(critical_alerts) * 5
            financial_impact = avg_revenue_per_sale * Decimal(estimated_lost_sales)
        
        insight = InsightModel(
            type=InsightType.STOCK_ALERT,
            title=title,
            description=description,
            priority=priority,
            financial_impact=financial_impact,
            actionable=True,
            metadata={
                "total_alerts": len(alerts),
                "critical_alerts": len(critical_alerts),
                "products": [
                    {
                        "name": a['product_name'],
                        "stock": float(a['stock_total']),
                        "alert_level": a['alert_level']
                    }
                    for a in alerts[:5]  # Top 5
                ]
            }
        )
        
        self._log_insight_detected(company_id, insight)
        
        return insight