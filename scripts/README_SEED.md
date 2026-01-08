# 🌱 Guide de Seed de la Base de Données

## 🔍 Problème Rencontré

Lorsque vous testez l'API via Swagger (`/docs`), vous obtenez l'erreur :

```
Company company_123 not found
```

**Cause :** La base de données MySQL est vide. Aucune donnée de test n'existe.

---

## ✅ Solution : Créer des Données de Test

### **Option 1 : Script Python (Recommandé)**

```bash
# Depuis le répertoire du projet
python scripts/seed_database.py
```

**Ce script crée automatiquement :**
- ✅ 3 entreprises de test
- ✅ 50 clients
- ✅ 5 produits
- ✅ 80 commandes (30 derniers jours)
- ✅ 5 stocks (dont 1 avec alerte)
- ✅ 2 configurations de rapports

---

### **Option 2 : Script SQL Direct**

```bash
# Se connecter à MySQL
mysql -u root -p

# Exécuter le script
source scripts/seed_database.sql

# Ou en une ligne
mysql -u root -p genuka < scripts/seed_database.sql
```

---

## 🧪 Tester l'API Après le Seed

### **1. Via Swagger UI**

Ouvrez : `http://localhost:8000/docs`

**Endpoint à tester :** `POST /api/v1/reports/preview`

**Body JSON :**
```json
{
  "company_id": "company_123",
  "frequency": "monthly"
}
```

**Réponse attendue :** Status 200 avec les KPIs, insights et recommandations

---

### **2. Via curl**

```bash
curl -X POST "http://localhost:8000/api/v1/reports/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "company_123",
    "frequency": "monthly"
  }'
```

---

### **3. Via Postman**

```
POST http://localhost:8000/api/v1/reports/preview
Content-Type: application/json

{
  "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
  "frequency": "weekly"
}
```

---

## 📋 Données de Test Disponibles

### **Entreprises**

| ID | Nom | Type | Description |
|----|-----|------|-------------|
| `01hjt9qsj7b039ww1nyrn9kg5t` | Boulangerie du Coin | retail | 50 commandes, 50 clients |
| `company_123` | Boutique Mode Élégante | retail | 30 commandes, config Telegram |
| `company_456` | Restaurant Saveur Africaine | restaurant | Données minimales |

### **Commandes**

- **Boulangerie** : 50 commandes sur les 30 derniers jours
  - Montant moyen : 2 500 FCFA
  - Total revenue : ~125 000 FCFA

- **Boutique Mode** : 30 commandes sur les 30 derniers jours
  - Montant moyen : 10 000 FCFA
  - Total revenue : ~300 000 FCFA

### **Produits**

**Boulangerie :**
- Pain Blanc (500 FCFA) - Stock: 50
- Croissant (300 FCFA) - **Stock: 5** ⚠️ Alerte
- Baguette (400 FCFA) - Stock: 35

**Boutique Mode :**
- T-shirt (5 000 FCFA) - Stock: 120
- Pantalon (12 000 FCFA) - Stock: 45

---

## 🛠️ Dépannage

### **Erreur : "Table 'genuka.companies' doesn't exist"**

**Cause :** Les tables n'ont pas été créées.

**Solution :** Vous devez créer le schéma de la base de données.

```bash
# Si vous utilisez Alembic (migrations)
alembic upgrade head

# Sinon, créez les tables manuellement
mysql -u root -p genuka < scripts/create_schema.sql
```

---

### **Erreur : "Access denied for user"**

**Cause :** Mauvais identifiants MySQL dans `.env`

**Solution :** Vérifiez votre fichier `.env`

```bash
# .env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=genuka
DB_USER=root
DB_PASSWORD=votre_mot_de_passe
```

---

### **Erreur : "Unknown database 'genuka'"**

**Cause :** La base de données n'existe pas.

**Solution :** Créez la base

```bash
mysql -u root -p -e "CREATE DATABASE genuka CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

### **Les données existent déjà**

Le script utilise `ON DUPLICATE KEY UPDATE`, donc :
- ✅ Ré-exécuter le script est **sûr**
- ✅ Les données existantes seront mises à jour
- ✅ Pas de duplicata

---

## 🔄 Réinitialiser les Données

Pour repartir de zéro :

```bash
# 1. Supprimer toutes les données
mysql -u root -p genuka -e "
  SET FOREIGN_KEY_CHECKS=0;
  TRUNCATE TABLE orders;
  TRUNCATE TABLE customers;
  TRUNCATE TABLE products;
  TRUNCATE TABLE stock;
  TRUNCATE TABLE companies;
  TRUNCATE TABLE report_config;
  TRUNCATE TABLE report_history;
  SET FOREIGN_KEY_CHECKS=1;
"

# 2. Re-seed
python scripts/seed_database.py
```

---

## 📊 Vérifier les Données

```bash
# Via MySQL CLI
mysql -u root -p genuka

# Compter les entreprises
SELECT COUNT(*) FROM companies;

# Voir les commandes par entreprise
SELECT company_id, COUNT(*) as orders, SUM(total_amount) as revenue
FROM orders
GROUP BY company_id;

# Vérifier les stocks bas
SELECT p.name, s.quantity, s.min_threshold
FROM stock s
JOIN products p ON s.product_id = p.id
WHERE s.quantity < s.min_threshold;
```

---

## 🎯 Prochaines Étapes

1. ✅ **Seed les données** : `python scripts/seed_database.py`
2. ✅ **Tester l'API** : `http://localhost:8000/docs`
3. ✅ **Générer un rapport** : Essayez `POST /api/v1/reports/preview`
4. ✅ **Voir l'historique** : `GET /api/v1/reports/history/company_123`

---

## 💡 Astuce

Pour des données plus réalistes en production, vous pouvez :
- Importer vos vraies données depuis CSV
- Utiliser un script de migration depuis votre système existant
- Connecter directement à votre base Genuka existante

---

**Besoin d'aide ?** Consultez le `QUICKSTART.md` ou la documentation API sur `/docs`
