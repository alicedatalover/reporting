-- =========================================================================
-- Script de seed pour la base de données Genuka
-- Crée des données de test pour développement
-- =========================================================================

-- Utiliser la base genuka
USE genuka;

-- ==================== COMPANIES ====================

INSERT INTO companies (id, name, handle, company_code, description, currency_code, currency_name, type, created_at, updated_at)
VALUES
    (
        '01hjt9qsj7b039ww1nyrn9kg5t',
        'Boulangerie du Coin',
        'boulangerie-du-coin',
        'BOUL001',
        'Boulangerie artisanale proposant pains et viennoiseries',
        'XAF',
        'Franc CFA',
        'retail',
        NOW(),
        NOW()
    ),
    (
        'company_123',
        'Boutique Mode Élégante',
        'boutique-mode',
        'MODE001',
        'Boutique de vêtements et accessoires',
        'XAF',
        'Franc CFA',
        'retail',
        NOW(),
        NOW()
    ),
    (
        'company_456',
        'Restaurant Saveur Africaine',
        'restaurant-saveur',
        'REST001',
        'Restaurant spécialisé en cuisine africaine',
        'XAF',
        'Franc CFA',
        'restaurant',
        NOW(),
        NOW()
    );

-- ==================== REPORT_CONFIG ====================

INSERT INTO report_config (id, company_id, is_active, frequency, delivery_method, recipient, created_at, updated_at)
VALUES
    (
        CONCAT('cfg_', UUID()),
        '01hjt9qsj7b039ww1nyrn9kg5t',
        1,
        'weekly',
        'whatsapp',
        '+237658173627',
        NOW(),
        NOW()
    ),
    (
        CONCAT('cfg_', UUID()),
        'company_123',
        1,
        'monthly',
        'telegram',
        '123456789',
        NOW(),
        NOW()
    );

-- ==================== ORDERS (Données factices pour tester) ====================

-- Commandes pour Boulangerie du Coin (30 derniers jours)
INSERT INTO orders (id, company_id, customer_id, total_amount, status, created_at, updated_at)
SELECT
    CONCAT('order_', UUID()),
    '01hjt9qsj7b039ww1nyrn9kg5t',
    CONCAT('cust_', FLOOR(RAND() * 50)),
    ROUND(500 + (RAND() * 4500), 2),
    'completed',
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY),
    NOW()
FROM
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t1,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t2,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t3
LIMIT 50;

-- Commandes pour Boutique Mode (30 derniers jours)
INSERT INTO orders (id, company_id, customer_id, total_amount, status, created_at, updated_at)
SELECT
    CONCAT('order_', UUID()),
    'company_123',
    CONCAT('cust_', FLOOR(RAND() * 40)),
    ROUND(2000 + (RAND() * 18000), 2),
    'completed',
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY),
    NOW()
FROM
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) t1,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) t2,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) t3
LIMIT 40;

-- ==================== CUSTOMERS ====================

-- Clients pour Boulangerie
INSERT INTO customers (id, company_id, name, phone, email, created_at, updated_at, last_order_date)
SELECT
    CONCAT('cust_', n),
    '01hjt9qsj7b039ww1nyrn9kg5t',
    CONCAT('Client ', n),
    CONCAT('+23765', LPAD(n, 7, '0')),
    CONCAT('client', n, '@example.cm'),
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 180) DAY),
    NOW(),
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY)
FROM
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
     UNION SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15
     UNION SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION SELECT 20
     UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24 UNION SELECT 25
     UNION SELECT 26 UNION SELECT 27 UNION SELECT 28 UNION SELECT 29 UNION SELECT 30
     UNION SELECT 31 UNION SELECT 32 UNION SELECT 33 UNION SELECT 34 UNION SELECT 35
     UNION SELECT 36 UNION SELECT 37 UNION SELECT 38 UNION SELECT 39 UNION SELECT 40
     UNION SELECT 41 UNION SELECT 42 UNION SELECT 43 UNION SELECT 44 UNION SELECT 45
     UNION SELECT 46 UNION SELECT 47 UNION SELECT 48 UNION SELECT 49 UNION SELECT 50) numbers;

-- ==================== PRODUCTS ====================

INSERT INTO products (id, company_id, name, sku, price, created_at, updated_at)
VALUES
    ('prod_1', '01hjt9qsj7b039ww1nyrn9kg5t', 'Pain Blanc', 'PAIN001', 500, NOW(), NOW()),
    ('prod_2', '01hjt9qsj7b039ww1nyrn9kg5t', 'Croissant', 'CROI001', 300, NOW(), NOW()),
    ('prod_3', '01hjt9qsj7b039ww1nyrn9kg5t', 'Baguette', 'BAGU001', 400, NOW(), NOW()),
    ('prod_4', 'company_123', 'T-shirt', 'TSHI001', 5000, NOW(), NOW()),
    ('prod_5', 'company_123', 'Pantalon', 'PANT001', 12000, NOW(), NOW());

-- ==================== STOCK ====================

INSERT INTO stock (id, company_id, product_id, quantity, min_threshold, created_at, updated_at)
VALUES
    ('stock_1', '01hjt9qsj7b039ww1nyrn9kg5t', 'prod_1', 50, 20, NOW(), NOW()),
    ('stock_2', '01hjt9qsj7b039ww1nyrn9kg5t', 'prod_2', 5, 15, NOW(), NOW()),  -- Stock bas !
    ('stock_3', '01hjt9qsj7b039ww1nyrn9kg5t', 'prod_3', 35, 10, NOW(), NOW()),
    ('stock_4', 'company_123', 'prod_4', 120, 20, NOW(), NOW()),
    ('stock_5', 'company_123', 'prod_5', 45, 10, NOW(), NOW());

-- ==================== EXPENSES ====================

-- Dépenses pour Boulangerie (mois en cours)
INSERT INTO expenses (id, company_id, category, amount, description, expense_date, created_at, updated_at)
VALUES
    ('exp_1', '01hjt9qsj7b039ww1nyrn9kg5t', 'Matières premières', 15000, 'Achat farine et levure', DATE_SUB(NOW(), INTERVAL 5 DAY), NOW(), NOW()),
    ('exp_2', '01hjt9qsj7b039ww1nyrn9kg5t', 'Électricité', 8000, 'Facture électricité', DATE_SUB(NOW(), INTERVAL 10 DAY), NOW(), NOW()),
    ('exp_3', '01hjt9qsj7b039ww1nyrn9kg5t', 'Salaires', 45000, 'Salaires employés', DATE_SUB(NOW(), INTERVAL 1 DAY), NOW(), NOW());

-- ==================== ORDER_ITEMS ====================

-- Articles de commande (pour top produits)
INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, created_at, updated_at)
SELECT
    CONCAT('item_', UUID()),
    o.id,
    CASE
        WHEN RAND() < 0.4 THEN 'prod_1'
        WHEN RAND() < 0.7 THEN 'prod_2'
        ELSE 'prod_3'
    END,
    FLOOR(1 + RAND() * 5),
    CASE
        WHEN RAND() < 0.4 THEN 500
        WHEN RAND() < 0.7 THEN 300
        ELSE 400
    END,
    NOW(),
    NOW()
FROM orders o
WHERE o.company_id = '01hjt9qsj7b039ww1nyrn9kg5t'
LIMIT 100;

-- ==================== REPORT_HISTORY ====================

INSERT INTO report_history (id, company_id, report_type, period_start, period_end, status, delivery_method, recipient, execution_time_ms, created_at)
VALUES
    (
        CONCAT('hist_', UUID()),
        '01hjt9qsj7b039ww1nyrn9kg5t',
        'weekly',
        DATE_SUB(CURDATE(), INTERVAL 7 DAY),
        CURDATE(),
        'success',
        'whatsapp',
        '+237658173627',
        2340,
        DATE_SUB(NOW(), INTERVAL 2 DAY)
    ),
    (
        CONCAT('hist_', UUID()),
        'company_123',
        'monthly',
        DATE_SUB(CURDATE(), INTERVAL 30 DAY),
        CURDATE(),
        'success',
        'telegram',
        '123456789',
        3120,
        DATE_SUB(NOW(), INTERVAL 5 DAY)
    );

-- =========================================================================
-- Vérification des données insérées
-- =========================================================================

SELECT '=== COMPANIES ===' AS '';
SELECT COUNT(*) AS total_companies FROM companies;

SELECT '=== ORDERS ===' AS '';
SELECT company_id, COUNT(*) AS total_orders, SUM(total_amount) AS total_revenue
FROM orders
GROUP BY company_id;

SELECT '=== CUSTOMERS ===' AS '';
SELECT COUNT(*) AS total_customers FROM customers;

SELECT '=== PRODUCTS ===' AS '';
SELECT COUNT(*) AS total_products FROM products;

SELECT 'Données de test créées avec succès !' AS message;
