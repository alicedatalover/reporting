# app/services/company_service.py
"""
Service de gestion des entreprises.

Gère les opérations CRUD sur les companies et leurs configurations.
"""

from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    CompanyDetail,
    ReportConfig,
    ReportConfigCreate,
    ReportConfigUpdate
)
from app.domain.enums import ReportFrequency
from app.infrastructure.repositories import CompanyRepository, ReportConfigRepository

logger = logging.getLogger(__name__)


class CompanyService:
    """
    Service de gestion des entreprises et leurs configurations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialise le service.
        
        Args:
            session: Session SQLAlchemy async
        """
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.config_repo = ReportConfigRepository(session)
    
    async def get_company_with_config(
        self,
        company_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère une entreprise avec sa configuration.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Dictionnaire avec company + config ou None
        """
        return await self.company_repo.get_with_report_config(company_id)
    
    async def create_or_update_config(
        self,
        company_id: str,
        config_data: ReportConfigUpdate
    ) -> bool:
        """
        Crée ou met à jour la configuration d'une entreprise.
        
        Args:
            company_id: ID de l'entreprise
            config_data: Données de configuration
        
        Returns:
            True si succès
        """
        
        logger.info(
            "Creating/updating report config",
            extra={"company_id": company_id}
        )
        
        # Vérifier si config existe
        existing_config = await self.config_repo.get_by_company_id(company_id)
        
        if existing_config:
            # Update
            success = await self.config_repo.update(company_id, config_data)
        else:
            # Create
            config_create = ReportConfigCreate(
                company_id=company_id,
                report_frequency=config_data.report_frequency or ReportFrequency.WEEKLY,
                contact_name=config_data.contact_name,
                contact_phone=config_data.contact_phone,
                contact_email=config_data.contact_email,
                is_active=config_data.is_active if config_data.is_active is not None else True
            )
            
            config_id = await self.config_repo.create(config_create)
            success = bool(config_id)
        
        return success
    
    async def activate_company_reports(
        self,
        company_id: str,
        frequency: ReportFrequency = ReportFrequency.WEEKLY
    ) -> bool:
        """
        Active les rapports pour une entreprise.
        
        Args:
            company_id: ID de l'entreprise
            frequency: Fréquence des rapports
        
        Returns:
            True si succès
        """
        
        config_update = ReportConfigUpdate(
            report_frequency=frequency,
            is_active=True
        )
        
        return await self.create_or_update_config(company_id, config_update)
    
    async def deactivate_company_reports(self, company_id: str) -> bool:
        """
        Désactive les rapports pour une entreprise.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            True si succès
        """
        
        config_update = ReportConfigUpdate(is_active=False)
        return await self.create_or_update_config(company_id, config_update)
    
    async def list_active_companies(
        self,
        frequency: Optional[ReportFrequency] = None
    ) -> List[Dict[str, Any]]:
        """
        Liste les entreprises avec rapports actifs.
        
        Args:
            frequency: Filtrer par fréquence (optionnel)
        
        Returns:
            Liste d'entreprises
        """
        
        if frequency:
            return await self.company_repo.list_active_for_frequency(frequency)
        else:
            return await self.company_repo.list_all_with_configs()