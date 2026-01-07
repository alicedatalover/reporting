# app/core/recommendations/generator.py
"""
Générateur de recommandations.

Orchestre la génération de recommandations via Gemini avec fallback
sous forme de liste prête pour Telegram.
"""

from typing import List, Optional
import logging

from app.domain.models import KPIData, KPIComparison, InsightModel
from app.infrastructure.external.gemini_client import GeminiClient
from app.core.recommendations.prompts import PromptBuilder
from app.config import settings

logger = logging.getLogger(__name__)

class RecommendationsGenerator:
    """
    Générateur de recommandations intelligentes.
    """
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client
        self.prompt_builder = PromptBuilder()
        self.use_llm = settings.ENABLE_LLM_RECOMMENDATIONS and settings.GOOGLE_API_KEY
        
        if not self.use_llm:
            logger.warning("LLM recommendations disabled",
                           extra={"enable_llm": settings.ENABLE_LLM_RECOMMENDATIONS,
                                  "has_api_key": bool(settings.GOOGLE_API_KEY)})
    
    async def generate(
        self,
        company_name: str,
        period_name: str,
        period_range: str,
        kpis: KPIData,
        kpis_comparison: KPIComparison,
        insights: List[InsightModel]
    ) -> str:
        """
        Génère 2-3 recommandations actionnables prêtes pour Telegram.
        """
        logger.info("Generating recommendations",
                    extra={"company": company_name, "use_llm": self.use_llm, "insights_count": len(insights)})
        
        if self.use_llm and self.gemini_client:
            try:
                recs = await self._generate_with_gemini(
                    company_name, period_name, period_range, kpis, kpis_comparison, insights
                )
                if recs and len(recs.strip()) > 20:
                    return recs
            except Exception as e:
                logger.error("Gemini generation failed", extra={"company": company_name, "error": str(e)}, exc_info=True)
        
        # fallback
        return self._generate_fallback(kpis, kpis_comparison, insights)
    
    async def _generate_with_gemini(
        self,
        company_name: str,
        period_name: str,
        period_range: str,
        kpis: KPIData,
        kpis_comparison: KPIComparison,
        insights: List[InsightModel]
    ) -> str:
        prompt = self.prompt_builder.build_recommendations_prompt(
            company_name, period_name, period_range, kpis, kpis_comparison, insights
        )
        recommendations = await self.gemini_client.generate_recommendations(
            prompt=prompt, max_tokens=settings.GEMINI_MAX_TOKENS, temperature=settings.GEMINI_TEMPERATURE
        )
        return self._clean_recommendations(recommendations)

    @staticmethod
    def _clean_recommendations(text: str) -> str:
        if not text: return ""
        for c in ["**", "*", "#"]: text = text.replace(c, "")
        for prefix in ["Voici mes recommandations :", "Recommandations :", "Mes recommandations :", "Je recommande :", "Je vous recommande :"]:
            if text.strip().startswith(prefix): text = text.replace(prefix, "", 1)
        text = " ".join(text.split())
        # S'assurer que chaque recommandation commence par "-"
        lines = [l.strip() if l.strip().startswith("-") else f"- {l.strip()}" for l in text.split("\n") if l.strip()]
        return "\n".join(lines)


    def _generate_fallback(self, kpis, comp, insights):
        """
        Fallback simple si Gemini échoue.
        """
        rec = []

        if kpis.net_result < 0:
            rec.append(
                "- Réduisez immédiatement vos dépenses de 15 à 20% en ciblant les fournisseurs les plus coûteux."
            )

        if comp.revenue_variation < -10:
            rec.append(
                "- Lancer une promotion clients existants cette semaine peut compenser la baisse de ventes."
            )

        if kpis.returning_customers < kpis.new_customers:
            rec.append(
                "- Mettez en place une offre fidélité (ex : -10% sur le 3e achat) pour augmenter les visites répétées."
            )

        if not rec:
            rec.append(
                "- Continuez vos efforts actuels et surveillez vos indicateurs chaque semaine."
            )

        return "\n".join(rec[:3])
