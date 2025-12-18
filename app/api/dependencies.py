# app/api/dependencies.py
"""
Dépendances FastAPI réutilisables.

Fournit des dépendances communes pour les endpoints.
"""

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import get_db_session
from app.services import ReportService, NotificationService, CompanyService


# ==================== DATABASE ====================

async def get_report_service(
    session: AsyncSession = Depends(get_db_session)
) -> ReportService:
    """
    Dépendance pour obtenir le ReportService.
    
    Example:
        @app.get("/reports")
        async def get_reports(
            service: ReportService = Depends(get_report_service)
        ):
            ...
    """
    return ReportService(session)


async def get_company_service(
    session: AsyncSession = Depends(get_db_session)
) -> CompanyService:
    """Dépendance pour obtenir le CompanyService."""
    return CompanyService(session)


def get_notification_service() -> NotificationService:
    """Dépendance pour obtenir le NotificationService."""
    return NotificationService()


# ==================== VALIDATION ====================

async def validate_company_exists(
    company_id: str,
    service: CompanyService = Depends(get_company_service)
) -> str:
    """
    Valide qu'une entreprise existe.
    
    Args:
        company_id: ID de l'entreprise
        service: Service des entreprises
    
    Returns:
        company_id si valide
    
    Raises:
        HTTPException 404 si entreprise non trouvée
    """
    company = await service.get_company_with_config(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    return company_id