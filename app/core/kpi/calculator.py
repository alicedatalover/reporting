# app/core/kpi/calculator.py
"""
Calculateur de KPIs

Calcule tous les indicateurs de performance pour une entreprise sur une période donnée.
"""

from datetime import date
from decimal import Decimal
from typing import Dict, Any
import logging

from app.domain.models import KPIData
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.repositories.customer_repo import CustomerRepository
from app.infrastructure.repositories.stock_repo import StockRepository
from app.infrastructure.repositories.expense_repo import ExpenseRepository

logger = logging.getLogger(__name__)


class KPICalculator:
    """
    Calculateur de KPIs pour les entreprises.
    
    Agrège les données de différents repositories pour produire
    un ensemble complet d'indicateurs de performance.
    """
    
    def __init__(
        self,
        order_repo: OrderRepository,
        customer_repo: CustomerRepository,
        stock_repo: StockRepository,
        expense_repo: ExpenseRepository
    ):
        """
        Initialise le calculateur avec les repositories nécessaires.
        
        Args:
            order_repo: Repository des commandes
            customer_repo: Repository des clients
            stock_repo: Repository des stocks
            expense_repo: Repository des dépenses
        """
        self.order_repo = order_repo
        self.customer_repo = customer_repo
        self.stock_repo = stock_repo
        self.expense_repo = expense_repo
    
    async def calculate(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> KPIData:
        """
        Calcule tous les KPIs pour une période.
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début de la période
            end_date: Date de fin de la période
        
        Returns:
            KPIData avec tous les indicateurs calculés
        
        Example:
            >>> calculator = KPICalculator(order_repo, customer_repo, stock_repo, expense_repo)
            >>> kpis = await calculator.calculate("company_123", date(2025, 7, 1), date(2025, 7, 31))
            >>> print(f"CA: {kpis.total_revenue}")
        """
        
        logger.info(
            "Calculating KPIs",
            extra={
                "company_id": company_id,
                "start_date": str(start_date),
                "end_date": str(end_date)
            }
        )
        
        # Calcul en parallèle de tous les KPIs
        try:
            # KPIs de ventes (optimisé en une seule requête)
            sales_kpis = await self.order_repo.calculate_sales_kpis(
                company_id, start_date, end_date
            )
            total_revenue = sales_kpis['total_revenue']
            total_sales = sales_kpis['total_sales']
            
            # KPIs clients
            new_customers = await self.customer_repo.count_new_customers(
                company_id, start_date, end_date
            )
            
            returning_customers = await self.customer_repo.count_returning_customers(
                company_id, start_date, end_date
            )
            
            # KPIs stock
            stock_alerts_count = await self.stock_repo.count_stock_alerts(company_id)
            
            # KPIs dépenses
            total_expenses = await self.expense_repo.calculate_total_expenses(
                company_id, start_date, end_date
            )
            
            # Calcul résultat net
            net_result = total_revenue - total_expenses
            
            kpis = KPIData(
                total_revenue=total_revenue,
                total_sales=total_sales,
                new_customers=new_customers,
                returning_customers=returning_customers,
                stock_alerts_count=stock_alerts_count,
                total_expenses=total_expenses,
                net_result=net_result
            )
            
            logger.info(
                "KPIs calculated successfully",
                extra={
                    "company_id": company_id,
                    "revenue": float(total_revenue),
                    "sales": total_sales,
                    "net_result": float(net_result)
                }
            )
            
            return kpis
            
        except Exception as e:
            logger.error(
                "Failed to calculate KPIs",
                extra={"company_id": company_id, "error": str(e)},
                exc_info=True
            )
            raise
    
    async def calculate_average_order_value(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> Decimal:
        """
        Calcule le panier moyen (AOV - Average Order Value).
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Panier moyen en XAF
        """
        total_revenue = await self.order_repo.calculate_revenue_for_period(
            company_id, start_date, end_date
        )
        
        total_sales = await self.order_repo.count_sales_for_period(
            company_id, start_date, end_date
        )
        
        if total_sales == 0:
            return Decimal("0")
        
        return total_revenue / Decimal(total_sales)
    
    async def calculate_customer_retention_rate(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> float:
        """
        Calcule le taux de rétention client.
        
        Formule: (Clients récurrents / Total clients actifs) * 100
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Taux de rétention en %
        """
        new_customers = await self.customer_repo.count_new_customers(
            company_id, start_date, end_date
        )
        
        returning_customers = await self.customer_repo.count_returning_customers(
            company_id, start_date, end_date
        )
        
        total_active_customers = new_customers + returning_customers
        
        if total_active_customers == 0:
            return 0.0
        
        return (returning_customers / total_active_customers) * 100
    
    async def calculate_profit_margin(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> float:
        """
        Calcule la marge bénéficiaire.
        
        Formule: (Résultat net / CA) * 100
        
        Args:
            company_id: ID de l'entreprise
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Marge en %
        """
        total_revenue = await self.order_repo.calculate_revenue_for_period(
            company_id, start_date, end_date
        )
        
        total_expenses = await self.expense_repo.calculate_total_expenses(
            company_id, start_date, end_date
        )
        
        if total_revenue == 0:
            return 0.0
        
        net_result = total_revenue - total_expenses
        
        return float((net_result / total_revenue) * 100)