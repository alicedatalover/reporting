# app/api/V1/reports.py
"""
Endpoints pour la génération et l'historique des rapports.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from typing import Dict, Any, Optional, List
from datetime import date, datetime
import logging

from app.domain.enums import ReportFrequency, DeliveryMethod
from app.services import ReportService
from app.api.dependencies import (
    get_report_service,
    validate_company_exists,
    get_notification_service
)
from app.workers.tasks.report_generation import generate_single_report
from app.utils.validators import PhoneValidator, ReportValidator
from kombu.exceptions import OperationalError as KombuOperationalError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate")
async def generate_report_manual(
    company_id: str = Body(...),
    frequency: ReportFrequency = Body(default=ReportFrequency.MONTHLY),
    end_date: Optional[str] = Body(default=None),
    recipient: Optional[str] = Body(default=None),
    delivery_method: DeliveryMethod = Body(default=DeliveryMethod.TELEGRAM),
    send_notification: bool = Body(default=True)
) -> Dict[str, Any]:
    """
    Génère un rapport manuellement (test ou à la demande).
    
    Cette endpoint déclenche une tâche Celery asynchrone.
    
    Args:
        company_id: ID de l'entreprise
        frequency: Fréquence du rapport
        end_date: Date de fin au format YYYY-MM-DD (optionnel)
        recipient: Destinataire (optionnel, récupéré depuis config si None)
        delivery_method: Méthode d'envoi
        send_notification: Envoyer la notification ou juste générer
    
    Returns:
        Task ID et statut
    
    Raises:
        HTTPException 400 si données invalides
    
    Example:
        POST /api/v1/reports/generate
        {
            "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
            "frequency": "monthly",
            "end_date": "2025-07-31",
            "recipient": "+237658173627",
            "delivery_method": "telegram"
        }
    """
    
    # Valider le numéro si fourni
    if recipient:
        normalized_phone = PhoneValidator.normalize(recipient)
        if not normalized_phone and delivery_method == DeliveryMethod.WHATSAPP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid phone number: {recipient}"
            )
        recipient = normalized_phone or recipient
    
    # Valider la date si fournie
    end_date_obj = None
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {end_date}. Use YYYY-MM-DD"
            )
    
    # Déclencher la tâche Celery
    try:
        task = generate_single_report.delay(
            company_id=company_id,
            frequency=frequency.value,
            end_date=end_date,
            recipient=recipient,
            delivery_method=delivery_method.value
        )
    except KombuOperationalError as e:
        logger.error(
            "Celery broker unavailable",
            extra={"company_id": company_id, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Celery broker indisponible. Démarrez Redis sur localhost:6379 ou mettez à jour la configuration."
        )
    except Exception as e:
        logger.error(
            "Failed to enqueue report task",
            extra={"company_id": company_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec du déclenchement de la tâche de génération de rapport."
        )
    
    logger.info(
        "Report generation task created",
        extra={
            "company_id": company_id,
            "task_id": task.id,
            "frequency": frequency.value
        }
    )
    
    return {
        "message": "Report generation started",
        "task_id": task.id,
        "status": "pending",
        "company_id": company_id
    }


@router.get("/task/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Récupère le statut d'une tâche de génération de rapport.
    
    Args:
        task_id: ID de la tâche Celery
    
    Returns:
        Statut et résultat de la tâche
    
    Example:
        GET /api/v1/reports/task/abc123-def456
    """
    
    from celery.result import AsyncResult
    from app.workers.celery_app import celery_app
    
    task = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task.status,
        "ready": task.ready()
    }
    
    if task.ready():
        if task.successful():
            response["result"] = task.result
        elif task.failed():
            response["error"] = str(task.info)
    
    return response


@router.post("/preview")
async def preview_report(
    company_id: str = Body(...),
    frequency: ReportFrequency = Body(default=ReportFrequency.MONTHLY),
    end_date: Optional[str] = Body(default=None),
    service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """
    Génère un aperçu du rapport sans l'envoyer.
    
    Utile pour tester les données avant l'envoi réel.
    
    Args:
        company_id: ID de l'entreprise
        frequency: Fréquence du rapport
        end_date: Date de fin (optionnel)
        service: Service de rapports
    
    Returns:
        Données complètes du rapport
    
    Raises:
        HTTPException 404 si entreprise non trouvée
    
    Example:
        POST /api/v1/reports/preview
        {
            "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
            "frequency": "monthly",
            "end_date": "2025-07-31"
        }
    """
    
    # Valider la date si fournie
    end_date_obj = None
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {end_date}. Use YYYY-MM-DD"
            )
    
    try:
        # Générer le rapport
        report_data = await service.generate_report(
            company_id=company_id,
            frequency=frequency,
            end_date=end_date_obj
        )
        
        # Formater pour le retour
        from app.utils.formatters import WhatsAppFormatter
        formatter = WhatsAppFormatter()
        formatted_message = formatter.format_report(report_data.model_dump())
        
        return {
            "company_name": report_data.company_name,
            "period_name": report_data.period_name,
            "period_range": report_data.period_range,
            "kpis": report_data.kpis.model_dump(),
            "kpis_comparison": report_data.kpis_comparison.model_dump() if report_data.kpis_comparison else None,
            "insights": [i.model_dump() for i in report_data.insights],
            "recommendations": report_data.recommendations,
            "formatted_message": formatted_message,
            "message_length": len(formatted_message)
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Report preview failed",
            extra={"company_id": company_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report preview: {str(e)}"
        )


@router.get("/history/{company_id}")
async def get_report_history(
    company_id: str = Depends(validate_company_exists),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
) -> Dict[str, Any]:
    """
    Récupère l'historique des rapports d'une entreprise.
    
    Args:
        company_id: ID de l'entreprise
        limit: Nombre max de résultats
        offset: Décalage pour pagination
    
    Returns:
        Historique paginé des rapports
    
    Example:
        GET /api/v1/reports/history/company_123?limit=10&offset=0
    """
    
    from sqlalchemy import text
    from app.infrastructure.database.connection import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        # Requête pour récupérer l'historique
        query = """
            SELECT 
                id,
                report_type,
                period_start,
                period_end,
                status,
                delivery_method,
                recipient,
                execution_time_ms,
                error_message,
                created_at
            FROM report_history
            WHERE company_id = :company_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        result = await session.execute(
            text(query),
            {
                "company_id": company_id,
                "limit": limit,
                "offset": offset
            }
        )
        
        history = [dict(row._mapping) for row in result.all()]
        
        # Compter le total
        count_query = """
            SELECT COUNT(*) as total
            FROM report_history
            WHERE company_id = :company_id
        """
        
        count_result = await session.execute(
            text(count_query),
            {"company_id": company_id}
        )
        
        total = count_result.scalar() or 0
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "history": history
    }


@router.get("/stats/global")
async def get_global_stats() -> Dict[str, Any]:
    """
    Récupère les statistiques globales des rapports.
    
    Returns:
        Statistiques d'utilisation globales
    
    Example:
        GET /api/v1/reports/stats/global
    """
    
    from sqlalchemy import text
    from app.infrastructure.database.connection import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        # Total rapports
        total_query = "SELECT COUNT(*) as total FROM report_history"
        total_result = await session.execute(text(total_query))
        total = total_result.scalar() or 0
        
        # Par statut
        status_query = """
            SELECT 
                status,
                COUNT(*) as count
            FROM report_history
            GROUP BY status
        """
        status_result = await session.execute(text(status_query))
        by_status = {row.status: row.count for row in status_result.all()}
        
        # Par fréquence
        frequency_query = """
            SELECT 
                report_type,
                COUNT(*) as count
            FROM report_history
            GROUP BY report_type
        """
        frequency_result = await session.execute(text(frequency_query))
        by_frequency = {row.report_type: row.count for row in frequency_result.all()}
        
        # Temps d'exécution moyen
        avg_time_query = """
            SELECT AVG(execution_time_ms) as avg_time
            FROM report_history
            WHERE status = 'success'
        """
        avg_time_result = await session.execute(text(avg_time_query))
        avg_execution_time = avg_time_result.scalar() or 0
    
    return {
        "total_reports": total,
        "by_status": by_status,
        "by_frequency": by_frequency,
        "avg_execution_time_ms": int(avg_execution_time)
    }
