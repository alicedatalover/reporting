# app/services/notification_service.py
"""
Service de notifications.

Gère l'envoi de rapports via différents canaux (WhatsApp, Telegram).
"""

from typing import Optional
import logging

from app.domain.models import ReportData
from app.domain.enums import DeliveryMethod
from app.utils.formatters import WhatsAppFormatter
from app.infrastructure.external.whatsapp_client import WhatsAppClient
from app.infrastructure.external.telegram_client import TelegramClient
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service d'envoi de notifications.
    
    Formate et envoie les rapports via le canal approprié.
    """
    
    def __init__(self):
        """Initialise le service avec les clients de messaging."""
        
        self.formatter = WhatsAppFormatter()
        
        # Initialiser WhatsApp
        self.whatsapp_client = None
        if settings.ENABLE_WHATSAPP_NOTIFICATIONS and settings.WHATSAPP_API_TOKEN:
            try:
                self.whatsapp_client = WhatsAppClient(settings)
                logger.info("WhatsApp client initialized")
            except Exception as e:
                logger.warning(
                    "Failed to initialize WhatsApp client",
                    extra={"error": str(e)}
                )
        
        # Initialiser Telegram
        self.telegram_client = None
        if settings.ENABLE_TELEGRAM_NOTIFICATIONS and settings.TELEGRAM_BOT_TOKEN:
            try:
                self.telegram_client = TelegramClient(settings)
                logger.info("Telegram client initialized")
            except Exception as e:
                logger.warning(
                    "Failed to initialize Telegram client",
                    extra={"error": str(e)}
                )
    
    async def send_report(
        self,
        report_data: ReportData,
        recipient: str,
        method: DeliveryMethod = DeliveryMethod.WHATSAPP
    ) -> bool:
        """
        Envoie un rapport via le canal spécifié.
        
        Args:
            report_data: Données du rapport
            recipient: Numéro de téléphone ou chat_id
            method: Méthode d'envoi
        
        Returns:
            True si envoi réussi, False sinon
        
        Example:
            >>> service = NotificationService()
            >>> success = await service.send_report(
            ...     report_data,
            ...     "+237658173627",
            ...     DeliveryMethod.WHATSAPP
            ... )
        """
        
        logger.info(
            "Sending report",
            extra={
                "company": report_data.company_name,
                "recipient": recipient,
                "method": method.value
            }
        )
        
        try:
            # Formater le message
            message = self.formatter.format_report(report_data)

            # Valider la taille
            if len(message) > 4096:
                logger.warning(
                    "Message too long, truncating",
                    extra={"length": len(message)}
                )
                message = message[:4090] + "...\n[Tronqué]"
            
            # Envoyer selon la méthode
            if method == DeliveryMethod.WHATSAPP:
                success = await self._send_via_whatsapp(recipient, message)
            elif method == DeliveryMethod.TELEGRAM:
                success = await self._send_via_telegram(recipient, message)
            else:
                logger.error(f"Unsupported delivery method: {method}")
                return False
            
            if success:
                logger.info(
                    "Report sent successfully",
                    extra={
                        "company": report_data.company_name,
                        "method": method.value,
                        "message_length": len(message)
                    }
                )
            else:
                logger.error(
                    "Failed to send report",
                    extra={
                        "company": report_data.company_name,
                        "method": method.value
                    }
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Error sending report",
                extra={
                    "company": report_data.company_name,
                    "recipient": recipient,
                    "method": method.value,
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    async def _send_via_whatsapp(self, phone_number: str, message: str) -> bool:
        """
        Envoie un message via WhatsApp.
        
        Args:
            phone_number: Numéro WhatsApp (format international)
            message: Message à envoyer
        
        Returns:
            True si succès
        """
        
        if not self.whatsapp_client:
            logger.error("WhatsApp client not initialized")
            return False
        
        try:
            success = await self.whatsapp_client.send_message(
                phone_number=phone_number,
                message=message
            )
            return success
            
        except Exception as e:
            logger.error(
                "WhatsApp send failed",
                extra={"phone": phone_number, "error": str(e)},
                exc_info=True
            )
            return False
    
    async def _send_via_telegram(self, chat_id: str, message: str) -> bool:
        """
        Envoie un message via Telegram.
        
        Args:
            chat_id: ID du chat Telegram
            message: Message à envoyer
        
        Returns:
            True si succès
        """
        
        logger.info(
            "Attempting Telegram send",
            extra={
                "chat_id": chat_id,
                "has_client": bool(self.telegram_client),
                "message_length": len(message)
            }
        )
        
        if not self.telegram_client:
            logger.error("Telegram client is None - not initialized!")
            return False
        
        try:
            # Nettoyer le chat_id
            cleaned_chat_id = chat_id.replace("+", "").replace(" ", "").replace("-", "")
            
            # Si ça commence par 237, enlever
            if cleaned_chat_id.startswith("237"):
                logger.warning(f"Removing 237 prefix from {chat_id}")
                cleaned_chat_id = cleaned_chat_id[3:]
            
            logger.info(f"Sending to cleaned chat_id: {cleaned_chat_id}")
            
            success = await self.telegram_client.send_message(
                chat_id=cleaned_chat_id,
                message=message
            )
            
            if success:
                logger.info(f"✅ Telegram message sent successfully to {cleaned_chat_id}")
            else:
                logger.error(f"❌ Telegram client returned False for {cleaned_chat_id}")
            
            return success
            
        except Exception as e:
            logger.error(
                "Telegram send exception",
                extra={"chat_id": chat_id, "error": str(e)},
                exc_info=True
            )
            return False
    
    def get_available_methods(self) -> list[DeliveryMethod]:
        """
        Retourne les méthodes d'envoi disponibles.
        
        Returns:
            Liste des méthodes activées et configurées
        """
        methods = []
        
        if self.whatsapp_client:
            methods.append(DeliveryMethod.WHATSAPP)
        
        if self.telegram_client:
            methods.append(DeliveryMethod.TELEGRAM)
        
        return methods