"""
Client Telegram Bot API pour envoi de rapports.
Utilisé pour les tests (production = WhatsApp).
"""

import httpx
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(
    chat_id: str,
    message: str
) -> bool:
    """
    Envoie un message via Telegram Bot API.

    Args:
        chat_id: ID du chat Telegram (numérique)
        message: Message à envoyer (même format que WhatsApp)

    Returns:
        True si envoi réussi

    Example:
        >>> success = await send_telegram_message("1498227036", "Bonjour...")
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("Telegram bot token not configured")
        return False

    # Nettoyer le chat_id
    chat_id = str(chat_id).strip()

    # URL
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    # Payload (désactiver Markdown pour éviter les erreurs de formatage)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": None,  # Pas de Markdown pour éviter conflits avec emojis
        "disable_web_page_preview": True
    }

    logger.info(
        "Sending Telegram message",
        extra={
            "chat_id": chat_id,
            "message_length": len(message)
        }
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()

            if result.get("ok"):
                message_id = result.get("result", {}).get("message_id")
                logger.info(
                    "Telegram message sent successfully",
                    extra={
                        "chat_id": chat_id,
                        "message_id": message_id
                    }
                )
                return True
            else:
                logger.error(
                    "Telegram API returned error",
                    extra={
                        "chat_id": chat_id,
                        "error": result.get("description")
                    }
                )
                return False

    except httpx.HTTPStatusError as e:
        logger.error(
            "Telegram API HTTP error",
            extra={
                "chat_id": chat_id,
                "status_code": e.response.status_code,
                "response": e.response.text
            },
            exc_info=True
        )
        return False

    except Exception as e:
        logger.error(
            "Telegram send failed",
            extra={
                "chat_id": chat_id,
                "error": str(e)
            },
            exc_info=True
        )
        return False


async def test_telegram_connection() -> bool:
    """
    Teste la connexion à l'API Telegram.

    Returns:
        True si connexion OK
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return False

    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            result = response.json()
            return result.get("ok", False)

    except Exception as e:
        logger.error(f"Telegram connection test failed: {e}")
        return False
