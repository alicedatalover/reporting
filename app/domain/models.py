# app/domain/models.py
"""
Modèles Pydantic pour la validation et sérialisation des données.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app.domain.enums import (
    ReportFrequency,
    ReportStatus,
    DeliveryMethod,
    InsightType
)


# ==================== COMPANY ====================

class CompanyBase(BaseModel):
    """Données de base d'une entreprise"""
    id: str
    name: str
    currency_code: str = "XAF"


class CompanyDetail(CompanyBase):
    """Détails complets d'une entreprise"""
    handle: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    whatsapp_number: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


# ==================== REPORT CONFIG ====================

class ReportConfigBase(BaseModel):
    """Configuration de base pour les rapports"""
    report_frequency: ReportFrequency = ReportFrequency.WEEKLY
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: bool = True


class ReportConfigCreate(ReportConfigBase):
    """Création d'une configuration"""
    company_id: str


class ReportConfigUpdate(BaseModel):
    """Mise à jour d'une configuration"""
    report_frequency: Optional[ReportFrequency] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None


class ReportConfig(ReportConfigBase):
    """Configuration complète"""
    id: str
    company_id: str
    last_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== KPIs ====================

class KPIData(BaseModel):
    """Données KPI pour une période"""
    total_revenue: Decimal = Field(default=Decimal("0"), description="Chiffre d'affaires", ge=0)
    total_sales: int = Field(default=0, description="Nombre de ventes", ge=0)
    new_customers: int = Field(default=0, description="Nouveaux clients", ge=0)
    returning_customers: int = Field(default=0, description="Clients récurrents", ge=0)
    stock_alerts_count: int = Field(default=0, description="Alertes stock", ge=0)
    total_expenses: Decimal = Field(default=Decimal("0"), description="Dépenses totales", ge=0)
    net_result: Decimal = Field(default=Decimal("0"), description="Résultat net")  # Peut être négatif (perte)

    @field_validator('total_revenue', 'total_expenses')
    @classmethod
    def validate_positive_decimal(cls, v: Decimal, info) -> Decimal:
        """
        Valide que les montants financiers ne sont pas négatifs.

        Note: net_result PEUT être négatif (perte), il n'est pas validé ici.
        """
        if v < 0:
            raise ValueError(f"{info.field_name} ne peut pas être négatif: {v}")
        return v


class KPIComparison(BaseModel):
    """Comparaison KPIs vs période précédente"""
    revenue_variation: float = Field(default=0.0, description="Variation CA en %")
    sales_variation: float = Field(default=0.0, description="Variation ventes en %")
    returning_customers_variation: int = Field(default=0, description="Variation clients récurrents")
    expenses_variation: float = Field(default=0.0, description="Variation dépenses en %")


# ==================== INSIGHTS ====================

class InsightModel(BaseModel):
    """Modèle d'un insight"""
    type: InsightType
    title: str
    description: str
    priority: int = Field(ge=1, le=5, description="Priorité 1-5")
    financial_impact: Optional[Decimal] = Field(default=None, description="Impact financier estimé en XAF")
    actionable: bool = Field(default=True, description="Est-ce actionnable?")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Données supplémentaires")
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Priority must be between 1 and 5")
        return v


# ==================== REPORT ====================

class ReportData(BaseModel):
    """Données complètes d'un rapport"""
    company_name: str
    period_name: str
    period_range: str
    kpis: KPIData
    kpis_comparison: Optional[KPIComparison] = None
    insights: List[InsightModel] = Field(default_factory=list)
    recommendations: Optional[str] = None


class ReportHistoryCreate(BaseModel):
    """Création d'un historique de rapport"""
    company_id: str
    report_type: ReportFrequency
    period_start: date
    period_end: date
    status: ReportStatus
    delivery_method: DeliveryMethod
    recipient: str
    kpis: Optional[Dict[str, Any]] = None
    insights: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class ReportHistory(ReportHistoryCreate):
    """Historique complet"""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True