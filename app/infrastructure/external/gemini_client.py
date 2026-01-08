# app/infrastructure/external/gemini_client.py
"""
Client pour l'API Google Gemini.

Gère les appels à l'API Gemini pour la génération de recommandations.
"""

import google.generativeai as genai
from typing import Optional
import logging

from app.config import Settings
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client pour l'API Google Gemini.
    
    Encapsule les appels à Gemini avec gestion d'erreurs et configuration.
    """
    
    def __init__(self, config: Settings):
        """
        Initialise le client Gemini.
        
        Args:
            config: Configuration de l'application
        
        Raises:
            ValueError: Si GOOGLE_API_KEY non configuré
        """
        self.api_key = config.GOOGLE_API_KEY
        self.model_name = config.GEMINI_MODEL
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured")
        
        # Configurer l'API
        genai.configure(api_key=self.api_key)
        
        # Créer le modèle
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(
            "Gemini client initialized",
            extra={"model": self.model_name}
        )
    
    @async_retry(
        max_attempts=3,
        initial_delay=2.0,
        max_delay=10.0,
        exceptions=(Exception,)  # Catch toutes exceptions Gemini (API errors, network, etc.)
    )
    async def generate_recommendations(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ) -> str:
        """
        Génère des recommandations via Gemini.
        
        Args:
            prompt: Prompt complet
            max_tokens: Nombre maximum de tokens à générer
            temperature: Créativité de la génération (0-1)
        
        Returns:
            Texte généré par Gemini
        
        Raises:
            Exception: Si erreur API Gemini
        
        Example:
            >>> client = GeminiClient(settings)
            >>> recommendations = await client.generate_recommendations(
            ...     prompt="Analyse...",
            ...     max_tokens=250
            ... )
        """
        
        try:
            # Configuration de génération
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                top_k=40
            )
            
            logger.debug(
                "Calling Gemini API",
                extra={
                    "model": self.model_name,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "prompt_length": len(prompt)
                }
            )

            # Appel synchrone via asyncio.to_thread pour ne pas bloquer l'event loop
            import asyncio
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            # Vérifier la réponse
            if not response or not response.text:
                logger.warning("Gemini returned empty response")
                return ""
            
            text = response.text.strip()
            
            logger.info(
                "Gemini API call successful",
                extra={
                    "response_length": len(text),
                    "tokens_used": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
                }
            )
            
            return text
            
        except Exception as e:
            logger.error(
                "Gemini API call failed",
                extra={
                    "error": str(e),
                    "model": self.model_name
                },
                exc_info=True
            )
            raise
    
    async def test_connection(self) -> bool:
        """
        Teste la connexion à l'API Gemini.
        
        Returns:
            True si connexion OK, False sinon
        """
        try:
            # Prompt simple et sûr (appel via asyncio.to_thread)
            import asyncio
            response = await asyncio.to_thread(
                self.model.generate_content,
                "What is 2+2? Answer with just the number.",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0.1
                )
            )
            
            # Vérifier si on a une réponse valide
            success = False
            if response and hasattr(response, 'candidates') and response.candidates:
                # Vérifier le finish_reason
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    # 1 = STOP (succès normal)
                    # 2 = MAX_TOKENS
                    # 3 = SAFETY
                    # 4 = RECITATION
                    success = candidate.finish_reason in [1, 2]  # STOP ou MAX_TOKENS = OK
                else:
                    success = True  # Si pas de finish_reason, considérer comme succès
            
            logger.info(
                "Gemini connection test",
                extra={
                    "success": success,
                    "has_response": bool(response),
                    "has_candidates": bool(response and hasattr(response, 'candidates') and response.candidates)
                }
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Gemini connection test failed",
                extra={"error": str(e)},
                exc_info=True
            )
            return False