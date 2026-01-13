# app/utils/validators.py
"""
Validateurs pour les données métier.
"""

import re
from typing import Optional


def clean_phone_string(phone: str) -> str:
    """
    Nettoie une chaîne de téléphone (retire espaces, +, -).

    Fonction utilitaire pour normaliser les numéros avant validation/parsing.

    Args:
        phone: Numéro brut

    Returns:
        Numéro nettoyé

    Example:
        >>> clean_phone_string("+237 6 12-34-56-78")
        "237612345678"
    """
    return phone.replace("+", "").replace(" ", "").replace("-", "")


class PhoneValidator:
    """Validateur de numéros de téléphone."""
    
    # Format international : +237XXXXXXXXX
    CAMEROON_PATTERN = re.compile(r'^\+237[0-9]{9}$')
    
    # Format local : 6XXXXXXXX ou 237XXXXXXXXX
    LOCAL_PATTERN = re.compile(r'^(237)?[0-9]{9}$')
    
    @classmethod
    def validate(cls, phone: str) -> bool:
        """
        Valide un numéro de téléphone camerounais.

        Args:
            phone: Numéro à valider

        Returns:
            True si valide
        """
        if not phone:
            return False

        # ⚡ REFACTOR: Utilise la fonction utilitaire commune (définie plus bas)
        phone = clean_phone_string(phone.strip())

        return bool(
            cls.CAMEROON_PATTERN.match(phone) or
            cls.LOCAL_PATTERN.match(phone)
        )

    @classmethod
    def normalize(cls, phone: str) -> Optional[str]:
        """
        Normalise un numéro au format international.

        Args:
            phone: Numéro à normaliser

        Returns:
            Numéro au format +237XXXXXXXXX ou None si invalide
        """
        if not phone:
            return None

        # ⚡ REFACTOR: Utilise la fonction utilitaire commune (définie plus bas)
        phone = clean_phone_string(phone.strip())
        
        # Déjà au format international
        if cls.CAMEROON_PATTERN.match(phone):
            return phone
        
        # Format local
        match = cls.LOCAL_PATTERN.match(phone)
        if match:
            # Enlever le préfixe 237 si présent
            if phone.startswith('237'):
                phone = phone[3:]
            # Ajouter +237
            return f"+237{phone}"
        
        return None


class ReportValidator:
    """Validateur pour les données de rapport."""

    @staticmethod
    def validate_frequency(frequency: str) -> bool:
        """
        Valide une fréquence de rapport.

        Args:
            frequency: Fréquence à valider

        Returns:
            True si valide
        """
        return frequency in ['weekly', 'monthly', 'quarterly']

    @staticmethod
    def validate_delivery_method(method: str) -> bool:
        """
        Valide une méthode de livraison.

        Args:
            method: Méthode à valider

        Returns:
            True si valide
        """
        return method in ['whatsapp', 'telegram', 'email']


def validate_date_string(
    date_str: Optional[str],
    param_name: str = "date"
) -> Optional['date']:
    """
    Valide et convertit une chaîne de date au format YYYY-MM-DD.

    Args:
        date_str: Chaîne de date à valider (ou None)
        param_name: Nom du paramètre pour les messages d'erreur

    Returns:
        Objet date si valide, None si date_str est None

    Raises:
        HTTPException: Si le format de date est invalide

    Example:
        >>> validate_date_string("2024-01-15", "end_date")
        date(2024, 1, 15)
    """
    from datetime import datetime, date
    from fastapi import HTTPException, status

    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format for {param_name}: {date_str}. Use YYYY-MM-DD"
        )


def clean_telegram_chat_id(chat_id: str) -> str:
    """
    Nettoie et normalise un chat_id Telegram.

    - Supprime les caractères +, espace, tiret
    - Retire le préfixe 237 (Cameroun) si présent

    Args:
        chat_id: ID du chat Telegram (numéro de téléphone)

    Returns:
        Chat ID nettoyé

    Example:
        >>> clean_telegram_chat_id("+237 6 12-34-56-78")
        "612345678"
    """
    # ⚡ REFACTOR: Utilise la fonction utilitaire commune
    cleaned = clean_phone_string(chat_id)

    # Retirer le préfixe 237 si présent
    if cleaned.startswith("237"):
        cleaned = cleaned[3:]

    return cleaned