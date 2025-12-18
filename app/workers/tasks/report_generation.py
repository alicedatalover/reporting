# app/workers/tasks/report_generation.py
"""
Tâches Celery pour la génération de rapports.

Contient toutes les tâches liées à la génération et l'envoi
automatique des rapports d'activité.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
import logging
import asyncio

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.infrastructure.database.connection import AsyncSessionLocal
from app.services import ReportService, NotificationService, CompanyService
from app.domain.enums import ReportFrequency, DeliveryMethod, ReportStatus
from app.infrastructure.repositories import ReportConfigRepository
from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """
    Tâche Celery avec support async et gestion DB.
    
    Fournit une session DB async pour les tâches.
    """
    
    _session: Optional[AsyncSession] = None
    
    def get_session(self) -> AsyncSession:
        """Obtient ou crée une session DB."""
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session
    
    def cleanup_session(self):
        """Ferme la session DB."""
        if self._session:
            asyncio.run(self._session.close())
            self._session = None


@celery_app.task(
    name="app.workers.tasks.report_generation.generate_scheduled_reports",
    base=DatabaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def generate_scheduled_reports(self, frequency: str) -> Dict[str, Any]:
    """
    Génère tous les rapports planifiés pour une fréquence donnée.
    
    Appelée automatiquement par Celery Beat selon le planning.
    
    Args:
        frequency: Fréquence des rapports ("weekly", "monthly", "quarterly")
    
    Returns:
        Statistiques d'exécution
    
    Example:
        # Appelé automatiquement chaque lundi à 8h
        >>> generate_scheduled_reports.delay("weekly")
    """
    
    logger.info(
        "Starting scheduled report generation",
        extra={
            "frequency": frequency,
            "task_id": self.request.id
        }
    )
    
    try:
        # Convertir en enum
        report_frequency = ReportFrequency(frequency)
        
        # Exécuter la génération en async
        result = asyncio.run(
            _generate_reports_for_frequency(report_frequency)
        )
        
        logger.info(
            "Scheduled report generation completed",
            extra={
                "frequency": frequency,
                "task_id": self.request.id,
                "total": result["total"],
                "success": result["success"],
                "failed": result["failed"]
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Scheduled report generation failed",
            extra={
                "frequency": frequency,
                "task_id": self.request.id,
                "error": str(e)
            },
            exc_info=True
        )
        
        # Retry avec backoff exponentiel
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


@celery_app.task(
    name="app.workers.tasks.report_generation.generate_single_report",
    base=DatabaseTask,
    bind=True,
    max_retries=2,
    default_retry_delay=60
)
def generate_single_report(
    self,
    company_id: str,
    frequency: str,
    end_date: Optional[str] = None,
    recipient: Optional[str] = None,
    delivery_method: str = "telegram"
) -> Dict[str, Any]:
    """
    Génère un rapport pour une entreprise spécifique.
    
    Utilisée pour les tests manuels ou génération à la demande.
    
    Args:
        company_id: ID de l'entreprise
        frequency: Fréquence ("weekly", "monthly", "quarterly")
        end_date: Date de fin au format YYYY-MM-DD (optionnel)
        recipient: Numéro/chat_id du destinataire (optionnel)
        delivery_method: Méthode d'envoi ("whatsapp", "telegram")
    
    Returns:
        Résultat de la génération
    
    Example:
        >>> generate_single_report.delay(
        ...     "company_123",
        ...     "monthly",
        ...     "2025-07-31",
        ...     "+237658173627",
        ...     "whatsapp"
        ... )
    """
    
    logger.info(
        "Starting single report generation",
        extra={
            "company_id": company_id,
            "frequency": frequency,
            "task_id": self.request.id
        }
    )
    
    try:
        # Convertir les paramètres
        report_frequency = ReportFrequency(frequency)
        delivery_method_enum = DeliveryMethod(delivery_method)
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        
        # Exécuter la génération
        result = asyncio.run(
            _generate_and_send_report(
                company_id=company_id,
                frequency=report_frequency,
                end_date=end_date_obj,
                recipient=recipient,
                delivery_method=delivery_method_enum
            )
        )
        
        logger.info(
            "Single report generation completed",
            extra={
                "company_id": company_id,
                "task_id": self.request.id,
                "status": result["status"]
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Single report generation failed",
            extra={
                "company_id": company_id,
                "task_id": self.request.id,
                "error": str(e)
            },
            exc_info=True
        )
        
        raise self.retry(exc=e)


# ==================== FONCTIONS ASYNC INTERNES ====================

async def _generate_reports_for_frequency(
    frequency: ReportFrequency
) -> Dict[str, Any]:
    """
    Génère tous les rapports pour une fréquence donnée.
    
    Args:
        frequency: Fréquence des rapports
    
    Returns:
        Statistiques d'exécution
    """
    
    async with AsyncSessionLocal() as session:
        company_service = CompanyService(session)
        
        # Récupérer toutes les entreprises actives pour cette fréquence
        companies = await company_service.list_active_companies(frequency)
        
        total = len(companies)
        success = 0
        failed = 0
        
        logger.info(
            f"Found {total} companies for {frequency.value} reports"
        )
        
        for company in companies:
            company_id = company['id']
            recipient = company.get('contact_phone')
            
            if not recipient:
                logger.warning(
                    "No contact phone for company",
                    extra={"company_id": company_id}
                )
                failed += 1
                continue
            
            try:
                # Générer et envoyer le rapport
                result = await _generate_and_send_report(
                    company_id=company_id,
                    frequency=frequency,
                    recipient=recipient,
                    delivery_method=DeliveryMethod.WHATSAPP  # Production
                )
                
                if result['status'] == 'success':
                    success += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(
                    "Failed to generate report for company",
                    extra={
                        "company_id": company_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
                failed += 1
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "frequency": frequency.value
        }


async def _generate_and_send_report(
    company_id: str,
    frequency: ReportFrequency,
    recipient: Optional[str] = None,
    delivery_method: DeliveryMethod = DeliveryMethod.WHATSAPP,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """Génère et envoie un rapport pour une entreprise."""
    
    start_time = datetime.utcnow()
    
    # Créer un nouveau engine pour cette tâche
    from app.infrastructure.database.connection import create_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    engine = create_engine()
    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    session = None
    
    try:
        async with SessionLocal() as session:
            # 1. Générer le rapport
            report_service = ReportService(session)
            
            report_data = await report_service.generate_report(
                company_id=company_id,
                frequency=frequency,
                end_date=end_date
            )
            
            logger.info("Report generated successfully")  # ← LOG
            
            # 2. Récupérer le destinataire si non fourni
            if not recipient:
                company_service = CompanyService(session)
                company_info = await company_service.get_company_with_config(company_id)
                recipient = company_info.get('contact_phone')
                
                if not recipient:
                    raise ValueError("No recipient phone number configured")
            
            # 3. IMPORTANT : Créer NotificationService ICI (après la session)
            logger.info("Creating NotificationService")  # ← NOUVEAU LOG
            notification_service = NotificationService()
            logger.info(f"NotificationService created, telegram_client exists: {notification_service.telegram_client is not None}")  # ← NOUVEAU LOG
            
            # 4. Envoyer la notification
            logger.info(f"About to call send_report with method={delivery_method}")  # ← NOUVEAU LOG
            
            send_success = await notification_service.send_report(
                report_data=report_data,
                recipient=recipient,
                method=delivery_method
            )
            
            logger.info(f"send_report returned: {send_success}")  # ← NOUVEAU LOG
            
            # 5. Enregistrer dans l'historique
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            await _save_report_history(
                session=session,
                company_id=company_id,
                frequency=frequency,
                report_data=report_data,
                status=ReportStatus.SUCCESS if send_success else ReportStatus.FAILED,
                delivery_method=delivery_method,
                recipient=recipient,
                execution_time_ms=execution_time,
                error_message=None if send_success else "Failed to send notification"
            )
            
            return {
                "status": "success" if send_success else "failed",
                "company_id": company_id,
                "company_name": report_data.company_name,
                "recipient": recipient,
                "delivery_method": delivery_method.value,
                "execution_time_ms": execution_time
            }
            
    except Exception as e:
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        if session is not None:
            try:
                await _save_report_history(
                    session=session,
                    company_id=company_id,
                    frequency=frequency,
                    report_data=None,
                    status=ReportStatus.FAILED,
                    delivery_method=delivery_method,
                    recipient=recipient,
                    execution_time_ms=execution_time,
                    error_message=str(e)
                )
            except Exception as save_error:
                logger.error(
                    "Failed to save error to history",
                    extra={"error": str(save_error)},
                    exc_info=True
                )
        
        raise
        
    finally:
        await engine.dispose()

async def _save_report_history(
    session: AsyncSession,
    company_id: str,
    frequency: ReportFrequency,
    report_data: Optional[Any],
    status: ReportStatus,
    delivery_method: DeliveryMethod,
    recipient: Optional[str],
    execution_time_ms: int,
    error_message: Optional[str] = None
) -> None:
    """
    Enregistre l'historique d'un rapport dans la base.
    """
    
    import uuid
    from sqlalchemy import text
    
    history_id = str(uuid.uuid4()).replace('-', '')[:26]
    
    # Extraire les infos du rapport
    if report_data:
        start_date, end_date = _parse_period_range(report_data.period_range)
        
        # Si parsing échoue, utiliser des valeurs par défaut
        if not start_date or not end_date:
            logger.warning("Failed to parse dates, using defaults")
            end_date = date.today()
            if frequency == ReportFrequency.WEEKLY:
                start_date = end_date - timedelta(days=6)
            elif frequency == ReportFrequency.MONTHLY:
                start_date = end_date.replace(day=1)
            else:  # QUARTERLY
                quarter_month = ((end_date.month - 1) // 3) * 3 + 1
                start_date = end_date.replace(month=quarter_month, day=1)
        
        kpis_json = report_data.kpis.model_dump_json() if report_data.kpis else None
        insights_json = [i.model_dump() for i in report_data.insights] if report_data.insights else None
        recommendations = report_data.recommendations
    else:
        # Valeurs par défaut si pas de report_data
        end_date = date.today()
        if frequency == ReportFrequency.WEEKLY:
            start_date = end_date - timedelta(days=6)
        elif frequency == ReportFrequency.MONTHLY:
            start_date = end_date.replace(day=1)
        else:  # QUARTERLY
            quarter_month = ((end_date.month - 1) // 3) * 3 + 1
            start_date = end_date.replace(month=quarter_month, day=1)
        
        kpis_json = insights_json = recommendations = None
    
    query = """
        INSERT INTO report_history (
            id,
            company_id,
            report_type,
            period_start,
            period_end,
            status,
            delivery_method,
            recipient,
            kpis,
            insights,
            recommendations,
            error_message,
            execution_time_ms,
            created_at
        ) VALUES (
            :id,
            :company_id,
            :report_type,
            :period_start,
            :period_end,
            :status,
            :delivery_method,
            :recipient,
            :kpis,
            :insights,
            :recommendations,
            :error_message,
            :execution_time_ms,
            NOW()
        )
    """
    
    await session.execute(
        text(query),
        {
            "id": history_id,
            "company_id": company_id,
            "report_type": frequency.value,
            "period_start": start_date,
            "period_end": end_date,
            "status": status.value,
            "delivery_method": delivery_method.value,
            "recipient": recipient,
            "kpis": kpis_json,
            "insights": str(insights_json) if insights_json else None,
            "recommendations": recommendations,
            "error_message": error_message,
            "execution_time_ms": execution_time_ms
        }
    )
    
    await session.commit()
    
    logger.info(
        "Report history saved",
        extra={
            "history_id": history_id,
            "company_id": company_id,
            "status": status.value,
            "period_start": str(start_date),
            "period_end": str(end_date)
        }
    )


def _parse_period_range(period_range: str) -> tuple[Optional[date], Optional[date]]:
    """
    Parse une période au format "DD/MM - DD/MM/YYYY".
    
    Args:
        period_range: Période formatée
    
    Returns:
        Tuple (start_date, end_date)
    """
    try:
        # Format attendu : "01/07 - 31/07/2025"
        parts = period_range.split(" - ")
        if len(parts) != 2:
            logger.warning(f"Invalid period_range format: {period_range}")
            return None, None
        
        start_str, end_str = parts
        
        # Parse end date (format: DD/MM/YYYY)
        end_date = datetime.strptime(end_str.strip(), "%d/%m/%Y").date()
        
        # Parse start date (format: DD/MM, même année que end)
        start_parts = start_str.strip().split("/")
        if len(start_parts) != 2:
            logger.warning(f"Invalid start date format: {start_str}")
            return None, None
            
        start_day = int(start_parts[0])
        start_month = int(start_parts[1])
        
        # Utiliser l'année de end_date
        start_date = date(end_date.year, start_month, start_day)
        
        logger.debug(f"Parsed period: {start_date} to {end_date}")
        return start_date, end_date
        
    except Exception as e:
        logger.error(f"Failed to parse period_range '{period_range}': {e}")
        return None, None