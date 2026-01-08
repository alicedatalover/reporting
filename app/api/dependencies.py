# app/api/dependencies.py
"""
Dépendances FastAPI réutilisables.

Fournit des dépendances communes pour les endpoints.
"""

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import get_db_session
from app.services import ReportService, NotificationService, CompanyService
from app.utils.rate_limiter import standard_limiter, strict_limiter, permissive_limiter


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


# ==================== RATE LIMITING ====================

async def rate_limit_standard(request: Request) -> None:
    """
    Rate limiting standard (60/min, 1000/h).

    Utilisé pour les endpoints de consultation classiques.
    """
    await standard_limiter.check_rate_limit(
        request,
        endpoint=f"{request.method}:{request.url.path}"
    )


async def rate_limit_strict(request: Request) -> None:
    """
    Rate limiting strict (10/min, 100/h).

    Utilisé pour les endpoints intensifs (génération de rapports, preview).
    """
    await strict_limiter.check_rate_limit(
        request,
        endpoint=f"{request.method}:{request.url.path}"
    )


async def rate_limit_permissive(request: Request) -> None:
    """
    Rate limiting permissif (120/min, 2000/h).

    Utilisé pour les endpoints légers (status de tâche, stats).
    """
    await permissive_limiter.check_rate_limit(
        request,
        endpoint=f"{request.method}:{request.url.path}"
    )