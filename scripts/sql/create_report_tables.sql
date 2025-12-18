-- ============================================================
-- scripts/sql/create_report_tables.sql
-- TABLES POUR LE SYSTÈME DE RAPPORTS
-- Genuka KPI Engine
-- ============================================================
-- ============================================================
-- INDEXES CRITIQUES (VERSION SIMPLIFIÉE)
-- ============================================================

USE genuka;

-- TABLE: orders
CREATE INDEX IF NOT EXISTS idx_orders_company_date 
ON orders (company_id, created_at, deleted_at, status);

CREATE INDEX IF NOT EXISTS idx_orders_company_amount 
ON orders (company_id, amount, deleted_at, status);

CREATE INDEX IF NOT EXISTS idx_orders_customer 
ON orders (customer_id, created_at, deleted_at);

CREATE INDEX IF NOT EXISTS idx_orders_status 
ON orders (status, deleted_at);

-- TABLE: customers
CREATE INDEX IF NOT EXISTS idx_customers_company_date 
ON customers (company_id, created_at, deleted_at);

CREATE INDEX IF NOT EXISTS idx_customers_email 
ON customers (email, deleted_at);

CREATE INDEX IF NOT EXISTS idx_customers_phone 
ON customers (phone, deleted_at);

-- TABLE: bills
CREATE INDEX IF NOT EXISTS idx_bills_company_date 
ON bills (company_id, created_at, deleted_at);

CREATE INDEX IF NOT EXISTS idx_bills_amount_type 
ON bills (company_id, expense_type, amount, deleted_at);

-- TABLE: stocks
CREATE INDEX IF NOT EXISTS idx_stocks_company_alert 
ON stocks (company_id, quantity_alert);

-- TABLE: stock_warehouse
CREATE INDEX IF NOT EXISTS idx_stock_warehouse_stock 
ON stock_warehouse (stock_id, quantity);

-- TABLE: stock_histories
CREATE INDEX IF NOT EXISTS idx_stock_histories_date 
ON stock_histories (company_id, date);

-- TABLE: companies
CREATE INDEX IF NOT EXISTS idx_companies_handle 
ON companies (handle);

-- Résumé
SELECT 'Indexes créés avec succès' AS status;