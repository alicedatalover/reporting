-- ============================================================
-- scripts/sql/alter_companies.sql
-- AJOUT COLONNE WHATSAPP DANS COMPANIES
-- Genuka KPI Engine
-- ============================================================

-- Ajouter la colonne whatsapp_number dans la table companies
-- Cette colonne stocke le numéro WhatsApp au format international

-- Vérifier si la colonne existe déjà
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'genuka' 
      AND TABLE_NAME = 'companies' 
      AND COLUMN_NAME = 'whatsapp_number'
);

-- Ajouter la colonne si elle n'existe pas
SET @query = IF(
    @col_exists = 0,
    'ALTER TABLE companies 
     ADD COLUMN whatsapp_number VARCHAR(20) DEFAULT NULL COMMENT "Numéro WhatsApp (format: +237XXXXXXXXX)" AFTER metadata',
    'SELECT "Column whatsapp_number already exists" AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Ajouter un index sur whatsapp_number
CREATE INDEX IF NOT EXISTS idx_companies_whatsapp 
ON companies (whatsapp_number);

-- Vérifier l'ajout
DESCRIBE companies;

-- Résumé
SELECT 
    CASE 
        WHEN @col_exists = 0 THEN 'Colonne whatsapp_number ajoutée avec succès'
        ELSE 'Colonne whatsapp_number existe déjà'
    END AS status;