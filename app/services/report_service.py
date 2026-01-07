# app/services/report_service.py
"""
Service de génération de rapports.

Orchestre toute la logique de génération d'un rapport :
- Calcul KPIs
- Extraction insights
- Génération recommandations
- Formatage message
"""

from datetime import date, timedelta
from typing import Dict, Any, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.timezone import today_in_timezone
from app.domain.models import KPIData, KPIComparison, InsightModel, ReportData
from app.domain.enums import ReportFrequency
from app.infrastructure.repositories import (
    CompanyRepository,
    OrderRepository,
    CustomerRepository,
    StockRepository,
    ExpenseRepository,
)
from app.core.kpi.calculator import KPICalculator
from app.core.kpi.comparator import KPIComparator
from app.core.insights.selector import InsightSelector
from app.core.insights.miners import (
    StockAlertMiner,
    ChurnRiskMiner,
    SeasonalityMiner,
    ProfitMarginMiner,
)
from app.core.recommendations.generator import RecommendationsGenerator
from app.infrastructure.external.gemini_client import GeminiClient
from app.config import settings

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service de génération de rapports d'activité.
    
    Coordonne tous les composants pour produire un rapport complet
    avec KPIs, insights et recommandations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialise le service avec une session DB.
        
        Args:
            session: Session SQLAlchemy async
        """
        self.session = session
        
        # Initialiser les repositories
        self.company_repo = CompanyRepository(session)
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.stock_repo = StockRepository(session)
        self.expense_repo = ExpenseRepository(session)
        
        # Initialiser les calculateurs
        self.kpi_calculator = KPICalculator(
            order_repo=self.order_repo,
            customer_repo=self.customer_repo,
            stock_repo=self.stock_repo,
            expense_repo=self.expense_repo
        )
        
        self.kpi_comparator = KPIComparator(self.kpi_calculator)
        
        # Initialiser les miners
        self.insight_miners = [
            StockAlertMiner(self.stock_repo),
            ChurnRiskMiner(self.customer_repo),
            SeasonalityMiner(self.order_repo),
            ProfitMarginMiner(self.order_repo, self.expense_repo),
        ]
        
        self.insight_selector = InsightSelector()
        
        # Initialiser le générateur de recommandations
        try:
            gemini_client = GeminiClient(settings) if settings.GOOGLE_API_KEY else None
            self.recommendations_generator = RecommendationsGenerator(gemini_client)
        except Exception as e:
            logger.warning(
                "Failed to initialize Gemini client",
                extra={"error": str(e)}
            )
            self.recommendations_generator = RecommendationsGenerator(None)
    
    async def generate_report(
        self,
        company_id: str,
        frequency: ReportFrequency,
        end_date: Optional[date] = None
    ) -> ReportData:
        """
        Génère un rapport complet pour une entreprise.
        
        Args:
            company_id: ID de l'entreprise
            frequency: Fréquence du rapport (weekly/monthly/quarterly)
            end_date: Date de fin (par défaut: aujourd'hui)
        
        Returns:
            ReportData avec tous les éléments du rapport
        
        Raises:
            ValueError: Si l'entreprise n'existe pas
            Exception: Si erreur lors de la génération
        
        Example:
            >>> service = ReportService(session)
            >>> report = await service.generate_report(
            ...     "company_123",
            ...     ReportFrequency.MONTHLY
            ... )
        """
        
        logger.info(
            "Starting report generation",
            extra={
                "company_id": company_id,
                "frequency": frequency.value,
                "end_date": str(end_date) if end_date else "today"
            }
        )
        
        try:
            # 1. Récupérer les infos de l'entreprise
            company_info = await self.company_repo.get_by_id(company_id)
            if not company_info:
                raise ValueError(f"Company {company_id} not found")
            
            company_name = company_info['name']
            
            # 2. Calculer les dates de la période
            start_date, end_date, period_name, period_range = self._calculate_period_dates(
                frequency, end_date
            )
            
            logger.info(
                "Period calculated",
                extra={
                    "company_id": company_id,
                    "start_date": str(start_date),
                    "end_date": str(end_date)
                }
            )
            
            # 3. Calculer les KPIs
            kpis = await self.kpi_calculator.calculate(
                company_id, start_date, end_date
            )
            
            # 4. Comparer avec période précédente
            kpis_comparison = await self.kpi_comparator.compare(
                company_id, start_date, end_date
            )
            
            # 5. Extraire les insights
            insights = await self._extract_insights(
                company_id, start_date, end_date, kpis
            )
            
            # 6. Sélectionner les top insights
            top_insights = self.insight_selector.select_top_insights(
                insights,
                max_count=settings.MAX_INSIGHTS_PER_REPORT
            )
            
            # 7. Générer les recommandations
            recommendations = await self.recommendations_generator.generate(
                company_name=company_name,
                period_name=period_name,
                period_range=period_range,
                kpis=kpis,
                kpis_comparison=kpis_comparison,
                insights=top_insights
            )
            
            # 8. Construire le rapport
            report_data = ReportData(
                company_name=company_name,
                period_name=period_name,
                period_range=period_range,
                kpis=kpis,
                kpis_comparison=kpis_comparison,
                insights=top_insights,
                recommendations=recommendations
            )
            
            logger.info(
                "Report generated successfully",
                extra={
                    "company_id": company_id,
                    "insights_count": len(top_insights),
                    "recommendations_length": len(recommendations)
                }
            )
            
            return report_data
            
        except Exception as e:
            logger.error(
                "Report generation failed",
                extra={
                    "company_id": company_id,
                    "frequency": frequency.value,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def _extract_insights(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        kpis: KPIData
    ) -> list[InsightModel]:
        """
        Exécute tous les miners et collecte les insights.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
            kpis: KPIs pré-calculés (contexte)
        
        Returns:
            Liste de tous les insights détectés
        """
        
        insights = []
        context = kpis.model_dump()
        
        for miner in self.insight_miners:
            try:
                insight = await miner.mine(
                    company_id=company_id,
                    start_date=start_date,
                    end_date=end_date,
                    context=context
                )
                
                if insight:
                    insights.append(insight)
                    logger.debug(
                        f"Insight detected by {miner.name}",
                        extra={
                            "company_id": company_id,
                            "insight_type": insight.type.value,
                            "priority": insight.priority
                        }
                    )
                    
            except Exception as e:
                logger.error(
                    f"Miner {miner.name} failed",
                    extra={
                        "company_id": company_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
                # Continuer avec les autres miners
                continue
        
        logger.info(
            "Insights extraction completed",
            extra={
                "company_id": company_id,
                "total_insights": len(insights)
            }
        )
        
        return insights
    
    @staticmethod
    def _calculate_period_dates(
        frequency: ReportFrequency,
        end_date: Optional[date] = None
    ) -> tuple[date, date, str, str]:
        """
        Calcule les dates de début et fin de période.
        
        Args:
            frequency: Fréquence du rapport
            end_date: Date de fin (par défaut: aujourd'hui)
        
        Returns:
            Tuple (start_date, end_date, period_name, period_range)
        
        Example:
            >>> start, end, name, range_str = _calculate_period_dates(
            ...     ReportFrequency.MONTHLY,
            ...     date(2025, 7, 31)
            ... )
            >>> # (date(2025, 7, 1), date(2025, 7, 31), "Mois", "01/07 - 31/07/2025")
        """
        
        if end_date is None:
            end_date = today_in_timezone()
        
        if frequency == ReportFrequency.WEEKLY:
            start_date = end_date - timedelta(days=6)
            period_name = "Semaine"
            
        elif frequency == ReportFrequency.MONTHLY:
            # Début du mois de end_date
            start_date = end_date.replace(day=1)
            period_name = "Mois"
            
        else:  # QUARTERLY
            # Début du trimestre
            quarter_month = ((end_date.month - 1) // 3) * 3 + 1
            start_date = end_date.replace(month=quarter_month, day=1)
            period_name = "Trimestre"
        
        # Formater la période
        period_range = f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
        
        return start_date, end_date, period_name, period_range