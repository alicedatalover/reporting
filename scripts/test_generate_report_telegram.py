# -*- coding: utf-8 -*-
# scripts/test_generate_report_telegram.py
"""
Script pour tester la generation et l'envoi d'un rapport via Telegram.

Ce script :
- Recupere le vrai nom de l'entreprise depuis la DB (avec fallback)
- Genere des recommandations avec Gemini AI (si configure)
- Utilise le formatter professionnel existant
- Envoie un rapport realiste via Telegram

Usage:
    python scripts/test_generate_report_telegram.py --company-id 1 --chat-id 123456789 --period weekly
    python scripts/test_generate_report_telegram.py --company-id 1 --chat-id 123456789 --period monthly --use-test-data
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.infrastructure.external import TelegramClient, GeminiClient
from app.infrastructure.database.connection import get_db_session, init_database
from app.infrastructure.repositories.company_repo import CompanyRepository
from app.utils.formatters import WhatsAppFormatter
from app.core.recommendations.generator import RecommendationsGenerator
from app.domain.models import KPIData, KPIComparison, InsightModel
from app.services.report_service import ReportService
from app.domain.enums import ReportFrequency
from datetime import date


async def test_generate_and_send_report(
    company_id: str,
    chat_id: str,
    period: str,
    use_test_data: bool = False,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Teste la generation et l'envoi d'un rapport via Telegram.

    Args:
        company_id: ID de l'entreprise
        chat_id: ID du chat Telegram
        period: Periode du rapport (weekly, monthly, quarterly)
        use_test_data: Si True, utilise des donnees fictives sans DB
        start_date: Date de debut optionnelle (YYYY-MM-DD)
        end_date: Date de fin optionnelle (YYYY-MM-DD)
    """

    print("=" * 80)
    print("TEST GENERATION ET ENVOI RAPPORT TELEGRAM")
    print("=" * 80)
    print(f"Company ID: {company_id}")
    print(f"Chat ID: {chat_id}")
    print(f"Periode: {period}")
    print(f"Mode: {'Test (donnees fictives)' if use_test_data else 'Production (vraies donnees)'}")
    print("=" * 80)

    # Verifier la configuration Telegram
    if not settings.TELEGRAM_BOT_TOKEN:
        print("\nERREUR: TELEGRAM_BOT_TOKEN non configure dans .env")
        print("Ajoutez votre token dans le fichier .env :")
        print("TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        return

    try:
        # Initialiser le client Telegram
        telegram_client = TelegramClient(settings)

        # Test connexion
        print("\n1. Test de connexion Telegram...")
        bot_info = await telegram_client.get_bot_info()
        if bot_info:
            print(f"   OK: Bot connecte -> @{bot_info.get('username')}")
        else:
            print("   ERREUR: Impossible de se connecter au bot Telegram")
            return

        # Recuperer le nom de l'entreprise
        print(f"\n2. Recuperation des infos de l'entreprise (ID={company_id})...")
        company_name = await _get_company_name(company_id, use_test_data)
        print(f"   OK: Entreprise -> {company_name}")

        # Generer le rapport
        print(f"\n3. Generation du rapport {period}...")

        if use_test_data:
            # Mode test : donnees fictives
            report_data = await _generate_report_data(
                company_id=company_id,
                company_name=company_name,
                period=period,
                use_test_data=True
            )
        else:
            # Mode production : VRAIS services avec DB
            report_data = await _generate_real_report(
                company_id=company_id,
                period=period,
                end_date=end_date
            )

        print(f"   OK: Rapport genere")
        print(f"      - Entreprise: {report_data.get('company_name', company_name)}")
        print(f"      - CA: {report_data['kpis']['total_revenue']:,.0f} XAF")
        print(f"      - Ventes: {report_data['kpis']['total_sales']}")
        print(f"      - Clients: {report_data['kpis']['new_customers']} nouveaux")
        print(f"      - Recommandations: {'Oui' if report_data.get('recommendations') else 'Non'}")

        # Formater le message avec le formatter professionnel
        print("\n4. Formatage du message pour Telegram...")
        formatter = WhatsAppFormatter()
        messages = formatter.format_report(report_data)

        if isinstance(messages, list):
            message = messages[0]  # Premier message si splitte
            total_length = sum(len(m) for m in messages)
            print(f"   OK: Message formate ({total_length} caracteres, {len(messages)} partie(s))")
        else:
            message = messages
            print(f"   OK: Message formate ({len(message)} caracteres)")

        # Afficher un apercu du message
        print("\n   Apercu du message:")
        print("   " + "-" * 76)
        message_lines = message.split('\n')
        preview_lines = message_lines[:15]
        for line in preview_lines:
            print(f"   {line}")
        if len(message_lines) > 15:
            remaining_lines = len(message_lines) - 15
            print(f"   ... ({remaining_lines} lignes supplementaires)")
        print("   " + "-" * 76)

        # Envoyer le rapport via Telegram
        print(f"\n5. Envoi du rapport au chat {chat_id}...")
        success = await telegram_client.send_message(chat_id, message)

        if success:
            print(f"   OK: Rapport envoye avec succes!")
            print(f"\n   Verifiez votre Telegram pour voir le message.")
        else:
            print(f"   ERREUR: Echec de l'envoi")
            print(f"   Verifiez que le chat_id est correct et que le bot a acces au chat")

        print("\n" + "=" * 80)
        print("TEST TERMINE")
        print("=" * 80)

    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()


async def _generate_real_report(
    company_id: str,
    period: str,
    end_date: Optional[date] = None
) -> dict:
    """
    Genere un rapport avec les VRAIS services (DB + Gemini).

    Args:
        company_id: ID de l'entreprise
        period: Periode du rapport
        end_date: Date de fin optionnelle

    Returns:
        Rapport complet avec vraies donnees
    """
    try:
        # Initialiser la DB
        init_database()

        # Convertir la periode en enum
        frequency_map = {
            'weekly': ReportFrequency.WEEKLY,
            'monthly': ReportFrequency.MONTHLY,
            'quarterly': ReportFrequency.QUARTERLY
        }
        frequency = frequency_map.get(period, ReportFrequency.MONTHLY)

        # Utiliser le generateur de session
        async for session in get_db_session():
            # Initialiser le ReportService avec la session
            report_service = ReportService(session)

            # Generer le rapport avec le VRAI service
            print(f"   INFO: Utilisation du ReportService avec vraies donnees DB...")
            report_data = await report_service.generate_report(
                company_id=company_id,
                frequency=frequency,
                end_date=end_date
            )

            # Convertir en dict pour compatibilite avec le formatter
            return report_data.model_dump()

    except Exception as e:
        print(f"   ERREUR: Impossible de generer le rapport reel ({e})")
        raise


async def _get_company_name(company_id: str, use_test_data: bool) -> str:
    """
    Recupere le nom de l'entreprise depuis la DB.

    Args:
        company_id: ID de l'entreprise
        use_test_data: Si True, retourne un nom fictif

    Returns:
        Nom de l'entreprise
    """
    if use_test_data:
        return f"Entreprise Demo {company_id}"

    try:
        # Initialiser la DB si necessaire
        init_database()

        # Utiliser le generateur de session
        async for session in get_db_session():
            company_repo = CompanyRepository(session)
            company = await company_repo.get_by_id(company_id)

            if company and company.get('name'):
                return company['name']
            else:
                print(f"   AVERTISSEMENT: Entreprise {company_id} non trouvee en DB")
                return f"Entreprise {company_id}"

    except Exception as e:
        print(f"   AVERTISSEMENT: Impossible de se connecter a la DB ({e})")
        print(f"   Utilisation d'un nom fictif")
        return f"Entreprise {company_id}"


async def _generate_report_data(
    company_id: str,
    company_name: str,
    period: str,
    use_test_data: bool
) -> dict:
    """
    Genere les donnees du rapport avec KPIs et recommandations.

    Args:
        company_id: ID de l'entreprise
        company_name: Nom de l'entreprise
        period: Periode du rapport
        use_test_data: Si True, utilise des donnees fictives

    Returns:
        Dictionnaire avec toutes les donnees du rapport
    """
    # Calculer les dates
    end_date = datetime.now()
    if period == "weekly":
        start_date = end_date - timedelta(days=7)
        period_name = "Hebdomadaire"
    elif period == "monthly":
        start_date = end_date - timedelta(days=30)
        period_name = "Mensuel"
    elif period == "quarterly":
        start_date = end_date - timedelta(days=90)
        period_name = "Trimestriel"
    else:
        start_date = end_date - timedelta(days=7)
        period_name = "Hebdomadaire"

    period_range = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

    # Generer des KPIs realistes
    kpis = _generate_test_kpis(period)
    kpis_comparison = _generate_test_comparison(kpis)

    # Generer des insights
    insights = _generate_test_insights(kpis)

    # Generer des recommandations avec Gemini (si configure)
    recommendations = await _generate_recommendations(
        company_name=company_name,
        period_name=period_name,
        period_range=period_range,
        kpis=kpis,
        kpis_comparison=kpis_comparison,
        insights=insights
    )

    return {
        'company_id': company_id,
        'company_name': company_name,
        'period_name': period_name,
        'period_range': period_range,
        'kpis': kpis,
        'kpis_comparison': kpis_comparison,
        'insights': insights,
        'recommendations': recommendations
    }


def _generate_test_kpis(period: str) -> dict:
    """Genere des KPIs de test realistes selon la periode."""

    base_multiplier = {
        'weekly': 1,
        'monthly': 4,
        'quarterly': 12
    }.get(period, 1)

    return {
        'total_revenue': 5000000 * base_multiplier,
        'total_sales': 45 * base_multiplier,
        'new_customers': 8 * base_multiplier,
        'returning_customers': 15 * base_multiplier,
        'stock_alerts_count': 3,
        'total_expenses': 4200000 * base_multiplier,
        'net_result': 800000 * base_multiplier
    }


def _generate_test_comparison(kpis: dict) -> dict:
    """Genere des comparaisons avec periode precedente."""

    return {
        'revenue_variation': 11.5,
        'sales_variation': 12.5,
        'returning_customers_variation': 7.0,
        'expenses_variation': 8.0
    }


def _generate_test_insights(kpis: dict) -> list:
    """Genere des insights de test."""

    insights = []

    # Insight sur les clients a risque
    if kpis.get('returning_customers', 0) < 20:
        insights.append({
            'type': 'churn_risk',
            'priority': 4,
            'message': '5 clients fideles inactifs depuis 30+ jours - Risque de perte',
            'details': {'at_risk_count': 5}
        })

    # Insight sur le stock
    if kpis.get('stock_alerts_count', 0) > 0:
        insights.append({
            'type': 'stock_alert',
            'priority': 3,
            'message': f"{kpis['stock_alerts_count']} produits en stock faible ou rupture",
            'details': {'alert_count': kpis['stock_alerts_count']}
        })

    # Insight sur la croissance
    insights.append({
        'type': 'positive_trend',
        'priority': 2,
        'message': 'Croissance du CA de +11.5% par rapport a la periode precedente',
        'details': {'growth': 11.5}
    })

    return insights


async def _generate_recommendations(
    company_name: str,
    period_name: str,
    period_range: str,
    kpis: dict,
    kpis_comparison: dict,
    insights: list
) -> Optional[str]:
    """
    Genere des recommandations avec Gemini AI.

    Returns:
        Recommandations formatees ou None
    """
    if not settings.GOOGLE_API_KEY or not settings.ENABLE_LLM_RECOMMENDATIONS:
        print("   INFO: Gemini non configure, utilisation de recommandations par defaut")
        return _generate_fallback_recommendations(kpis, insights)

    try:
        print("   INFO: Generation de recommandations avec Gemini AI...")

        # Initialiser Gemini
        gemini_client = GeminiClient(settings)

        # Creer des objets de domaine pour le generator
        kpis_data = KPIData(**kpis)
        kpis_comp = KPIComparison(**kpis_comparison)
        insights_models = [InsightModel(**insight) for insight in insights]

        # Generer avec le RecommendationsGenerator
        rec_generator = RecommendationsGenerator(gemini_client)
        recommendations = await rec_generator.generate(
            company_name=company_name,
            period_name=period_name,
            period_range=period_range,
            kpis=kpis_data,
            kpis_comparison=kpis_comp,
            insights=insights_models
        )

        if recommendations and len(recommendations.strip()) > 20:
            print("   OK: Recommandations generees par Gemini AI")
            return recommendations
        else:
            print("   INFO: Gemini a retourne une reponse vide, utilisation du fallback")
            return _generate_fallback_recommendations(kpis, insights)

    except Exception as e:
        print(f"   AVERTISSEMENT: Erreur Gemini ({e}), utilisation du fallback")
        return _generate_fallback_recommendations(kpis, insights)


def _generate_fallback_recommendations(kpis: dict, insights: list) -> str:
    """Genere des recommandations par defaut sans IA."""

    recs = []

    # Recommandation sur les clients
    if any(i.get('type') == 'churn_risk' for i in insights):
        recs.append("1. Relancer les clients inactifs avec une offre speciale ou un message personnalise")

    # Recommandation sur le stock
    if kpis.get('stock_alerts_count', 0) > 0:
        recs.append(f"2. Reapprovisionner les {kpis['stock_alerts_count']} produits en alerte stock")

    # Recommandation sur la croissance
    if kpis.get('total_revenue', 0) > 0:
        recs.append("3. Capitaliser sur la croissance actuelle en augmentant la visibilite marketing")

    if not recs:
        recs.append("1. Continuer a suivre les indicateurs cles pour identifier les opportunites")

    return "\n".join(recs)


async def main():
    parser = argparse.ArgumentParser(
        description="Teste la generation et l'envoi d'un rapport via Telegram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Rapport hebdomadaire avec vraies donnees DB
  python scripts/test_generate_report_telegram.py --company-id 1 --chat-id 123456789 --period weekly

  # Rapport mensuel avec donnees de test (sans DB)
  python scripts/test_generate_report_telegram.py --company-id 1 --chat-id 123456789 --period monthly --use-test-data

Configuration requise dans .env:
  TELEGRAM_BOT_TOKEN=votre_token_bot
  GOOGLE_API_KEY=votre_cle_gemini (optionnel, pour les recommandations IA)
        """
    )

    parser.add_argument(
        "--company-id",
        type=str,
        required=True,
        help="ID de l'entreprise"
    )

    parser.add_argument(
        "--chat-id",
        required=True,
        help="Chat ID Telegram"
    )

    parser.add_argument(
        "--period",
        choices=["weekly", "monthly", "quarterly"],
        default="weekly",
        help="Periode du rapport (defaut: weekly)"
    )

    parser.add_argument(
        "--use-test-data",
        action="store_true",
        help="Utiliser des donnees de test sans connexion DB"
    )

    parser.add_argument(
        "--start-date",
        help="Date de debut au format YYYY-MM-DD (ex: 2024-09-01)"
    )

    parser.add_argument(
        "--end-date",
        help="Date de fin au format YYYY-MM-DD (ex: 2024-09-30)"
    )

    args = parser.parse_args()

    # Parser les dates si fournie
    start_date_obj = None
    end_date_obj = None

    if args.end_date:
        try:
            end_date_obj = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"ERREUR: Format de date invalide pour end-date: {args.end_date}")
            print("Utilisez le format YYYY-MM-DD (ex: 2024-09-30)")
            return

    if args.start_date:
        try:
            start_date_obj = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"ERREUR: Format de date invalide pour start-date: {args.start_date}")
            print("Utilisez le format YYYY-MM-DD (ex: 2024-09-01)")
            return

    await test_generate_and_send_report(
        company_id=args.company_id,
        chat_id=args.chat_id,
        period=args.period,
        use_test_data=args.use_test_data,
        start_date=start_date_obj,
        end_date=end_date_obj
    )


if __name__ == "__main__":
    asyncio.run(main())
