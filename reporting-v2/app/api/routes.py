"""
Routes API pour Genuka KPI Engine V2.
Contient tous les endpoints : health, reports, admin.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Optional, List
from datetime import datetime, date
import logging

from app.models import (
    GenerateReportRequest,
    PreviewReportRequest,
    ReportConfigCreate,
    ReportConfigResponse,
    ReportHistoryResponse,
    ReportData,
    ReportFrequency,
    DeliveryMethod
)
from app.core.database import (
    test_connection,
    get_company_info,
    get_last_activity_date,
    execute_query,
    execute_one,
    execute_insert
)
from app.core.kpi import (
    calculate_period_dates,
    format_period_range,
    calculate_kpis,
    compare_kpis,
    get_last_year_comparison
)
from app.core.insights import extract_all_insights
from app.core.recommendations import (
    generate_recommendations,
    test_gemini_connection
)
from app.notifications.whatsapp import (
    format_whatsapp_message,
    send_whatsapp_message,
    test_whatsapp_connection
)
from app.notifications.telegram import (
    send_telegram_message,
    test_telegram_connection
)
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== HEALTH CHECK ====================

@router.get("/health/detailed")
async def detailed_health_check():
    """
    Health check détaillé de tous les services.

    Returns:
        Statut de : database, redis, gemini, whatsapp, telegram
    """
    checks = {}

    # Database
    db_ok = await test_connection()
    checks["database"] = {
        "status": "healthy" if db_ok else "unhealthy",
        "host": settings.DB_HOST,
        "database": settings.DB_NAME
    }

    # Gemini AI
    gemini_ok = await test_gemini_connection()
    checks["gemini"] = {
        "status": "healthy" if gemini_ok else "unhealthy",
        "model": settings.GEMINI_MODEL,
        "configured": bool(settings.GOOGLE_API_KEY)
    }

    # WhatsApp
    whatsapp_ok = await test_whatsapp_connection()
    checks["whatsapp"] = {
        "status": "configured" if whatsapp_ok else "not_configured",
        "enabled": bool(settings.WHATSAPP_API_TOKEN)
    }

    # Telegram
    telegram_ok = await test_telegram_connection()
    checks["telegram"] = {
        "status": "configured" if telegram_ok else "not_configured",
        "enabled": bool(settings.TELEGRAM_BOT_TOKEN)
    }

    # Status global
    all_critical_ok = db_ok and gemini_ok
    overall_status = "healthy" if all_critical_ok else "unhealthy"

    return {
        "status": overall_status,
        "checks": checks
    }


# ==================== REPORTS ====================

@router.post("/reports/preview")
async def preview_report(request: PreviewReportRequest):
    """
    Prévisualise un rapport sans l'envoyer.
    Utile pour tester la génération avant envoi réel.

    Args:
        request: company_id, frequency, end_date (optionnel)

    Returns:
        Rapport complet formaté

    Example:
        POST /api/v1/reports/preview
        {
          "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
          "frequency": "weekly",
          "end_date": "2026-01-19"
        }
    """
    try:
        # Vérifier que l'entreprise existe
        company = await get_company_info(request.company_id)
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company {request.company_id} not found"
            )

        # Calculer les dates
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date() if request.end_date else None
        start_date, end_date = calculate_period_dates(request.frequency, end_date)
        period_range = format_period_range(start_date, end_date, request.frequency)

        # Générer le rapport
        report_data = await _generate_report_data(
            company_id=request.company_id,
            company_name=company["name"],
            frequency=request.frequency,
            start_date=start_date,
            end_date=end_date,
            period_range=period_range
        )

        # Formater le message
        message = format_whatsapp_message(
            company_name=company["name"],
            period_range=period_range,
            kpis=report_data["kpis"],
            kpis_comparison=report_data["kpis_comparison"],
            insights=report_data["insights"],
            recommendations=report_data["recommendations"]
        )

        return {
            "company_name": company["name"],
            "period_range": period_range,
            "kpis": report_data["kpis"].dict(),
            "kpis_comparison": report_data["kpis_comparison"].dict(),
            "insights": [i.dict() for i in report_data["insights"]],
            "recommendations": report_data["recommendations"],
            "formatted_message": message
        }

    except Exception as e:
        logger.error(f"Failed to generate report preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report preview: {str(e)}"
        )


@router.post("/reports/generate")
async def generate_report(request: GenerateReportRequest):
    """
    Génère un rapport et l'envoie via WhatsApp ou Telegram.

    Args:
        request: company_id, frequency, end_date, recipient, delivery_method

    Returns:
        Statut de l'envoi

    Example:
        POST /api/v1/reports/generate
        {
          "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
          "frequency": "weekly",
          "recipient": "+237658173627",
          "delivery_method": "whatsapp"
        }
    """
    try:
        # Vérifier que l'entreprise existe
        company = await get_company_info(request.company_id)
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company {request.company_id} not found"
            )

        # Vérifier filtrage activité (30 jours)
        last_activity = await get_last_activity_date(request.company_id)
        if last_activity:
            days_since_activity = (settings.get_current_date() - datetime.strptime(last_activity, "%Y-%m-%d").date()).days
            if days_since_activity > settings.INACTIVE_DAYS_THRESHOLD:
                return {
                    "status": "skipped",
                    "reason": "inactive",
                    "message": f"No sales in last {settings.INACTIVE_DAYS_THRESHOLD} days",
                    "last_activity": last_activity
                }

        # Calculer les dates
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date() if request.end_date else None
        start_date, end_date = calculate_period_dates(request.frequency, end_date)
        period_range = format_period_range(start_date, end_date, request.frequency)

        # Générer le rapport
        report_data = await _generate_report_data(
            company_id=request.company_id,
            company_name=company["name"],
            frequency=request.frequency,
            start_date=start_date,
            end_date=end_date,
            period_range=period_range
        )

        # Formater le message
        message = format_whatsapp_message(
            company_name=company["name"],
            period_range=period_range,
            kpis=report_data["kpis"],
            kpis_comparison=report_data["kpis_comparison"],
            insights=report_data["insights"],
            recommendations=report_data["recommendations"]
        )

        # Déterminer le destinataire
        recipient = request.recipient
        if not recipient:
            recipient = company.get("whatsapp_number")
            if not recipient:
                raise HTTPException(
                    status_code=400,
                    detail="No recipient specified and no WhatsApp number configured for company"
                )

        # Envoyer
        if request.delivery_method == DeliveryMethod.WHATSAPP:
            success = await send_whatsapp_message(recipient, message)
        else:  # Telegram
            success = await send_telegram_message(recipient, message)

        # Sauvegarder dans l'historique
        await _save_report_history(
            company_id=request.company_id,
            frequency=request.frequency,
            start_date=start_date,
            end_date=end_date,
            report_data=report_data,
            success=success,
            recipient=recipient,
            delivery_method=request.delivery_method
        )

        return {
            "status": "success" if success else "failed",
            "company_name": company["name"],
            "recipient": recipient,
            "delivery_method": request.delivery_method.value,
            "period_range": period_range
        }

    except Exception as e:
        logger.error(f"Failed to generate and send report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate and send report: {str(e)}"
        )


# ==================== ADMIN - CONFIGS ====================

@router.get("/admin/companies/configs", response_model=List[ReportConfigResponse])
async def list_report_configs(enabled: Optional[bool] = None):
    """
    Liste toutes les configurations de rapports.

    Args:
        enabled: Filtrer par statut activé (optionnel)

    Returns:
        Liste des configurations
    """
    query = """
        SELECT
            rc.company_id,
            c.name as company_name,
            rc.frequency,
            rc.enabled,
            rc.whatsapp_number,
            rc.last_activity_date,
            rc.next_report_date,
            rc.created_at,
            rc.updated_at
        FROM report_configs rc
        JOIN companies c ON rc.company_id = c.id
    """

    if enabled is not None:
        query += f" WHERE rc.enabled = {1 if enabled else 0}"

    query += " ORDER BY c.name ASC"

    results = await execute_query(query)
    return results


@router.post("/admin/companies/{company_id}/config")
async def create_or_update_config(company_id: str, config: ReportConfigCreate):
    """
    Crée ou met à jour la configuration de rapport pour une entreprise.

    Args:
        company_id: ID de l'entreprise
        config: Configuration (frequency, enabled, whatsapp_number)

    Returns:
        Configuration créée/mise à jour
    """
    # Vérifier que l'entreprise existe
    company = await get_company_info(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Récupérer la dernière activité
    last_activity = await get_last_activity_date(company_id)

    # Insert ou update
    query = """
        INSERT INTO report_configs
            (company_id, frequency, enabled, whatsapp_number, last_activity_date)
        VALUES
            (:company_id, :frequency, :enabled, :whatsapp_number, :last_activity_date)
        ON DUPLICATE KEY UPDATE
            frequency = :frequency,
            enabled = :enabled,
            whatsapp_number = :whatsapp_number,
            last_activity_date = :last_activity_date,
            updated_at = NOW()
    """

    await execute_insert(query, {
        "company_id": company_id,
        "frequency": config.frequency.value,
        "enabled": config.enabled,
        "whatsapp_number": config.whatsapp_number,
        "last_activity_date": last_activity
    })

    # Retourner la config
    result = await execute_one(
        """
        SELECT
            rc.company_id,
            c.name as company_name,
            rc.frequency,
            rc.enabled,
            rc.whatsapp_number,
            rc.last_activity_date,
            rc.next_report_date,
            rc.created_at,
            rc.updated_at
        FROM report_configs rc
        JOIN companies c ON rc.company_id = c.id
        WHERE rc.company_id = :company_id
        """,
        {"company_id": company_id}
    )

    return result


@router.delete("/admin/companies/{company_id}/config")
async def delete_config(company_id: str):
    """Supprime la configuration de rapport pour une entreprise."""
    await execute_insert(
        "DELETE FROM report_configs WHERE company_id = :company_id",
        {"company_id": company_id}
    )
    return {"message": "Configuration deleted"}


# ==================== ADMIN - HISTORIQUE ====================

@router.get("/admin/companies/{company_id}/history", response_model=List[ReportHistoryResponse])
async def get_company_history(company_id: str, limit: int = 10):
    """
    Récupère l'historique des rapports d'une entreprise.

    Args:
        company_id: ID de l'entreprise
        limit: Nombre max de rapports à retourner

    Returns:
        Liste des rapports envoyés
    """
    query = """
        SELECT
            id,
            company_id,
            frequency,
            period_start,
            period_end,
            status,
            delivery_method,
            recipient,
            error_message,
            execution_time_ms,
            sent_at
        FROM report_history
        WHERE company_id = :company_id
        ORDER BY sent_at DESC
        LIMIT :limit
    """

    results = await execute_query(query, {
        "company_id": company_id,
        "limit": limit
    })

    return results


# ==================== HELPERS ====================

async def _generate_report_data(
    company_id: str,
    company_name: str,
    frequency: ReportFrequency,
    start_date: date,
    end_date: date,
    period_range: str
) -> dict:
    """Génère toutes les données du rapport (helper interne)."""

    # 1. Calculer les KPIs
    kpis = await calculate_kpis(company_id, start_date, end_date)

    # 2. Comparer avec période précédente
    kpis_comparison = await compare_kpis(company_id, start_date, end_date, frequency)

    # 3. Extraire les insights
    insights = await extract_all_insights(company_id, start_date, end_date)

    # 4. Comparaison année passée (pour recommandations)
    last_year_kpis = await get_last_year_comparison(company_id, start_date, end_date)

    # 5. Générer les recommandations Gemini
    recommendations = await generate_recommendations(
        company_name=company_name,
        period_range=period_range,
        kpis=kpis,
        kpis_comparison=kpis_comparison,
        insights=insights,
        last_year_kpis=last_year_kpis
    )

    return {
        "kpis": kpis,
        "kpis_comparison": kpis_comparison,
        "insights": insights,
        "recommendations": recommendations
    }


async def _save_report_history(
    company_id: str,
    frequency: ReportFrequency,
    start_date: date,
    end_date: date,
    report_data: dict,
    success: bool,
    recipient: str,
    delivery_method: DeliveryMethod
):
    """Sauvegarde le rapport dans l'historique."""
    import json
    import uuid

    history_id = str(uuid.uuid4()).replace('-', '')[:26]

    query = """
        INSERT INTO report_history (
            id, company_id, frequency, period_start, period_end,
            kpis, insights, recommendations,
            status, delivery_method, recipient, sent_at
        ) VALUES (
            :id, :company_id, :frequency, :period_start, :period_end,
            :kpis, :insights, :recommendations,
            :status, :delivery_method, :recipient, NOW()
        )
    """

    await execute_insert(query, {
        "id": history_id,
        "company_id": company_id,
        "frequency": frequency.value,
        "period_start": start_date,
        "period_end": end_date,
        "kpis": json.dumps(report_data["kpis"].dict()),
        "insights": json.dumps([i.dict() for i in report_data["insights"]]),
        "recommendations": report_data["recommendations"],
        "status": "success" if success else "failed",
        "delivery_method": delivery_method.value,
        "recipient": recipient
    })
