# app/core/insights/__init__.py
"""
Module d'extraction d'insights.
"""

from app.core.insights.base import AbstractInsightMiner
from app.core.insights.selector import InsightSelector

__all__ = [
    "AbstractInsightMiner",
    "InsightSelector",
]