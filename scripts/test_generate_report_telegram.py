# -*- coding: utf-8 -*-
# scripts/test_generate_report_telegram.py
"""
Script pour tester la generation et l'envoi d'un rapport via Telegram.

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


async def test_generate_and_send_report(company_id: int, chat_id: str, period: str):
    """
    Teste la generation et l'envoi d'un rapport via Telegram.

    Args:
        company_id: ID de l'entreprise
        chat_id: ID du chat Telegram
        period: Periode du rapport (weekly, monthly, quarterly)
    """

    print("=" * 80)
    print("TEST GENERATION ET ENVOI RAPPORT TELEGRAM")
    print("=" * 80)
    print(f"Company ID: {company_id}")
    print(f"Chat ID: {chat_id}")
    print(f"Periode: {period}")
    print("=" * 80)

    # Verifier la configuration Telegram
    if not settings.TELEGRAM_BOT_TOKEN:
        print("ERREUR: TELEGRAM_BOT_TOKEN non configure dans .env")
        return

    try:
        # Initialiser le client Telegram
        telegram_client = TelegramClient(settings)

        # Test connexion
        print("\n1. Test de connexion Telegram...")
        bot_info = await telegram_client.get_bot_info()
        if bot_info:
            print(f"OK: Bot connecte: @{bot_info.get('username')}")
        else:
            print("ERREUR: Impossible de se connecter au bot Telegram")
            return

        # Generer un rapport de test
        print(f"\n2. Generation du rapport {period}...")

        # Calculer les dates selon la periode
        end_date = datetime.now()
        if period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        elif period == "quarterly":
            start_date = end_date - timedelta(days=90)
        else:
            print(f"ERREUR: Periode invalide: {period}")
            return

        print(f"Periode: {start_date.strftime('%Y-%m-%d')} au {end_date.strftime('%Y-%m-%d')}")

        # Creer un rapport de test
        print("\n3. Creation du contenu du rapport de test...")
        test_report = _create_test_report(company_id, period, start_date, end_date)

        print("OK: Rapport de test cree")
        print(f"   - KPIs: {len(test_report.get('kpis', {}))}")
        print(f"   - Insights: {len(test_report.get('insights', []))}")
        print(f"   - Recommandations: {'Oui' if test_report.get('recommendations') else 'Non'}")

        # Formater le rapport pour Telegram
        print("\n4. Formatage du rapport pour Telegram...")
        message = _format_report_for_telegram(test_report, period)
        print(f"OK: Message formate ({len(message)} caracteres)")

        # Envoyer le rapport via Telegram
        print(f"\n5. Envoi du rapport au chat {chat_id}...")
        success = await telegram_client.send_message(chat_id, message)

        if success:
            print(f"OK: Rapport envoye avec succes a {chat_id}")
        else:
            print(f"ERREUR: Echec de l'envoi a {chat_id}")

        print("\n" + "=" * 80)
        print("TEST TERMINE")
        print("=" * 80)

    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()


def _create_test_report(company_id: int, period: str, start_date: datetime, end_date: datetime) -> dict:
    """
    Cree un rapport de test avec des donnees fictives.

    Args:
        company_id: ID de l'entreprise
        period: Periode du rapport
        start_date: Date de debut
        end_date: Date de fin

    Returns:
        Rapport de test avec KPIs, insights et recommandations
    """
    return {
        'company_id': company_id,
        'period': period,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'kpis': {
            'revenue': {
                'current': 5000000,
                'previous': 4500000,
                'variation': 11.1
            },
            'sales_count': {
                'current': 45,
                'previous': 40
            },
            'new_clients': {
                'current': 8,
                'previous': 6
            }
        },
        'insights': [
            {
                'type': 'churn_risk',
                'priority': 4,
                'message': 'Clients a risque: 5 clients fideles inactifs depuis 30+ jours'
            },
            {
                'type': 'stock_alert',
                'priority': 3,
                'message': 'Stock faible: 3 produits sous le seuil critique'
            },
            {
                'type': 'seasonal_trend',
                'priority': 3,
                'message': 'Hausse saisonniere: +15% vs meme periode annee precedente'
            }
        ],
        'recommendations': (
            "1. Relancer les clients inactifs avec une offre speciale\n"
            "2. Reapprovisionner les produits en stock faible\n"
            "3. Capitaliser sur la hausse saisonniere avec des promotions"
        )
    }


def _format_report_for_telegram(report: dict, period: str) -> str:
    """
    Formate le rapport pour l'envoi via Telegram.

    Args:
        report: Donnees du rapport
        period: Periode du rapport

    Returns:
        Message formate en Markdown pour Telegram
    """
    period_names = {
        "weekly": "hebdomadaire",
        "monthly": "mensuel",
        "quarterly": "trimestriel"
    }

    message = f"*Rapport {period_names.get(period, period)}*\n\n"

    # KPIs
    kpis = report.get('kpis', {})
    if kpis:
        message += "*KPIs*\n"

        if 'revenue' in kpis:
            revenue = kpis['revenue']
            message += f"- CA: {revenue.get('current', 0):,.0f} XAF"
            if 'variation' in revenue:
                var = revenue['variation']
                emoji = "+" if var > 0 else "-"
                message += f" ({emoji}{abs(var):.1f}%)"
            message += "\n"

        if 'sales_count' in kpis:
            message += f"- Ventes: {kpis['sales_count'].get('current', 0)}\n"

        if 'new_clients' in kpis:
            message += f"- Nouveaux clients: {kpis['new_clients'].get('current', 0)}\n"

        message += "\n"

    # Insights
    insights = report.get('insights', [])
    if insights:
        message += "*Insights*\n"
        for insight in insights[:3]:  # Limiter a 3 insights
            priority = insight.get('priority', 0)
            emoji = "!" if priority >= 4 else "~" if priority >= 3 else "."
            message += f"{emoji} {insight.get('message', '')}\n"
        message += "\n"

    # Recommandations
    recommendations = report.get('recommendations')
    if recommendations:
        message += "*Recommandations*\n"
        message += f"{recommendations}\n"

    return message


async def main():
    parser = argparse.ArgumentParser(
        description="Teste la generation et l'envoi d'un rapport via Telegram"
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
        help="Periode du rapport"
    )

    args = parser.parse_args()

    await test_generate_and_send_report(
        company_id=args.company_id,
        chat_id=args.chat_id,
        period=args.period
    )


if __name__ == "__main__":
    asyncio.run(main())
