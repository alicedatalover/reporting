-- ================================================
-- Genuka KPI Engine V2 - Initial Tables
-- ================================================
-- Version: 1.0
-- Date: 2026-01-15
-- Description: Création des tables pour la gestion des rapports
-- ================================================

-- Table: report_configs
-- Description: Configuration de génération de rapports par entreprise
CREATE TABLE IF NOT EXISTS report_configs (
    company_id VARCHAR(26) PRIMARY KEY COMMENT 'ID ULID de l''entreprise',
    frequency ENUM('weekly', 'monthly') NOT NULL DEFAULT 'weekly' COMMENT 'Fréquence d''envoi des rapports',
    enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Activer/désactiver les rapports auto',
    whatsapp_number VARCHAR(20) DEFAULT NULL COMMENT 'Numéro WhatsApp (format: +237XXXXXXXXX)',
    last_activity_date DATE DEFAULT NULL COMMENT 'Date de la dernière vente (pour filtrage 30 jours)',
    next_report_date DATE DEFAULT NULL COMMENT 'Date prévue du prochain rapport (calculée par le système)',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de création de la config',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Date de dernière modification',

    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,

    INDEX idx_enabled (enabled),
    INDEX idx_frequency (frequency),
    INDEX idx_next_report_date (next_report_date),
    INDEX idx_last_activity (last_activity_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Configuration de génération de rapports par entreprise';

-- Table: report_history
-- Description: Historique de tous les rapports générés et envoyés
CREATE TABLE IF NOT EXISTS report_history (
    id VARCHAR(26) PRIMARY KEY COMMENT 'ID ULID unique du rapport',
    company_id VARCHAR(26) NOT NULL COMMENT 'ID de l''entreprise concernée',
    frequency ENUM('weekly', 'monthly') NOT NULL COMMENT 'Fréquence du rapport',
    period_start DATE NOT NULL COMMENT 'Date de début de la période analysée',
    period_end DATE NOT NULL COMMENT 'Date de fin de la période analysée',

    -- KPIs (stockés en JSON pour flexibilité)
    kpis JSON DEFAULT NULL COMMENT 'KPIs calculés (CA, ventes, panier moyen, etc.)',

    -- Insights & Recommendations
    insights JSON DEFAULT NULL COMMENT 'Insights détectés (stock, churn, saisonnalité, etc.)',
    recommendations TEXT DEFAULT NULL COMMENT 'Recommandations Gemini AI',

    -- Statut d''envoi
    status ENUM('success', 'failed', 'skipped') NOT NULL DEFAULT 'success' COMMENT 'Statut de la génération/envoi',
    error_message TEXT DEFAULT NULL COMMENT 'Message d''erreur si échec',
    delivery_method ENUM('whatsapp', 'telegram') DEFAULT NULL COMMENT 'Canal d''envoi utilisé',
    recipient VARCHAR(50) DEFAULT NULL COMMENT 'Destinataire (numéro ou chat_id)',

    -- Métadonnées
    execution_time_ms INT DEFAULT NULL COMMENT 'Temps d''exécution en millisecondes',
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Date d''envoi du rapport',

    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,

    INDEX idx_company_id (company_id),
    INDEX idx_status (status),
    INDEX idx_sent_at (sent_at),
    INDEX idx_period (period_start, period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Historique de tous les rapports générés';

-- ================================================
-- NOTE: Initialisation des configurations
-- ================================================
-- Pour remplir automatiquement report_configs avec toutes les entreprises,
-- exécutez le script Python après avoir créé les tables :
--
--   docker-compose exec api python /app/scripts/init_configs.py
--
-- Ce script récupère toutes les entreprises et crée leur configuration
-- en évitant les problèmes de collation entre tables.
