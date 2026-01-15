"""
Modèles Pydantic pour Genuka KPI Engine V2.
Définit tous les modèles de données utilisés dans l'application.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# ==================== ENUMS ====================

class ReportFrequency(str, Enum):
    """Fréquence de génération des rapports."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DeliveryMethod(str, Enum):
    """Méthode d'envoi des rapports."""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class ReportStatus(str, Enum):
    """Statut d'un rapport."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ==================== KPIs ====================

class KPIData(BaseModel):
    """KPIs calculés pour une période."""
    revenue: float = Field(description="Chiffre d'affaires total (FCFA)")
    orders_count: int = Field(description="Nombre de commandes")
    avg_basket: float = Field(description="Panier moyen (FCFA)")
    unique_customers: int = Field(description="Nombre de clients uniques")
    top_products: List[dict] = Field(
        description="Top 3 produits [{name, sales_count}]",
        default_factory=list
    )


class KPIComparison(BaseModel):
    """Comparaison des KPIs avec période précédente."""
    revenue_evolution: float = Field(description="Évolution CA en %")
    orders_evolution: float = Field(description="Évolution ventes en %")
    avg_basket_evolution: float = Field(description="Évolution panier moyen en %")


# ==================== INSIGHTS ====================

class InsightType(str, Enum):
    """Types d'insights détectés."""
    STOCK_ALERT = "stock_alert"
    CHURN_RISK = "churn_risk"
    SEASONALITY = "seasonality"
    PROFIT_MARGIN = "profit_margin"


class Insight(BaseModel):
    """Un insight détecté dans les données."""
    type: InsightType
    message: str = Field(description="Message descriptif de l'insight")
    severity: int = Field(description="Priorité (1=faible, 5=critique)", ge=1, le=5)
    data: Optional[dict] = Field(description="Données supplémentaires", default=None)


# ==================== REPORT ====================

class ReportData(BaseModel):
    """Données complètes d'un rapport."""
    company_name: str
    period_start: date
    period_end: date
    frequency: ReportFrequency

    # KPIs
    kpis: KPIData
    kpis_comparison: KPIComparison

    # Insights & Recommendations
    insights: List[Insight]
    recommendations: str = Field(description="Recommandations Gemini AI")

    # Métadonnées
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== API REQUESTS ====================

class GenerateReportRequest(BaseModel):
    """Requête pour générer un rapport manuellement."""
    company_id: str = Field(min_length=26, max_length=26)
    frequency: ReportFrequency
    end_date: Optional[str] = Field(
        default=None,
        description="Date de fin (YYYY-MM-DD). Si None, utilise date actuelle"
    )
    recipient: Optional[str] = Field(
        default=None,
        description="Destinataire (numéro WhatsApp ou chat_id Telegram)"
    )
    delivery_method: DeliveryMethod = Field(default=DeliveryMethod.WHATSAPP)


class PreviewReportRequest(BaseModel):
    """Requête pour prévisualiser un rapport sans l'envoyer."""
    company_id: str = Field(min_length=26, max_length=26)
    frequency: ReportFrequency
    end_date: Optional[str] = Field(default=None)


# ==================== REPORT CONFIG ====================

class ReportConfigCreate(BaseModel):
    """Création/mise à jour d'une configuration de rapport."""
    frequency: ReportFrequency
    enabled: bool = Field(default=True)
    whatsapp_number: Optional[str] = Field(
        default=None,
        description="Numéro WhatsApp (format: +237XXXXXXXXX)"
    )


class ReportConfigResponse(BaseModel):
    """Configuration de rapport (réponse API)."""
    company_id: str
    company_name: str
    frequency: ReportFrequency
    enabled: bool
    whatsapp_number: Optional[str]
    last_activity_date: Optional[date]
    next_report_date: Optional[date]
    created_at: datetime
    updated_at: datetime


# ==================== REPORT HISTORY ====================

class ReportHistoryResponse(BaseModel):
    """Historique d'un rapport (réponse API)."""
    id: str
    company_id: str
    frequency: ReportFrequency
    period_start: date
    period_end: date
    status: ReportStatus
    delivery_method: Optional[DeliveryMethod]
    recipient: Optional[str]
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    sent_at: datetime


# ==================== HEALTH CHECK ====================

class HealthCheckResponse(BaseModel):
    """Réponse du health check."""
    status: str = Field(description="healthy ou unhealthy")
    database: dict
    redis: dict
    gemini: dict
    whatsapp: dict
    telegram: dict
