# app/infrastructure/repositories/company_repo.py
"""
Repository pour les entreprises (companies).

Gère toutes les requêtes liées aux companies et leur configuration.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json

from app.infrastructure.repositories.base import BaseRepository
from app.domain.enums import ReportFrequency

logger = logging.getLogger(__name__)


class CompanyRepository(BaseRepository):
    """Repository pour les opérations sur les companies"""
    
    async def get_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une entreprise par son ID.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Dictionnaire avec les données de l'entreprise ou None
        """
        query = """
            SELECT 
                id,
                name,
                handle,
                company_code,
                description,
                logoUrl as logo_url,
                currency_code,
                currency_name,
                metadata,
                created_at,
                updated_at,
                type
            FROM companies
            WHERE id = :company_id
        """
        
        company = await self._fetch_one(query, {"company_id": company_id})
        
        if company:
            # Parser metadata JSON
            if company.get('metadata'):
                try:
                    company['metadata'] = json.loads(company['metadata']) \
                        if isinstance(company['metadata'], str) \
                        else company['metadata']
                except json.JSONDecodeError:
                    logger.warning(
                        "Failed to parse company metadata",
                        extra={"company_id": company_id}
                    )
                    company['metadata'] = {}
        
        return company
    
    async def exists(self, company_id: str) -> bool:
        """
        Vérifie si une entreprise existe.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            True si existe, False sinon
        """
        query = "SELECT COUNT(*) FROM companies WHERE id = :company_id"
        count = await self._execute_scalar(query, {"company_id": company_id})
        return count > 0
    
    async def get_with_report_config(
        self,
        company_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère une entreprise avec sa configuration de rapport.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Dictionnaire avec company + report_config ou None
        """
        query = f"""
            SELECT 
                c.id,
                c.name,
                c.currency_code,
                c.metadata,
                rc.id as config_id,
                rc.report_frequency,
                rc.contact_name,
                rc.contact_phone,
                rc.contact_email,
                rc.is_active,
                rc.last_sent_at
            FROM companies c
            LEFT JOIN report_configs rc 
                ON {self._apply_collation_cast('c.id')} = {self._apply_collation_cast('rc.company_id')}
            WHERE c.id = :company_id
        """
        
        result = await self._fetch_one(query, {"company_id": company_id})
        
        if result and result.get('metadata'):
            try:
                result['metadata'] = json.loads(result['metadata']) \
                    if isinstance(result['metadata'], str) \
                    else result['metadata']
            except json.JSONDecodeError:
                result['metadata'] = {}
        
        return result
    
    async def extract_contact_phone(
        self,
        company_id: str
    ) -> Optional[str]:
        """
        Extrait le numéro de téléphone depuis metadata ou report_config.
        
        Priorité:
        1. report_configs.contact_phone
        2. companies.whatsapp_number (si colonne existe)
        3. companies.metadata.contact
        4. companies.metadata.phone
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Numéro de téléphone ou None
        """
        company = await self.get_with_report_config(company_id)
        
        if not company:
            return None
        
        # Priorité 1: contact_phone dans report_configs
        if company.get('contact_phone'):
            return company['contact_phone']
        
        # Priorité 2: metadata.contact ou metadata.phone
        metadata = company.get('metadata', {})
        if isinstance(metadata, dict):
            contact = metadata.get('contact')
            if contact and '+' in contact:  # Probablement un numéro
                return contact
            
            phone = metadata.get('phone')
            if phone:
                return phone
        
        return None
    
    async def list_active_for_frequency(
        self,
        frequency: ReportFrequency
    ) -> List[Dict[str, Any]]:
        """
        Liste toutes les entreprises actives pour une fréquence donnée.
        
        Args:
            frequency: Fréquence des rapports
        
        Returns:
            Liste d'entreprises avec leur config
        """
        query = f"""
            SELECT 
                c.id,
                c.name,
                c.currency_code,
                rc.contact_phone,
                rc.contact_email,
                rc.report_frequency,
                rc.last_sent_at
            FROM companies c
            INNER JOIN report_configs rc 
                ON {self._apply_collation_cast('c.id')} = {self._apply_collation_cast('rc.company_id')}
            WHERE rc.report_frequency = :frequency
              AND rc.is_active = 1
            ORDER BY c.name
        """
        
        return await self._execute_query(
            query,
            {"frequency": frequency.value}
        )
    
    async def list_all_with_configs(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Liste toutes les entreprises avec leurs configurations.
        
        Utilisé pour l'interface admin.
        
        Args:
            limit: Nombre max de résultats
            offset: Décalage pour pagination
        
        Returns:
            Liste d'entreprises avec configs
        """
        query = f"""
            SELECT 
                c.id,
                c.name,
                c.handle,
                c.currency_code,
                c.created_at,
                rc.id as config_id,
                rc.report_frequency,
                rc.contact_name,
                rc.contact_phone,
                rc.contact_email,
                rc.is_active,
                rc.last_sent_at,
                rc.updated_at as config_updated_at
            FROM companies c
            LEFT JOIN report_configs rc 
                ON {self._apply_collation_cast('c.id')} = {self._apply_collation_cast('rc.company_id')}
            ORDER BY c.name
            LIMIT :limit OFFSET :offset
        """
        
        return await self._execute_query(
            query,
            {"limit": limit, "offset": offset}
        )
    
    async def count_total(self) -> int:
        """
        Compte le nombre total d'entreprises.
        
        Returns:
            Nombre d'entreprises
        """
        query = "SELECT COUNT(*) FROM companies"
        return await self._execute_scalar(query) or 0
    
    async def count_active_reports(self) -> int:
        """
        Compte le nombre d'entreprises avec rapports actifs.
        
        Returns:
            Nombre d'entreprises avec is_active=1
        """
        query = """
            SELECT COUNT(DISTINCT company_id) 
            FROM report_configs 
            WHERE is_active = 1
        """
        return await self._execute_scalar(query) or 0