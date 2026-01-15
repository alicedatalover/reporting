"""
Tâches Celery pour génération et envoi automatique des rapports.
"""

from celery import Celery
from datetime import datetime, date, timedelta
import logging
import asyncio

from app.config import settings
from app.core.database import (
    init_database,
    execute_query,
    get_company_info,
    get_last_activity_date
)
from app.core.kpi import (
    calculate_period_dates,
    format_period_range,
    calculate_kpis,
    compare_kpis,
    get_last_year_comparison
)
from app.core.insights import extract_all_insights
from app.core.recommendations import generate_recommendations
from app.notifications.whatsapp import format_whatsapp_message, send_whatsapp_message
from app.notifications.telegram import send_telegram_message
from app.models import ReportFrequency, DeliveryMethod

logger = logging.getLogger(__name__)

# Créer l'application Celery
celery_app = Celery(
    "genuka_kpi_engine_v2",
    broker=settings.CELERY_BROKER_URL_COMPUTED,
    backend=settings.CELERY_RESULT_BACKEND_COMPUTED
)

# Configuration Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max par tâche
    worker_prefetch_multiplier=1,
)

# Importer le schedule depuis scheduler.py
from app.worker.scheduler import celery_schedule
celery_app.conf.beat_schedule = celery_schedule


# ==================== HELPER ASYNC/SYNC ====================

def run_async(coro):
    """
    Exécute une coroutine de manière sûre depuis Celery.
    Compatible avec event loop existant ou non.
    """
    try:
        loop = asyncio.get_running_loop()
        # Loop existe, on doit exécuter dans un nouveau thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # Pas de loop actif, on peut utiliser asyncio.run()
        return asyncio.run(coro)


# ==================== TÂCHES CELERY ====================

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_scheduled_reports(self, frequency: str):
    """
    Génère et envoie les rapports pour toutes les entreprises actives d'une fréquence.
    Appelé automatiquement par Celery Beat.

    Args:
        frequency: "weekly" ou "monthly"

    Returns:
        Statistiques d'exécution

    Example:
        # Appelé automatiquement chaque lundi à 8h
        >>> generate_scheduled_reports.delay("weekly")
    """
    logger.info(f"Starting scheduled report generation for {frequency}")

    try:
        # Initialiser DB si nécessaire
        init_database()

        # Exécuter la génération en async
        result = run_async(_generate_reports_for_frequency(frequency))

        logger.info(
            f"Scheduled reports completed",
            extra={
                "frequency": frequency,
                "total": result["total"],
                "success": result["success"],
                "failed": result["failed"],
                "skipped": result["skipped"]
            }
        )

        return result

    except Exception as e:
        logger.error(
            f"Scheduled report generation failed: {e}",
            extra={"frequency": frequency},
            exc_info=True
        )
        # Retry avec backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_single_report_task(
    self,
    company_id: str,
    frequency: str,
    end_date: str = None,
    recipient: str = None,
    delivery_method: str = "whatsapp"
):
    """
    Génère et envoie un rapport pour une entreprise spécifique.
    Utilisé pour génération manuelle ou tests.

    Args:
        company_id: ID de l'entreprise
        frequency: "weekly" ou "monthly"
        end_date: Date de fin (YYYY-MM-DD) ou None
        recipient: Destinataire ou None
        delivery_method: "whatsapp" ou "telegram"

    Returns:
        Résultat de la génération

    Example:
        >>> generate_single_report_task.delay(
        ...     "01hjt9qsj7b039ww1nyrn9kg5t",
        ...     "weekly",
        ...     recipient="+237658173627"
        ... )
    """
    logger.info(
        f"Starting single report generation",
        extra={
            "company_id": company_id,
            "frequency": frequency,
            "task_id": self.request.id
        }
    )

    try:
        # Initialiser DB
        init_database()

        # Convertir end_date en date object
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # Exécuter la génération
        result = run_async(
            _generate_and_send_report(
                company_id=company_id,
                frequency=ReportFrequency(frequency),
                end_date=end_date_obj,
                recipient=recipient,
                delivery_method=DeliveryMethod(delivery_method)
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
            f"Single report generation failed: {e}",
            extra={
                "company_id": company_id,
                "task_id": self.request.id
            },
            exc_info=True
        )
        # Retry
        raise self.retry(exc=e)


# ==================== FONCTIONS ASYNC INTERNES ====================

async def _generate_reports_for_frequency(frequency: str) -> dict:
    """
    Génère tous les rapports pour une fréquence donnée.

    Returns:
        Statistiques : {total, success, failed, skipped}
    """
    freq_enum = ReportFrequency(frequency)

    # Récupérer toutes les entreprises actives pour cette fréquence
    query = """
        SELECT
            rc.company_id,
            c.name as company_name,
            rc.whatsapp_number,
            rc.last_activity_date
        FROM report_configs rc
        JOIN companies c ON rc.company_id = c.id
        WHERE rc.frequency = :frequency
          AND rc.enabled = 1
        ORDER BY c.name ASC
    """

    companies = await execute_query(query, {"frequency": frequency})

    total = len(companies)
    success = 0
    failed = 0
    skipped = 0

    logger.info(f"Found {total} companies for {frequency} reports")

    # Générer les rapports séquentiellement (pas de semaphore pour simplicité)
    for company in companies:
        company_id = company["company_id"]
        recipient = company.get("whatsapp_number")

        # Skip si pas de numéro WhatsApp
        if not recipient:
            logger.warning(
                f"No WhatsApp number for company {company_id}",
                extra={"company_id": company_id}
            )
            skipped += 1
            continue

        try:
            result = await _generate_and_send_report(
                company_id=company_id,
                frequency=freq_enum,
                recipient=recipient,
                delivery_method=DeliveryMethod.WHATSAPP
            )

            if result["status"] == "success":
                success += 1
            elif result["status"] == "skipped":
                skipped += 1
            else:
                failed += 1

        except Exception as e:
            logger.error(
                f"Failed to generate report for {company_id}: {e}",
                extra={"company_id": company_id},
                exc_info=True
            )
            failed += 1

    return {
        "frequency": frequency,
        "total": total,
        "success": success,
        "failed": failed,
        "skipped": skipped
    }


async def _generate_and_send_report(
    company_id: str,
    frequency: ReportFrequency,
    end_date: date = None,
    recipient: str = None,
    delivery_method: DeliveryMethod = DeliveryMethod.WHATSAPP
) -> dict:
    """
    Génère et envoie un rapport pour une entreprise.

    Returns:
        {status: "success"|"failed"|"skipped", ...}
    """
    try:
        # 1. Vérifier activité (30 jours)
        last_activity = await get_last_activity_date(company_id)
        if last_activity:
            days_since = (settings.get_current_date() - datetime.strptime(last_activity, "%Y-%m-%d").date()).days
            if days_since > settings.INACTIVE_DAYS_THRESHOLD:
                logger.info(
                    f"Skipping inactive company {company_id}",
                    extra={
                        "company_id": company_id,
                        "days_since_activity": days_since
                    }
                )
                return {
                    "status": "skipped",
                    "reason": "inactive",
                    "company_id": company_id,
                    "days_since_activity": days_since
                }

        # 2. Récupérer infos entreprise
        company = await get_company_info(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        company_name = company["name"]

        # 3. Calculer les dates
        start_date, end_date = calculate_period_dates(frequency, end_date)
        period_range = format_period_range(start_date, end_date, frequency)

        # 4. Générer le rapport
        kpis = await calculate_kpis(company_id, start_date, end_date)
        kpis_comparison = await compare_kpis(company_id, start_date, end_date, frequency)
        insights = await extract_all_insights(company_id, start_date, end_date)
        last_year_kpis = await get_last_year_comparison(company_id, start_date, end_date)

        recommendations = await generate_recommendations(
            company_name=company_name,
            period_range=period_range,
            kpis=kpis,
            kpis_comparison=kpis_comparison,
            insights=insights,
            last_year_kpis=last_year_kpis
        )

        # 5. Formater le message
        message = format_whatsapp_message(
            company_name=company_name,
            period_range=period_range,
            kpis=kpis,
            kpis_comparison=kpis_comparison,
            insights=insights,
            recommendations=recommendations
        )

        # 6. Déterminer destinataire
        if not recipient:
            recipient = company.get("whatsapp_number")
            if not recipient:
                raise ValueError("No recipient specified and no WhatsApp number configured")

        # 7. Envoyer
        if delivery_method == DeliveryMethod.WHATSAPP:
            send_success = await send_whatsapp_message(recipient, message)
        else:
            send_success = await send_telegram_message(recipient, message)

        # 8. Retourner résultat
        return {
            "status": "success" if send_success else "failed",
            "company_id": company_id,
            "company_name": company_name,
            "recipient": recipient,
            "delivery_method": delivery_method.value
        }

    except Exception as e:
        logger.error(
            f"Failed to generate and send report: {e}",
            extra={"company_id": company_id},
            exc_info=True
        )
        return {
            "status": "failed",
            "company_id": company_id,
            "error": str(e)
        }
