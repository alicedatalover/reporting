"""
Test pour voir pourquoi Gemini n'est pas utilisé et on tombe sur fallback.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.recommendations import generate_recommendations
from app.models import KPIData, KPIComparison, Insight, InsightType
from app.config import settings
import logging

# Activer les logs
logging.basicConfig(level=logging.INFO)


async def test_gemini_recommendations():
    """Test des recommandations Gemini avec données réelles."""

    print("=" * 70)
    print("TEST GEMINI RECOMMENDATIONS")
    print("=" * 70)
    print()

    print(f"📊 Configuration Gemini:")
    print(f"   Modèle: {settings.GEMINI_MODEL}")
    print(f"   Max tokens: {settings.GEMINI_MAX_TOKENS}")
    print(f"   API Key: {'✓ Configuré' if settings.GOOGLE_API_KEY else '✗ Manquant'}")
    print()

    # Données de test
    kpis = KPIData(
        revenue=3350275.0,
        orders_count=401,
        avg_basket=8354.80,
        unique_customers=374,
        top_products=[]
    )

    kpis_comparison = KPIComparison(
        revenue_evolution=18.7,
        orders_evolution=27.7,
        avg_basket_evolution=-7.0
    )

    insights = [
        Insight(
            type=InsightType.STOCK_ALERT,
            message="5 produits risquent la rupture de stock",
            severity=5,
            data={}
        )
    ]

    print("📤 Génération des recommandations Gemini...")
    print()

    try:
        recommendations = await generate_recommendations(
            company_name="Les Délices de Milly",
            period_range="semaine du 9 au 15 juin",
            kpis=kpis,
            kpis_comparison=kpis_comparison,
            insights=insights,
            last_year_kpis=None
        )

        print("=" * 70)
        print("RECOMMANDATIONS GÉNÉRÉES:")
        print("=" * 70)
        print(recommendations)
        print("=" * 70)
        print()

        # Vérifier si c'est du fallback ou du Gemini
        if "Capitalisez sur cette belle dynamique" in recommendations:
            print("⚠️  ALERTE : Ce sont les recommandations de FALLBACK !")
            print()
            print("Raisons possibles :")
            print("1. finish_reason = MAX_TOKENS (vérifiez les logs ci-dessus)")
            print("2. finish_reason ≠ STOP (filtre sécurité Gemini)")
            print("3. Exception levée par Gemini API")
            print()
            print("Vérifiez les logs INFO ci-dessus pour voir le finish_reason.")
        else:
            print("✅ Ce sont bien les recommandations GEMINI !")

    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_gemini_recommendations())
