# app/core/insights/miners/__init__.py
"""
Insight Miners disponibles.
"""

from app.core.insights.miners.stock_alert import StockAlertMiner
from app.core.insights.miners.churn_risk import ChurnRiskMiner
from app.core.insights.miners.seasonality import SeasonalityMiner
from app.core.insights.miners.profit_margin import ProfitMarginMiner

__all__ = [
    "StockAlertMiner",
    "ChurnRiskMiner",
    "SeasonalityMiner",
    "ProfitMarginMiner",
]