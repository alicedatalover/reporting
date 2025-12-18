# app/domain/enums.py
"""
Énumérations utilisées dans l'application.
"""

from enum import Enum


class ReportFrequency(str, Enum):
    """Fréquence des rapports"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ReportStatus(str, Enum):
    """Statut d'un rapport"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class DeliveryMethod(str, Enum):
    """Méthode de livraison"""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    EMAIL = "email"


class InsightType(str, Enum):
    """Type d'insight"""
    STOCK_ALERT = "stock_alert"
    CHURN_RISK = "churn_risk"
    SEASONALITY = "seasonality"
    PROFIT_MARGIN = "profit_margin"
    EXPENSE_ANOMALY = "expense_anomaly"


class OrderStatus(str, Enum):
    """Statut d'une commande"""
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    COMPLETED = "completed"