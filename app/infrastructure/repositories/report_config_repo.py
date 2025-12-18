# app/infrastructure/repositories/report_config_repo.py
"""
Repository pour les configurations de rapports.

Gère toutes les requêtes liées à report_configs.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.infrastructure.repositories.base import BaseRepository
from app.domain.enums import ReportFrequency
from app.domain.models import ReportConfigCreate, ReportConfigUpdate

logger = logging.getLogger(__name__)


class ReportConfigRepository(BaseRepository):
    """Repository pour les configurations de rapports"""
    
    async def get_by_id(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une configuration par son ID.
        
        Args:
            config_id: ID de la configuration
        
        Returns:
            Dictionnaire avec les données de config ou None
        """
        query = """
            SELECT 
                id,
                company_id,
                report_frequency,
                contact_name,
                contact_phone,
                contact_email,
                is_active,
                last_sent_at,
                created_at,
                updated_at
            FROM report_configs
            WHERE id = :config_id
        """
        
        return await self._fetch_one(query, {"config_id": config_id})
    
    async def exists(self, config_id: str) -> bool:
        """Vérifie si une configuration existe"""
        query = "SELECT COUNT(*) FROM report_configs WHERE id = :config_id"
        count = await self._execute_scalar(query, {"config_id": config_id})
        return count > 0
    
    async def get_by_company_id(
        self,
        company_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère la configuration d'une entreprise.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Configuration ou None
        """
        query = f"""
            SELECT 
                id,
                company_id,
                report_frequency,
                contact_name,
                contact_phone,
                contact_email,
                is_active,
                last_sent_at,
                created_at,
                updated_at
            FROM report_configs
            WHERE {self._apply_collation_cast('company_id')} = {self._apply_collation_cast(':company_id')}
        """
        
        return await self._fetch_one(query, {"company_id": company_id})
    
    async def create(
        self,
        config: ReportConfigCreate
    ) -> str:
        """
        Crée une nouvelle configuration.
        
        Args:
            config: Données de la configuration
        
        Returns:
            ID de la configuration créée
        """
        import uuid
        
        config_id = str(uuid.uuid4()).replace('-', '')[:26]
        
        query = """
            INSERT INTO report_configs (
                id,
                company_id,
                report_frequency,
                contact_name,
                contact_phone,
                contact_email,
                is_active,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :company_id,
                :report_frequency,
                :contact_name,
                :contact_phone,
                :contact_email,
                :is_active,
                NOW(),
                NOW()
            )
        """
        
        from sqlalchemy import text
        
        await self.session.execute(
            text(query),
            {
                "id": config_id,
                "company_id": config.company_id,
                "report_frequency": config.report_frequency.value,
                "contact_name": config.contact_name,
                "contact_phone": config.contact_phone,
                "contact_email": config.contact_email,
                "is_active": config.is_active
            }
        )
        
        await self.session.commit()
        
        logger.info(
            "Created report config",
            extra={
                "config_id": config_id,
                "company_id": config.company_id
            }
        )
        
        return config_id
    
    async def update(
        self,
        company_id: str,
        updates: ReportConfigUpdate
    ) -> bool:
        """
        Met à jour une configuration.
        
        Args:
            company_id: ID de l'entreprise
            updates: Champs à mettre à jour
        
        Returns:
            True si mise à jour réussie, False sinon
        """
        # Construire dynamiquement la requête UPDATE
        update_fields = []
        params: Dict[str, Any] = {"company_id": company_id}
        
        if updates.report_frequency is not None:
            update_fields.append("report_frequency = :report_frequency")
            params["report_frequency"] = updates.report_frequency.value
        
        if updates.contact_name is not None:
            update_fields.append("contact_name = :contact_name")
            params["contact_name"] = updates.contact_name
        
        if updates.contact_phone is not None:
            update_fields.append("contact_phone = :contact_phone")
            params["contact_phone"] = updates.contact_phone
        
        if updates.contact_email is not None:
            update_fields.append("contact_email = :contact_email")
            params["contact_email"] = updates.contact_email
        
        if updates.is_active is not None:
            update_fields.append("is_active = :is_active")
            params["is_active"] = updates.is_active
        
        if not update_fields:
            logger.warning("No fields to update")
            return False
        
        update_fields.append("updated_at = NOW()")
        
        query = f"""
            UPDATE report_configs
            SET {', '.join(update_fields)}
            WHERE {self._apply_collation_cast('company_id')} = {self._apply_collation_cast(':company_id')}
        """
        
        from sqlalchemy import text
        
        result = await self.session.execute(text(query), params)
        await self.session.commit()
        
        success = result.rowcount > 0
        
        if success:
            logger.info(
                "Updated report config",
                extra={"company_id": company_id, "fields": list(params.keys())}
            )
        
        return success
    
    async def update_last_sent_at(
        self,
        company_id: str,
        sent_at: datetime
    ) -> bool:
        """
        Met à jour la date du dernier envoi.
        
        Args:
            company_id: ID de l'entreprise
            sent_at: Date/heure d'envoi
        
        Returns:
            True si succès
        """
        query = f"""
            UPDATE report_configs
            SET last_sent_at = :sent_at,
                updated_at = NOW()
            WHERE {self._apply_collation_cast('company_id')} = {self._apply_collation_cast(':company_id')}
        """
        
        from sqlalchemy import text
        
        result = await self.session.execute(
            text(query),
            {"company_id": company_id, "sent_at": sent_at}
        )
        await self.session.commit()
        
        return result.rowcount > 0
    
    async def delete(self, company_id: str) -> bool:
        """
        Supprime une configuration.
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            True si suppression réussie
        """
        query = f"""
            DELETE FROM report_configs
            WHERE {self._apply_collation_cast('company_id')} = {self._apply_collation_cast(':company_id')}
        """
        
        from sqlalchemy import text
        
        result = await self.session.execute(text(query), {"company_id": company_id})
        await self.session.commit()
        
        success = result.rowcount > 0
        
        if success:
            logger.info(
                "Deleted report config",
                extra={"company_id": company_id}
            )
        
        return success
    
    async def list_active_for_frequency(
        self,
        frequency: ReportFrequency
    ) -> List[Dict[str, Any]]:
        """
        Liste toutes les configs actives pour une fréquence.
        
        Args:
            frequency: Fréquence recherchée
        
        Returns:
            Liste de configurations
        """
        query = """
            SELECT 
                id,
                company_id,
                report_frequency,
                contact_phone,
                contact_email,
                last_sent_at
            FROM report_configs
            WHERE report_frequency = :frequency
              AND is_active = 1
            ORDER BY company_id
        """
        
        return await self._execute_query(
            query,
            {"frequency": frequency.value}
        )
    
    async def count_active(self) -> int:
        """
        Compte le nombre de configurations actives.
        
        Returns:
            Nombre de configs avec is_active=1
        """
        query = "SELECT COUNT(*) FROM report_configs WHERE is_active = 1"
        return await self._execute_scalar(query) or 0
    
    async def count_by_frequency(
        self,
        frequency: ReportFrequency
    ) -> int:
        """
        Compte les configs pour une fréquence.
        
        Args:
            frequency: Fréquence
        
        Returns:
            Nombre de configurations
        """
        query = """
            SELECT COUNT(*) 
            FROM report_configs 
            WHERE report_frequency = :frequency 
              AND is_active = 1
        """
        
        return await self._execute_scalar(
            query,
            {"frequency": frequency.value}
        ) or 0