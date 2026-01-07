# scripts/test_generate_report_telegram.py
"""
Script pour tester la génération et l'envoi d'un rapport via Telegram.

Usage:
    python scripts/test_generate_report_telegram.py --company-id 1 --chat-id 123456789 --period weekly
    python scripts/test_generate_report_telegram.py --company-id 1 --chat-id 123456789 --period monthly
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.infrastructure.external import TelegramClient
from app.services.report_service import ReportService


async def test_generate_and_send_report(company_id: int, chat_id: str, period: str):
    """
    Teste la génération et l'envoi d'un rapport via Telegram.

    Args:
        company_id: ID de l'entreprise
        chat_id: ID du chat Telegram
        period: Période du rapport (weekly, monthly, quarterly)
    """

    print("=" * 80)
    print(f">ê TEST GÉNÉRATION ET ENVOI RAPPORT TELEGRAM")
    print("=" * 80)
    print(f"Company ID: {company_id}")
    print(f"Chat ID: {chat_id}")
    print(f"Période: {period}")
    print("=" * 80)

    # Vérifier la configuration Telegram
    if not settings.TELEGRAM_BOT_TOKEN:
        print("L TELEGRAM_BOT_TOKEN non configuré dans .env")
        return

    try:
        # Initialiser le client Telegram
        telegram_client = TelegramClient(settings)

        # Test connexion
        print("\n1. Test de connexion Telegram...")
        bot_info = await telegram_client.get_bot_info()
        if bot_info:
            print(f" Bot connecté: @{bot_info.get('username')}")
        else:
            print("L Impossible de se connecter au bot Telegram")
            return

        # Générer le rapport
        print(f"\n2. Génération du rapport {period}...")

        # Calculer les dates selon la période
        end_date = datetime.now()
        if period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        elif period == "quarterly":
            start_date = end_date - timedelta(days=90)
        else:
            print(f"L Période invalide: {period}")
            return

        print(f"Période: {start_date.strftime('%Y-%m-%d')} au {end_date.strftime('%Y-%m-%d')}")

        # Initialiser le service de rapport
        report_service = ReportService()

        # Générer le rapport
        print("\n3. Génération du contenu du rapport...")
        report = await report_service.generate_report(
            company_id=company_id,
            period_type=period,
            start_date=start_date,
            end_date=end_date
        )

        if not report:
            print("L Échec de génération du rapport")
            return

        print(f" Rapport généré avec succès")
        print(f"   - KPIs: {len(report.get('kpis', []))}")
        print(f"   - Insights: {len(report.get('insights', []))}")
        print(f"   - Recommandations: {'Oui' if report.get('recommendations') else 'Non'}")

        # Formater le rapport pour Telegram
        print("\n4. Formatage du rapport pour Telegram...")
        message = _format_report_for_telegram(report, period)
        print(f" Message formaté ({len(message)} caractères)")

        # Envoyer le rapport via Telegram
        print(f"\n5. Envoi du rapport au chat {chat_id}...")
        success = await telegram_client.send_message(chat_id, message)

        if success:
            print(f" Rapport envoyé avec succès à {chat_id}")
        else:
            print(f"L Échec de l'envoi à {chat_id}")

        print("\n" + "=" * 80)
        print(" TEST TERMINÉ")
        print("=" * 80)

    except Exception as e:
        print(f"\nL Erreur: {e}")
        import traceback
        traceback.print_exc()


def _format_report_for_telegram(report: dict, period: str) -> str:
    """
    Formate le rapport pour l'envoi via Telegram.

    Args:
        report: Données du rapport
        period: Période du rapport

    Returns:
        Message formaté en Markdown pour Telegram
    """
    period_names = {
        "weekly": "hebdomadaire",
        "monthly": "mensuel",
        "quarterly": "trimestriel"
    }

    message = f"=Ê *Rapport {period_names.get(period, period)}*\n\n"

    # KPIs
    kpis = report.get('kpis', {})
    if kpis:
        message += "*=° KPIs*\n"

        if 'revenue' in kpis:
            revenue = kpis['revenue']
            message += f"" CA: {revenue.get('current', 0):,.0f} XAF"
            if 'variation' in revenue:
                var = revenue['variation']
                emoji = "=È" if var > 0 else "=É"
                message += f" {emoji} {var:+.1f}%"
            message += "\n"

        if 'sales_count' in kpis:
            message += f"" Ventes: {kpis['sales_count'].get('current', 0)}\n"

        if 'new_clients' in kpis:
            message += f"" Nouveaux clients: {kpis['new_clients'].get('current', 0)}\n"

        message += "\n"

    # Insights
    insights = report.get('insights', [])
    if insights:
        message += "*= Insights*\n"
        for insight in insights[:3]:  # Limiter à 3 insights
            priority = insight.get('priority', 0)
            emoji = "=4" if priority >= 4 else "=á" if priority >= 3 else "=â"
            message += f"{emoji} {insight.get('message', '')}\n"
        message += "\n"

    # Recommandations
    recommendations = report.get('recommendations')
    if recommendations:
        message += "*=¡ Recommandations*\n"
        message += f"{recommendations}\n"

    return message


async def main():
    parser = argparse.ArgumentParser(
        description="Teste la génération et l'envoi d'un rapport via Telegram"
    )

    parser.add_argument(
        "--company-id",
        type=int,
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
        help="Période du rapport"
    )

    args = parser.parse_args()

    await test_generate_and_send_report(
        company_id=args.company_id,
        chat_id=args.chat_id,
        period=args.period
    )


if __name__ == "__main__":
    asyncio.run(main())
