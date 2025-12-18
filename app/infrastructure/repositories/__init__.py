# app/infrastructure/repositories/__init__.py
"""
Repositories pour l'accès aux données.

Expose tous les repositories pour faciliter les imports.
"""

from app.infrastructure.repositories.base import AbstractRepository, BaseRepository
from app.infrastructure.repositories.company_repo import CompanyRepository
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.repositories.customer_repo import CustomerRepository
from app.infrastructure.repositories.stock_repo import StockRepository
from app.infrastructure.repositories.expense_repo import ExpenseRepository
from app.infrastructure.repositories.report_config_repo import ReportConfigRepository

__all__ = [
    "AbstractRepository",
    "BaseRepository",
    "CompanyRepository",
    "OrderRepository",
    "CustomerRepository",
    "StockRepository",
    "ExpenseRepository",
    "ReportConfigRepository",
]