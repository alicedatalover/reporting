# app/infrastructure/external/__init__.py
"""
Clients pour les services externes.
"""

from app.infrastructure.external.gemini_client import GeminiClient
from app.infrastructure.external.whatsapp_client import WhatsAppClient
from app.infrastructure.external.telegram_client import TelegramClient

__all__ = [
    "GeminiClient",
    "WhatsAppClient",
    "TelegramClient",
]