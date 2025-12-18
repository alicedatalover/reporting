-- ============================================================
-- scripts/sql/add_indexes.sql
-- INDEXES CRITIQUES POUR PERFORMANCE
-- Genuka KPI Engine
-- ============================================================

-- Ces indexes optimisent les requêtes fréquentes du KPI Engine
-- À exécuter AVANT le déploiement en production

-- ============================================================
-- TABLE: orders (Commandes)
-- ============================================================

-- Index pour requêtes par entreprise et période
CREATE INDEX IF NOT EXISTS idx_orders_company_date 
ON orders (company_id, created_at, deleted_at, status);

-- Index pour calcul CA
CREATE INDEX IF NOT EXISTS idx_orders_company_amount 
ON orders (company_id, amount, deleted_at, status);

-- Index pour recherche par client
CREATE INDEX IF NOT EXISTS idx_orders_customer 
ON orders (customer_id, created_at, deleted_at);

-- Index pour statut
CREATE INDEX IF NOT EXISTS idx_orders_status 
ON orders (status, deleted_at);


-- ============================================================
-- TABLE: customers (Clients)
-- ============================================================

-- Index pour nouveaux clients par période
CREATE INDEX IF NOT EXISTS idx_customers_company_date 
ON customers (company_id, created_at, deleted_at);

-- Index pour recherche par email/phone
CREATE INDEX IF NOT EXISTS idx_customers_email 
ON customers (email, deleted_at);

CREATE INDEX IF NOT EXISTS idx_customers_phone 
ON customers (phone, deleted_at);


-- ============================================================
-- TABLE: bills (Dépenses)
-- ============================================================

-- Index pour calcul dépenses par période
CREATE INDEX IF NOT EXISTS idx_bills_company_date 
ON bills (company_id, created_at, deleted_at);

-- Index pour montant et type
CREATE INDEX IF NOT EXISTS idx_bills_amount_type 
ON bills (company_id, expense_type, amount, deleted_at);


-- ============================================================
-- TABLE: stocks
-- ============================================================

-- Index pour alertes de stock
CREATE INDEX IF NOT EXISTS idx_stocks_company_alert 
ON stocks (company_id, quantity_alert);


-- ============================================================
-- TABLE: stock_warehouse
-- ============================================================

-- Index pour quantités par stock
CREATE INDEX IF NOT EXISTS idx_stock_warehouse_stock 
ON stock_warehouse (stock_id, quantity);


-- ============================================================
-- TABLE: stock_histories
-- ============================================================

-- Index pour mouvements de stock
CREATE INDEX IF NOT EXISTS idx_stock_histories_date 
ON stock_histories (company_id, date);


-- ============================================================
-- TABLE: companies
-- ============================================================

-- Index pour recherche par handle
CREATE INDEX IF NOT EXISTS idx_companies_handle 
ON companies (handle);


-- ============================================================
-- VÉRIFICATION
-- ============================================================

-- Afficher tous les indexes des tables critiques
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME,
    SEQ_IN_INDEX,
    INDEX_TYPE
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'genuka'
  AND TABLE_NAME IN ('orders', 'customers', 'bills', 'stocks', 'companies')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;


-- ============================================================
-- STATISTIQUES
-- ============================================================

-- Analyser les tables pour optimiser les requêtes
ANALYZE TABLE orders;
ANALYZE TABLE customers;
ANALYZE TABLE bills;
ANALYZE TABLE stocks;
ANALYZE TABLE stock_warehouse;
ANALYZE TABLE companies;
ANALYZE TABLE report_configs;
ANALYZE TABLE report_history;

-- Résumé
SELECT 'Indexes créés avec succès' AS status;