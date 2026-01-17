"""
Test qui reproduit EXACTEMENT le flux de l'endpoint /api/v1/reports/generate
pour voir où Gemini est appelé et pourquoi on obtient du fallback.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.kpi import calculate_kpis, compare_kpis, get_last_year_comparison
from app.core.insights import extract_all_insights
from app.core.recommendations import generate_recommendations
from app.core.database import get_company_info, init_database
from datetime import date
import logging

# Activer TOUS les logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:%(name)s:%(message)s'
)


async def test_full_flow():
    """Test du flux complet comme dans l'endpoint."""

    print("=" * 70)
    print("TEST FLUX COMPLET (comme endpoint /reports/generate)")
    print("=" * 70)
    print()

    init_database()

    # Utiliser les mêmes données que dans vos tests
    company_id = "01hjt9qsj7b039ww1nyrn9kg5t"
    start_date = date(2025, 6, 9)
    end_date = date(2025, 6, 15)
    period_range = "semaine du 9 au 15 juin"

    print(f"📊 Test pour:")
    print(f"   Company ID: {company_id}")
    print(f"   Période: {start_date} → {end_date}")
    print()

    # Récupérer infos entreprise
    print("1️⃣ Récupération infos entreprise...")
    company = await get_company_info(company_id)
    print(f"   ✓ {company['name']}")
    print()

    # Calculer KPIs
    print("2️⃣ Calcul des KPIs...")
    kpis = await calculate_kpis(company_id, start_date, end_date)
    print(f"   ✓ CA: {int(kpis.revenue):,} FCFA")
    print(f"   ✓ Ventes: {kpis.orders_count}")
    print()

    # Comparer
    print("3️⃣ Comparaison période précédente...")
    kpis_comparison = await compare_kpis(company_id, start_date, end_date, "weekly")
    print(f"   ✓ Évolution CA: {kpis_comparison.revenue_evolution:+.1f}%")
    print()

    # Insights
    print("4️⃣ Extraction insights...")
    insights = await extract_all_insights(company_id, start_date, end_date)
    print(f"   ✓ {len(insights)} insight(s) détecté(s)")
    for insight in insights:
        print(f"     - {insight.message[:60]}...")
    print()

    # Comparaison année passée
    print("5️⃣ Comparaison année passée...")
    last_year_kpis = await get_last_year_comparison(company_id, start_date, end_date)
    print(f"   ✓ Année dernière: {last_year_kpis.orders_count if last_year_kpis else 0} ventes")
    print()

    # CRITIQUE : Générer recommandations (c'est ici que ça bloque)
    print("6️⃣ Génération recommandations Gemini...")
    print()
    print("=" * 70)
    print("LOGS GEMINI (vérifiez les erreurs ci-dessous):")
    print("=" * 70)
    print()

    try:
        recommendations = await generate_recommendations(
            company_name=company['name'],
            period_range=period_range,
            kpis=kpis,
            kpis_comparison=kpis_comparison,
            insights=insights,
            last_year_kpis=last_year_kpis
        )

        print()
        print("=" * 70)
        print("RECOMMANDATIONS GÉNÉRÉES:")
        print("=" * 70)
        print(recommendations)
        print("=" * 70)
        print()

        # Vérifier si c'est du fallback
        if "Capitalisez sur cette belle dynamique" in recommendations or \
           "Réapprovisionnez en urgence vos produits" in recommendations:
            print("❌ FALLBACK DÉTECTÉ !")
            print()
            print("Les recommandations sont génériques, pas de Gemini.")
            print("Vérifiez les logs ci-dessus pour voir pourquoi Gemini a échoué.")
        else:
            print("✅ GEMINI UTILISÉ !")
            print()
            print("Les recommandations sont personnalisées par Gemini.")

    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_full_flow())
