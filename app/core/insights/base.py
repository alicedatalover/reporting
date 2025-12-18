# app/core/insights/base.py
"""
Interface de base pour les Insight Miners.

Définit le contrat que tous les miners doivent respecter.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, Dict, Any
import logging

from app.domain.models import InsightModel, KPIData

logger = logging.getLogger(__name__)


class AbstractInsightMiner(ABC):
    """
    Interface abstraite pour les Insight Miners.
    
    Un Insight Miner analyse les données d'une entreprise pour
    détecter des patterns, anomalies ou opportunités spécifiques.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du miner (pour logging)"""
        pass
    
    @abstractmethod
    async def mine(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[InsightModel]:
        """
        Analyse les données et extrait un insight.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début de la période
            end_date: Date de fin de la période
            context: Contexte additionnel (KPIs pré-calculés, etc.)
        
        Returns:
            InsightModel si un insight est détecté, None sinon
        
        Example:
            >>> miner = StockAlertMiner(stock_repo)
            >>> insight = await miner.mine("company_123", start, end)
            >>> if insight:
            ...     print(f"{insight.title}: {insight.description}")
        """
        pass
    
    def _log_insight_detected(
        self,
        company_id: str,
        insight: InsightModel
    ) -> None:
        """
        Log la détection d'un insight.
        
        Args:
            company_id: ID de l'entreprise
            insight: Insight détecté
        """
        logger.info(
            f"Insight detected: {self.name}",
            extra={
                "company_id": company_id,
                "insight_type": insight.type.value,
                "priority": insight.priority,
                "financial_impact": float(insight.financial_impact) if insight.financial_impact else None
            }
        )
    
    def _log_no_insight(self, company_id: str, reason: str = "No pattern detected") -> None:
        """
        Log l'absence d'insight.
        
        Args:
            company_id: ID de l'entreprise
            reason: Raison de l'absence d'insight
        """
        logger.debug(
            f"No insight from {self.name}",
            extra={
                "company_id": company_id,
                "reason": reason
            }
        )