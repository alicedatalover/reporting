# app/infrastructure/external/whatsapp_client.py
"""
Client pour l'API WhatsApp Business (Meta Graph API).

Gère l'envoi de messages via WhatsApp Business API.
"""

import httpx
from typing import Optional, Dict, Any
import logging

from app.config import Settings

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Client pour envoyer des messages via WhatsApp Business API.
    
    Documentation: https://developers.facebook.com/docs/whatsapp/cloud-api
    """
    
    def __init__(self, config: Settings):
        """
        Initialise le client WhatsApp.
        
        Args:
            config: Configuration de l'application
        
        Raises:
            ValueError: Si credentials manquants
        """
        self.api_token = config.WHATSAPP_API_TOKEN
        self.phone_number_id = config.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = config.WHATSAPP_BASE_URL
        
        if not self.api_token or not self.phone_number_id:
            raise ValueError(
                "WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID must be configured"
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(
            "WhatsApp client initialized",
            extra={"phone_number_id": self.phone_number_id}
        )
    
    async def send_message(
        self,
        phone_number: str,
        message: str,
        preview_url: bool = False
    ) -> bool:
        """
        Envoie un message texte via WhatsApp.
        
        Args:
            phone_number: Numéro du destinataire (format international: +237XXXXXXXXX)
            message: Message à envoyer (max 4096 caractères)
            preview_url: Activer l'aperçu des URLs
        
        Returns:
            True si envoi réussi, False sinon
        
        Raises:
            Exception: Si erreur API
        
        Example:
            >>> client = WhatsAppClient(settings)
            >>> await client.send_message(
            ...     "+237658173627",
            ...     "Bonjour ! Voici votre rapport..."
            ... )
        """
        
        # Nettoyer le numéro (enlever espaces, tirets)
        phone_number = phone_number.replace(" ", "").replace("-", "")
        
        # Vérifier la taille du message
        if len(message) > 4096:
            logger.warning(
                "Message too long, truncating",
                extra={
                    "phone": phone_number,
                    "length": len(message)
                }
            )
            message = message[:4090] + "..."
        
        # Construire l'URL de l'API
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        # Construire le payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message
            }
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
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers
                )
                
                response.raise_for_status()
                
                result = response.json()
                
                logger.info(
                    "WhatsApp message sent successfully",
                    extra={
                        "phone": phone_number,
                        "message_id": result.get("messages", [{}])[0].get("id")
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
                "Failed to send WhatsApp message",
                extra={
                    "phone": phone_number,
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    async def send_template_message(
        self,
        phone_number: str,
        template_name: str,
        language_code: str = "fr",
        parameters: Optional[list] = None
    ) -> bool:
        """
        Envoie un message template pré-approuvé.
        
        Les templates doivent être créés et approuvés dans Meta Business Manager.
        
        Args:
            phone_number: Numéro du destinataire
            template_name: Nom du template
            language_code: Code langue (fr, en, etc.)
            parameters: Paramètres du template
        
        Returns:
            True si envoi réussi
        
        Example:
            >>> await client.send_template_message(
            ...     "+237658173627",
            ...     "rapport_mensuel",
            ...     "fr",
            ...     ["Janvier", "1,234,567 XAF"]
            ... )
        """
        
        phone_number = phone_number.replace(" ", "").replace("-", "")
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        # Construire les composants du template
        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": param}
                    for param in parameters
                ]
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                },
                "components": components
            }
        }
        
        logger.info(
            "Sending WhatsApp template message",
            extra={
                "phone": phone_number,
                "template": template_name
            }
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers
                )
                
                response.raise_for_status()
                
                logger.info(
                    "WhatsApp template sent successfully",
                    extra={"phone": phone_number, "template": template_name}
                )
                
                return True
                
        except Exception as e:
            logger.error(
                "Failed to send WhatsApp template",
                extra={
                    "phone": phone_number,
                    "template": template_name,
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    async def get_business_profile(self) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations du profil WhatsApp Business.
        
        Returns:
            Dictionnaire avec les infos du profil ou None
        """
        
        url = f"{self.base_url}/{self.phone_number_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params={"fields": "verified_name,code_verification_status,quality_rating"}
                )
                
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error(
                "Failed to get business profile",
                extra={"error": str(e)},
                exc_info=True
            )
            return None
    
    async def test_connection(self) -> bool:
        """
        Teste la connexion à l'API WhatsApp.
        
        Returns:
            True si connexion OK
        """
        
        try:
            profile = await self.get_business_profile()
            success = profile is not None
            
            logger.info(
                "WhatsApp connection test",
                extra={"success": success}
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "WhatsApp connection test failed",
                extra={"error": str(e)},
                exc_info=True
            )
            return False