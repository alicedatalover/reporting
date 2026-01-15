"""
Génération de recommandations via Gemini AI.
CRITIQUE : Prompt optimisé pour ne PAS répéter les KPIs mais synthétiser en actions.
"""

import google.generativeai as genai
from typing import Optional, List
import logging

from app.models import KPIData, KPIComparison, Insight
from app.config import settings

logger = logging.getLogger(__name__)

# Initialiser Gemini
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


async def generate_recommendations(
    company_name: str,
    period_range: str,
    kpis: KPIData,
    kpis_comparison: KPIComparison,
    insights: List[Insight],
    last_year_kpis: Optional[KPIData] = None
) -> str:
    """
    Génère des recommandations personnalisées via Gemini AI.

    Args:
        company_name: Nom de l'entreprise
        period_range: Période du rapport (ex: "semaine du 13 au 19 janvier")
        kpis: KPIs de la période
        kpis_comparison: Comparaison avec période précédente
        insights: Insights détectés
        last_year_kpis: KPIs de l'année dernière (optionnel)

    Returns:
        Recommandations en texte brut (4 phrases max)

    Example:
        >>> reco = await generate_recommendations("Kerma", "semaine du 13 au 19 janvier", ...)
        >>> print(reco)
        "Réapprovisionnez en urgence vos 3 produits en rupture..."
    """
    if not settings.GOOGLE_API_KEY:
        logger.warning("Gemini API key not configured, using fallback")
        return generate_fallback_recommendations(
            company_name, kpis, kpis_comparison, insights
        )

    # Construire le contexte pour Gemini
    context = _build_context(
        company_name,
        period_range,
        kpis,
        kpis_comparison,
        insights,
        last_year_kpis
    )

    # Prompt optimisé
    prompt = f"""Tu es un conseiller business expert pour les PME en Afrique.

CONTEXTE :
{context}

INSTRUCTIONS STRICTES :
1. NE RÉPÈTE PAS les chiffres déjà mentionnés dans le contexte
2. SYNTHÉTISE les insights en recommandations actionnables
3. Sois DIRECT et PRÉCIS (pas de formules creuses)
4. Maximum 4 phrases courtes
5. Utilise le "vous" pour parler à l'entreprise
6. Chaque phrase = 1 action concrète à faire

FORMAT ATTENDU :
Une seule phrase par recommandation. Pas de listes à puces, pas de numéros.

GÉNÈRE LES RECOMMANDATIONS :"""

    try:
        # Appeler Gemini avec retry
        for attempt in range(3):
            try:
                model = genai.GenerativeModel(settings.GEMINI_MODEL)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        max_output_tokens=settings.GEMINI_MAX_TOKENS,
                        temperature=settings.GEMINI_TEMPERATURE,
                    )
                )

                recommendations = response.text.strip()

                logger.info(
                    "Gemini recommendations generated",
                    extra={
                        "company_name": company_name,
                        "recommendations_length": len(recommendations)
                    }
                )

                return recommendations

            except Exception as e:
                logger.warning(
                    f"Gemini API attempt {attempt + 1} failed: {e}",
                    extra={"attempt": attempt + 1}
                )
                if attempt == 2:
                    raise

    except Exception as e:
        logger.error(
            f"Gemini API failed after 3 attempts: {e}",
            extra={"company_name": company_name},
            exc_info=True
        )
        # Fallback
        return generate_fallback_recommendations(
            company_name, kpis, kpis_comparison, insights
        )


def _build_context(
    company_name: str,
    period_range: str,
    kpis: KPIData,
    kpis_comparison: KPIComparison,
    insights: List[Insight],
    last_year_kpis: Optional[KPIData]
) -> str:
    """Construit le contexte structuré pour Gemini."""

    # Formater les évolutions
    revenue_trend = "en hausse" if kpis_comparison.revenue_evolution > 0 else "en baisse"
    orders_trend = "en hausse" if kpis_comparison.orders_evolution > 0 else "en baisse"

    context = f"""Entreprise : {company_name}
Période : {period_range}

PERFORMANCES :
- Chiffre d'affaires : {int(kpis.revenue):,} FCFA ({kpis_comparison.revenue_evolution:+.1f}% vs période précédente) - {revenue_trend}
- Nombre de ventes : {kpis.orders_count} ({kpis_comparison.orders_evolution:+.1f}%) - {orders_trend}
- Panier moyen : {int(kpis.avg_basket):,} FCFA ({kpis_comparison.avg_basket_evolution:+.1f}%)
"""

    # Ajouter top produits
    if kpis.top_products:
        top_products_str = ", ".join([f"{p['name']} ({p['sales_count']} ventes)" for p in kpis.top_products])
        context += f"- Top produits : {top_products_str}\n"

    # Ajouter comparaison année précédente si disponible
    if last_year_kpis and last_year_kpis.orders_count > 0:
        year_evolution = ((kpis.revenue - last_year_kpis.revenue) / last_year_kpis.revenue) * 100
        context += f"- Comparaison année dernière : {year_evolution:+.1f}% de CA vs même période 2025\n"

    # Ajouter insights
    if insights:
        context += "\nINSIGHTS DÉTECTÉS :\n"
        for insight in insights:
            context += f"- {insight.message}\n"

    return context


def generate_fallback_recommendations(
    company_name: str,
    kpis: KPIData,
    kpis_comparison: KPIComparison,
    insights: List[Insight]
) -> str:
    """
    Génère des recommandations basiques si Gemini échoue.
    Utilise des templates basés sur les insights.
    """
    recommendations = []

    # Recommandation basée sur évolution CA
    if kpis_comparison.revenue_evolution < -10:
        recommendations.append(
            "Analysez la baisse de votre chiffre d'affaires en identifiant les jours/produits moins performants et lancez des actions promotionnelles ciblées."
        )
    elif kpis_comparison.revenue_evolution > 15:
        recommendations.append(
            "Capitalisez sur cette belle dynamique en augmentant vos stocks des produits stars et en communiquant sur vos offres."
        )

    # Recommandations basées sur les insights
    for insight in insights[:2]:
        if insight.type.value == "stock_alert":
            recommendations.append(
                "Réapprovisionnez en urgence vos produits en rupture de stock pour ne pas perdre de ventes."
            )
        elif insight.type.value == "churn_risk":
            count = insight.data.get("customers_count", 0)
            recommendations.append(
                f"Relancez vos {count} clients inactifs avec une offre spéciale pour les réactiver avant qu'ils ne partent définitivement."
            )
        elif insight.type.value == "seasonality":
            if "milieu de semaine" in insight.message:
                recommendations.append(
                    "Lancez une promotion flash en milieu de semaine pour relancer l'activité sur ces jours creux."
                )

    # Si pas assez de recommandations, ajouter des génériques
    if len(recommendations) < 2:
        if kpis.top_products:
            top_product = kpis.top_products[0]["name"]
            recommendations.append(
                f"Mettez en avant {top_product} dans vos communications car c'est votre produit phare."
            )

    # Limiter à 4 max
    return " ".join(recommendations[:4])


async def test_gemini_connection() -> bool:
    """
    Teste la connexion à l'API Gemini.

    Returns:
        True si connexion OK
    """
    if not settings.GOOGLE_API_KEY:
        logger.warning("Gemini API key not configured")
        return False

    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(
            "Réponds juste 'OK'",
            generation_config=genai.GenerationConfig(max_output_tokens=10)
        )
        return "OK" in response.text.upper()
    except Exception as e:
        logger.error(f"Gemini connection test failed: {e}")
        return False
