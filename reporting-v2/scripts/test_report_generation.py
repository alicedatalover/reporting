"""
Script de test pour générer et envoyer un rapport avec les données existantes.
Utilise juillet 2024 comme période de test car c'est la dernière période avec des données.
"""
import asyncio
import sys
import json
sys.path.insert(0, '/app')

from app.core.database import execute_query, init_database
from app.core.kpi import calculate_period_dates, format_period_range, calculate_kpis, compare_kpis
from app.core.insights import extract_all_insights
from app.core.recommendations import generate_recommendations, get_last_year_comparison
from app.notifications.telegram import send_telegram_message
from app.notifications.whatsapp import format_whatsapp_message
from datetime import datetime, date


async def main():
    print("=" * 70)
    print("TEST DE GÉNÉRATION DE RAPPORT - JUILLET 2024")
    print("=" * 70)
    print()

    init_database()

    # 1. Trouver une entreprise active
    print("📋 Recherche d'une entreprise avec des données...")
    companies = await execute_query("""
        SELECT DISTINCT c.id, c.name, COUNT(o.id) as order_count
        FROM companies c
        JOIN orders o ON c.id = o.company_id
        WHERE c.deleted_at IS NULL
          AND o.deleted_at IS NULL
          AND DATE(o.created_at) BETWEEN '2024-07-01' AND '2024-07-31'
        GROUP BY c.id, c.name
        ORDER BY order_count DESC
        LIMIT 5
    """)

    if not companies:
        print("❌ Aucune entreprise avec des commandes en juillet 2024")
        return

    print(f"\n✓ Trouvé {len(companies)} entreprise(s) avec des données en juillet 2024:")
    for idx, company in enumerate(companies, 1):
        print(f"  {idx}. {company['name']} - {company['order_count']} commandes")

    # Utiliser la première entreprise
    selected_company = companies[0]
    company_id = selected_company['id']
    company_name = selected_company['name']

    print(f"\n🏢 Entreprise sélectionnée: {company_name}")
    print(f"   ID: {company_id}")
    print()

    # 2. Définir la période (semaine du 15-21 juillet 2024)
    end_date = date(2024, 7, 21)
    start_date = date(2024, 7, 15)
    period_range = format_period_range(start_date, end_date, "weekly")

    print(f"📅 Période du rapport: {period_range}")
    print(f"   Du {start_date} au {end_date}")
    print()

    # 3. Calculer les KPIs
    print("📊 Calcul des KPIs...")
    kpis = await calculate_kpis(company_id, start_date, end_date)
    print(f"   ✓ CA: {int(kpis.revenue):,} FCFA")
    print(f"   ✓ Ventes: {kpis.orders_count}")
    print(f"   ✓ Panier moyen: {int(kpis.avg_basket):,} FCFA")
    if kpis.top_products:
        print(f"   ✓ Top produit: {kpis.top_products[0]['name']}")
    print()

    # 4. Comparer avec période précédente
    print("📈 Comparaison avec période précédente...")
    kpis_comparison = await compare_kpis(company_id, start_date, end_date, "weekly")
    print(f"   ✓ Évolution CA: {kpis_comparison.revenue_evolution:+.1f}%")
    print(f"   ✓ Évolution ventes: {kpis_comparison.orders_evolution:+.1f}%")
    print()

    # 5. Extraire les insights
    print("💡 Extraction des insights...")
    insights = await extract_all_insights(company_id, start_date, end_date)
    print(f"   ✓ {len(insights)} insight(s) détecté(s)")
    for insight in insights:
        print(f"     - {insight.message}")
    print()

    # 6. Générer les recommandations Gemini
    print("🤖 Génération des recommandations Gemini...")
    last_year_kpis = await get_last_year_comparison(company_id, start_date, end_date)
    recommendations = await generate_recommendations(
        company_name=company_name,
        period_range=period_range,
        kpis=kpis,
        kpis_comparison=kpis_comparison,
        insights=insights,
        last_year_kpis=last_year_kpis
    )
    print(f"   ✓ Recommandations générées:")
    print(f"     {recommendations[:200]}...")
    print()

    # 7. Formater le message
    print("📝 Formatage du message...")
    message = format_whatsapp_message(
        company_name=company_name,
        period_range=period_range,
        kpis=kpis,
        kpis_comparison=kpis_comparison,
        insights=insights,
        recommendations=recommendations
    )

    print("=" * 70)
    print("MESSAGE FORMATÉ:")
    print("=" * 70)
    print(message)
    print("=" * 70)
    print()

    # 8. Demander confirmation pour envoi Telegram
    print("📱 ENVOI VIA TELEGRAM")
    print("   Chat ID: 1498227036")
    print()

    # Envoyer automatiquement (en test)
    print("📤 Envoi en cours...")
    success = await send_telegram_message("1498227036", message)

    if success:
        print("   ✅ MESSAGE ENVOYÉ AVEC SUCCÈS!")
        print("   Vérifiez votre Telegram (@alicedatalover)")
    else:
        print("   ❌ Échec de l'envoi")
        print("   Vérifiez les logs pour plus de détails")

    print()
    print("=" * 70)
    print("TEST TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
