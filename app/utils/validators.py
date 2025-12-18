# app/utils/validators.py
"""
Validateurs pour les données métier.
"""

import re
from typing import Optional


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
        
        phone = phone.strip().replace(' ', '').replace('-', '')
        
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
        
        phone = phone.strip().replace(' ', '').replace('-', '')
        
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