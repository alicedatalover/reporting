# app/api/v1/companies.py
"""
Endpoints pour la gestion des entreprises.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any
import logging

from app.services import CompanyService
from app.api.dependencies import get_company_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("/")
async def list_companies(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, Any]:
    """
    Liste toutes les entreprises avec leurs configurations.
    
    Args:
        limit: Nombre max de résultats
        offset: Décalage pour pagination
        service: Service des entreprises
    
    Returns:
        Liste des entreprises avec métadonnées
    """
    
    companies = await service.list_active_companies()
    
    # Pagination
    total = len(companies)
    paginated = companies[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "companies": paginated
    }


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, Any]:
    """
    Récupère les détails d'une entreprise.
    
    Args:
        company_id: ID de l'entreprise
        service: Service des entreprises
    
    Returns:
        Détails de l'entreprise avec config
    
    Raises:
        HTTPException 404 si non trouvée
    """
    
    company = await service.get_company_with_config(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    return company


@router.get("/stats/summary")
async def get_companies_stats(
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, Any]:
    """
    Récupère les statistiques globales des entreprises.
    
    Returns:
        Statistiques d'utilisation
    """
    
    # Cette méthode nécessite d'ajouter des compteurs dans CompanyService
    # Pour l'instant, version simplifiée
    
    companies = await service.list_active_companies()
    
    total = len(companies)
    active_reports = sum(1 for c in companies if c.get('is_active'))
    
    frequencies = {}
    for company in companies:
        freq = company.get('report_frequency', 'none')
        frequencies[freq] = frequencies.get(freq, 0) + 1
    
    return {
        "total_companies": total,
        "active_reports": active_reports,
        "by_frequency": frequencies
    }