"""
Client WhatsApp Business API pour envoi de rapports.
Utilise Meta Graph API.
"""

import httpx
from typing import Optional
import logging

from app.models import ReportData, KPIData, KPIComparison, Insight
from app.config import settings

logger = logging.getLogger(__name__)


def format_whatsapp_message(
    company_name: str,
    period_range: str,
    kpis: KPIData,
    kpis_comparison: KPIComparison,
    insights: list[Insight],
    recommendations: str
) -> str:
    """
    Formate le message WhatsApp selon le template validé.

    Format :
    Bonjour {company_name},

    Vous avez eu une {qualificatif} {period_range}. Voici un recap rapide :

    💰 CA : XXX FCFA (+X%)
    📦 Ventes : XX (+X%)
    🛒 Panier moyen : XXX FCFA
    ⭐ Top produits : ...
    [Insights avec emojis]

    Au vu de tout ça, {recommandations}
    """

    # Qualifier la période (très bonne, bonne, calme, difficile)
    if kpis_comparison.revenue_evolution > 15:
        qualificatif = "très bonne"
    elif kpis_comparison.revenue_evolution > 5:
        qualificatif = "bonne"
    elif kpis_comparison.revenue_evolution > -5:
        qualificatif = "stable"
    elif kpis_comparison.revenue_evolution > -15:
        qualificatif = "plus calme"
    else:
        qualificatif = "difficile"

    # Formater évolutions avec symbole
    def format_evolution(value: float) -> str:
        if value > 0:
            return f"(+{value:.1f}%)"
        elif value < 0:
            return f"({value:.1f}%)"
        else:
            return "(stable)"

    # Construire le message
    lines = []

    # Salutation
    lines.append(f"Bonjour {company_name} ! 👋")
    lines.append("")
    lines.append(f"Vous avez eu une {qualificatif} {period_range}. Voici un recap rapide :")
    lines.append("")

    # KPIs
    lines.append(f"💰 Chiffre d'affaires : {int(kpis.revenue):,} FCFA {format_evolution(kpis_comparison.revenue_evolution)}")
    lines.append(f"📦 Nombre de ventes : {kpis.orders_count} commandes {format_evolution(kpis_comparison.orders_evolution)}")
    lines.append(f"🛒 Panier moyen : {int(kpis.avg_basket):,} FCFA {format_evolution(kpis_comparison.avg_basket_evolution)}")

    # Top produits
    if kpis.top_products:
        top_names = [f"{p['name']} ({p['sales_count']} ventes)" for p in kpis.top_products]
        lines.append(f"⭐ Top produits : {', '.join(top_names)}")

    # Insights avec emojis
    for insight in insights:
        emoji = _get_insight_emoji(insight.type.value)
        lines.append(f"{emoji} {insight.message}")

    # Recommandations
    lines.append("")
    lines.append(f"Au vu de tout ça, nous pensons que {recommendations}")

    return "\n".join(lines)


def _get_insight_emoji(insight_type: str) -> str:
    """Retourne l'emoji approprié pour un type d'insight."""
    emojis = {
        "stock_alert": "⚠️",
        "churn_risk": "😴",
        "seasonality": "📊",
        "profit_margin": "💹"
    }
    return emojis.get(insight_type, "ℹ️")


async def send_whatsapp_message(
    phone_number: str,
    message: str
) -> bool:
    """
    Envoie un message via WhatsApp Business API.

    Args:
        phone_number: Numéro WhatsApp (format: +237XXXXXXXXX)
        message: Message à envoyer

    Returns:
        True si envoi réussi

    Example:
        >>> success = await send_whatsapp_message("+237658173627", "Bonjour...")
    """
    if not settings.WHATSAPP_API_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return False

    # Nettoyer le numéro
    phone_number = phone_number.replace(" ", "").replace("-", "")

    # Construire l'URL
    url = f"{settings.WHATSAPP_BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    # Payload
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message
        }
    }

    # Headers
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }

    logger.info(
        "Sending WhatsApp message",
        extra={
            "phone": phone_number,
            "message_length": len(message)
        }
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            message_id = result.get("messages", [{}])[0].get("id")

            logger.info(
                "WhatsApp message sent successfully",
                extra={
                    "phone": phone_number,
                    "message_id": message_id
                }
            )

            return True

    except httpx.HTTPStatusError as e:
        logger.error(
            "WhatsApp API error",
            extra={
                "phone": phone_number,
                "status_code": e.response.status_code,
                "response": e.response.text
            },
            exc_info=True
        )
        return False

    except Exception as e:
        logger.error(
            "WhatsApp send failed",
            extra={
                "phone": phone_number,
                "error": str(e)
            },
            exc_info=True
        )
        return False


async def test_whatsapp_connection() -> bool:
    """
    Teste la connexion à l'API WhatsApp.

    Returns:
        True si connexion OK
    """
    if not settings.WHATSAPP_API_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        return False

    try:
        url = f"{settings.WHATSAPP_BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}"
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers=headers,
                params={"fields": "verified_name"}
            )
            response.raise_for_status()
            return True

    except Exception as e:
        logger.error(f"WhatsApp connection test failed: {e}")
        return False
