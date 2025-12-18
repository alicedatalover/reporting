USE genuka;

-- Supprimer si existe (au cas où)
DROP TABLE IF EXISTS report_history;

-- Créer SANS foreign key
CREATE TABLE report_history (
    id CHAR(26) PRIMARY KEY COMMENT 'ULID unique',
    company_id CHAR(26) NOT NULL COMMENT 'ID entreprise',
    report_type ENUM('weekly', 'monthly', 'quarterly') NOT NULL COMMENT 'Type de rapport',
    period_start DATE NOT NULL COMMENT 'Date de début de période',
    period_end DATE NOT NULL COMMENT 'Date de fin de période',
    status ENUM('success', 'failed', 'pending') NOT NULL DEFAULT 'pending' COMMENT 'Statut de génération',
    delivery_method ENUM('whatsapp', 'telegram', 'email') NOT NULL DEFAULT 'whatsapp' COMMENT 'Méthode d\'envoi',
    recipient VARCHAR(255) DEFAULT NULL COMMENT 'Destinataire (numéro/email)',
    kpis JSON DEFAULT NULL COMMENT 'KPIs calculés (JSON)',
    insights JSON DEFAULT NULL COMMENT 'Insights détectés (JSON)',
    recommendations TEXT DEFAULT NULL COMMENT 'Recommandations générées',
    error_message TEXT DEFAULT NULL COMMENT 'Message d\'erreur si échec',
    execution_time_ms INT DEFAULT NULL COMMENT 'Temps d\'exécution en millisecondes',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création',
    
    INDEX idx_company_date (company_id, created_at),
    INDEX idx_status (status),
    INDEX idx_period (period_start, period_end),
    INDEX idx_type_status (report_type, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci COMMENT='Historique des rapports générés';

-- Vérifier
SHOW TABLES LIKE 'report%';
DESCRIBE report_history;

SELECT 'Table report_history créée avec succès' AS status;