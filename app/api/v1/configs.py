# app/api/v1/configs.py
"""
Endpoints pour la gestion des configurations de rapports.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Dict, Any
import logging

from app.domain.models import ReportConfigUpdate
from app.domain.enums import ReportFrequency
from app.services import CompanyService
from app.api.dependencies import get_company_service, validate_company_exists
from app.utils.validators import PhoneValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/configs", tags=["Report Configs"])


@router.get("/{company_id}")
async def get_report_config(
    company_id: str = Depends(validate_company_exists),
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, Any]:
    """
    Récupère la configuration de rapport d'une entreprise.
    
    Args:
        company_id: ID de l'entreprise
        service: Service des entreprises
    
    Returns:
        Configuration du rapport
    
    Raises:
        HTTPException 404 si config non trouvée
    """
    
    company_data = await service.get_company_with_config(company_id)
    
    if not company_data or not company_data.get('config_id'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No report config found for company {company_id}"
        )
    
    config = {
        "company_id": company_data['id'],
        "company_name": company_data['name'],
        "report_frequency": company_data.get('report_frequency'),
        "contact_name": company_data.get('contact_name'),
        "contact_phone": company_data.get('contact_phone'),
        "contact_email": company_data.get('contact_email'),
        "is_active": company_data.get('is_active'),
        "last_sent_at": company_data.get('last_sent_at'),
    }
    
    return config


@router.post("/{company_id}")
async def create_or_update_config(
    company_id: str = Depends(validate_company_exists),
    config: ReportConfigUpdate = Body(...),
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, Any]:
    """
    Crée ou met à jour la configuration de rapport.
    
    Args:
        company_id: ID de l'entreprise
        config: Données de configuration
        service: Service des entreprises
    
    Returns:
        Message de confirmation
    
    Raises:
        HTTPException 400 si données invalides
    
    Example:
        POST /api/v1/configs/company_123
        {
            "report_frequency": "weekly",
            "contact_phone": "+237658173627",
            "is_active": true
        }
    """
    
    # Valider le numéro de téléphone si fourni
    if config.contact_phone:
        normalized_phone = PhoneValidator.normalize(config.contact_phone)
        if not normalized_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid phone number format: {config.contact_phone}"
            )
        config.contact_phone = normalized_phone
    
    # Créer ou mettre à jour
    success = await service.create_or_update_config(company_id, config)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration"
        )
    
    logger.info(
        "Report config updated",
        extra={
            "company_id": company_id,
            "frequency": config.report_frequency.value if config.report_frequency else None,
            "is_active": config.is_active
        }
    )
    
    return {
        "message": "Configuration saved successfully",
        "company_id": company_id
    }


@router.post("/{company_id}/activate")
async def activate_reports(
    company_id: str = Depends(validate_company_exists),
    frequency: ReportFrequency = Body(..., embed=True),
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, str]:
    """
    Active les rapports pour une entreprise.
    
    Args:
        company_id: ID de l'entreprise
        frequency: Fréquence des rapports
        service: Service des entreprises
    
    Returns:
        Message de confirmation
    
    Example:
        POST /api/v1/configs/company_123/activate
        {
            "frequency": "weekly"
        }
    """
    
    success = await service.activate_company_reports(company_id, frequency)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate reports"
        )
    
    logger.info(
        "Reports activated",
        extra={"company_id": company_id, "frequency": frequency.value}
    )
    
    return {
        "message": f"Reports activated with {frequency.value} frequency",
        "company_id": company_id,
        "frequency": frequency.value
    }


@router.post("/{company_id}/deactivate")
async def deactivate_reports(
    company_id: str = Depends(validate_company_exists),
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, str]:
    """
    Désactive les rapports pour une entreprise.
    
    Args:
        company_id: ID de l'entreprise
        service: Service des entreprises
    
    Returns:
        Message de confirmation
    """
    
    success = await service.deactivate_company_reports(company_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate reports"
        )
    
    logger.info(
        "Reports deactivated",
        extra={"company_id": company_id}
    )
    
    return {
        "message": "Reports deactivated successfully",
        "company_id": company_id
    }


@router.patch("/{company_id}/phone")
async def update_phone_number(
    company_id: str = Depends(validate_company_exists),
    phone: str = Body(..., embed=True),
    service: CompanyService = Depends(get_company_service)
) -> Dict[str, str]:
    """
    Met à jour le numéro de téléphone de contact.
    
    Args:
        company_id: ID de l'entreprise
        phone: Nouveau numéro
        service: Service des entreprises
    
    Returns:
        Message de confirmation
    
    Raises:
        HTTPException 400 si numéro invalide
    
    Example:
        PATCH /api/v1/configs/company_123/phone
        {
            "phone": "+237658173627"
        }
    """
    
    # Valider et normaliser
    normalized_phone = PhoneValidator.normalize(phone)
    if not normalized_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid phone number format: {phone}"
        )
    
    # Mettre à jour
    config_update = ReportConfigUpdate(contact_phone=normalized_phone)
    success = await service.create_or_update_config(company_id, config_update)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update phone number"
        )
    
    logger.info(
        "Phone number updated",
        extra={"company_id": company_id, "phone": normalized_phone}
    )
    
    return {
        "message": "Phone number updated successfully",
        "company_id": company_id,
        "phone": normalized_phone
    }