# app/infrastructure/external/telegram_client.py
"""
Client pour l'API Telegram Bot.

Gère l'envoi de messages via Telegram Bot API.
"""

import httpx
from typing import Optional, Dict, Any
import logging

from app.config import Settings

logger = logging.getLogger(__name__)


class TelegramClient:
    """
    Client pour envoyer des messages via Telegram Bot API.
    
    Documentation: https://core.telegram.org/bots/api
    """
    
    def __init__(self, config: Settings):
        """
        Initialise le client Telegram.
        
        Args:
            config: Configuration de l'application
        
        Raises:
            ValueError: Si bot token manquant
        """
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be configured")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        logger.info("Telegram client initialized")
    
    async def send_message(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Envoie un message via Telegram.
        
        Args:
            chat_id: ID du chat Telegram (numérique ou @username)
            message: Message à envoyer (max 4096 caractères)
            parse_mode: Mode de parsing ("Markdown", "HTML", ou None)
            disable_web_page_preview: Désactiver l'aperçu des liens
        
        Returns:
            True si envoi réussi, False sinon
        
        Example:
            >>> client = TelegramClient(settings)
            >>> await client.send_message(
            ...     "123456789",
            ...     "*Rapport Mensuel*\nCA: 1,234,567 XAF"
            ... )
        """
        
        # Vérifier la taille
        if len(message) > 4096:
            logger.warning(
                "Message too long for Telegram, truncating",
                extra={
                    "chat_id": chat_id,
                    "length": len(message)
                }
            )
            message = message[:4090] + "..."
        
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
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
                    logger.info(
                        "Telegram message sent successfully",
                        extra={
                            "chat_id": chat_id,
                            "message_id": result.get("result", {}).get("message_id")
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
                "Failed to send Telegram message",
                extra={
                    "chat_id": chat_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    async def send_document(
        self,
        chat_id: str,
        document_url: str,
        caption: Optional[str] = None
    ) -> bool:
        """
        Envoie un document via Telegram.
        
        Args:
            chat_id: ID du chat
            document_url: URL du document
            caption: Légende du document (optionnelle)
        
        Returns:
            True si envoi réussi
        """
        
        url = f"{self.base_url}/sendDocument"
        
        payload = {
            "chat_id": chat_id,
            "document": document_url
        }
        
        if caption:
            payload["caption"] = caption
        
        logger.info(
            "Sending Telegram document",
            extra={"chat_id": chat_id}
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("ok"):
                    logger.info(
                        "Telegram document sent successfully",
                        extra={"chat_id": chat_id}
                    )
                    return True
                else:
                    logger.error(
                        "Failed to send Telegram document",
                        extra={
                            "chat_id": chat_id,
                            "error": result.get("description")
                        }
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Failed to send Telegram document",
                extra={
                    "chat_id": chat_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    async def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations du bot.
        
        Returns:
            Dictionnaire avec les infos du bot ou None
        """
        
        url = f"{self.base_url}/getMe"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("ok"):
                    return result.get("result")
                else:
                    return None
                    
        except Exception as e:
            logger.error(
                "Failed to get bot info",
                extra={"error": str(e)},
                exc_info=True
            )
            return None
    
    async def test_connection(self) -> bool:
        """
        Teste la connexion à l'API Telegram.
        
        Returns:
            True si connexion OK
        """
        
        try:
            bot_info = await self.get_bot_info()
            success = bot_info is not None
            
            logger.info(
                "Telegram connection test",
                extra={
                    "success": success,
                    "bot_username": bot_info.get("username") if bot_info else None
                }
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Telegram connection test failed",
                extra={"error": str(e)},
                exc_info=True
            )
            return False
    
    async def get_chat_info(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un chat.
        
        Args:
            chat_id: ID du chat
        
        Returns:
            Informations du chat ou None
        """
        
        url = f"{self.base_url}/getChat"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={"chat_id": chat_id}
                )
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("ok"):
                    return result.get("result")
                else:
                    return None
                    
        except Exception as e:
            logger.error(
                "Failed to get chat info",
                extra={
                    "chat_id": chat_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return None