# app/core/recommendations/__init__.py
"""
Module de génération de recommandations.
"""

from app.core.recommendations.generator import RecommendationsGenerator
from app.core.recommendations.prompts import PromptBuilder

__all__ = [
    "RecommendationsGenerator",
    "PromptBuilder",
]