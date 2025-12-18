

# 🚀 Genuka KPI Engine

**Système automatisé de génération et d'envoi de rapports d'activité pour PME**

Génère automatiquement des rapports hebdomadaires, mensuels ou trimestriels avec KPIs, insights intelligents et recommandations IA, envoyés directement via WhatsApp ou Telegram.

---

## 📋 **Table des Matières**

-[Vue d'ensemble](#-vue-densemble)
-[Fonctionnalités](#-fonctionnalités)
-[Architecture](#-architecture)
-[Prérequis](#-prérequis)
-[Installation](#-installation)
-[Configuration](#-configuration)
-[Démarrage](#-démarrage)
-[Utilisation](#-utilisation)
-[API Documentation](#-api-documentation)
-[Déploiement](#-déploiement)
-[Maintenance](#-maintenance)
-[Troubleshooting](#-troubleshooting)
-[Contributing](#-contributing)

---

## 🎯 **Vue d'ensemble**

Genuka KPI Engine est un système intelligent qui :

1.**Calcule automatiquement** les KPIs d'activité (CA, ventes, clients, stocks, dépenses)
2.**Détecte des insights** (clients à risque, baisse saisonnière, alertes stock, rentabilité)
3.**Génère des recommandations** via IA (Google Gemini)
4.**Envoie des rapports** formatés via WhatsApp/Telegram

**Cible** : 150-200 PME au Cameroun (clients Genuka SaaS)

---

## ✨ **Fonctionnalités**

### **Rapports Automatiques**
- ✅ Hebdomadaires (chaque lundi 8h)
- ✅ Mensuels (1er du mois 9h)
- ✅ Trimestriels (Jan/Avr/Jul/Oct 10h)

### **KPIs Calculés**
- 💰 Chiffre d'affaires avec variation vs période précédente
- 🛒 Nombre de ventes
- 👥 Nouveaux clients
- 🔄 Clients récurrents
- 📦 Alertes de stock
- 💸 Dépenses totales
- 📈 Résultat net (CA - Dépenses)

### **Insights Intelligents**
- 🚨 **Clients à risque de churn** : Clients fidèles inactifs (priorité 4/5)
- 📉 **Alertes stock** : Ruptures et stock faible (priorité 3-5/5)
- 📊 **Variations saisonnières** : Hausses/baisses >20% (priorité 3/5)
- 💰 **Analyse rentabilité** : Déficit, faible marge, excellente performance (priorité 2-5/5)

### **Recommandations IA**
- 🤖 Générées par Google Gemini 2.0 Flash
- 🎯 Actionnables et concrètes (pas de généralités)
- 📊 Basées sur les KPIs et insights détectés
- 💡 Fallback intelligent si Gemini échoue

### **Multi-canal**
- 📱 WhatsApp Business API (Meta Graph API)
- 💬 Telegram Bot API
- 📧 Email (futur)

---

## 🏗️ **Architecture**

┌─────────────────────────────────────────┐
│             Interface Admin Web         │
│            (Streamlit – À venir)        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│             API REST (FastAPI)          │
│   • Gestion des companies               │
│   • Configuration des rapports          │
│   • Génération manuelle des rapports    │
│   • Consultation de l’historique        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          Celery Beat (Scheduler)        │
│   • Lundi 08h → Rapport hebdomadaire    │
│   • 1er du mois → Rapport mensuel       │
│   • Trimestriel → Jan / Avr / Jul / Oct │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│            Celery Workers (Async)       │
│   1. Calcul des KPIs + comparaison      │
│   2. Extraction d’insights (4 miners)   │
│   3. Sélection Top 3 (scoring)          │
│   4. Recommandations (Gemini)           │
│   5. Formatage WhatsApp                 │
│   6. Envoi de la notification           │
│   7. Historique (report_history)        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│              Services externes          │
│   • MySQL (Genuka DB)                   │
│   • Redis (Broker + Cache)              │
│   • Google Gemini API                   │
│   • Meta WhatsApp API                   │
│   • Telegram Bot API                    │
└─────────────────────────────────────────┘


---

```

### **Stack Technique**

| **Composant**    | **Technologie**                  |
| ---------------- | -------------------------------- |
| Backend          | FastAPI (Python 3.11)            |
| Queue            | Celery + Redis                   |
| Database         | MySQL 8.0                        |
| ORM              | SQLAlchemy (async)               |
| LLM              | Google Gemini 2.0 Flash          |
| Messaging        | WhatsApp Business API / Telegram |
| Containerisation | Docker + Docker Compose          |
| Monitoring       | Flower (Celery)                  |



## 🔧 **Prérequis**

### **Développement**
- Python 3.11+
- MySQL 8.0+ (base Genuka existante)
- Redis 7+
- Docker & Docker Compose (optionnel mais recommandé)

### **APIs & Credentials**
- ✅ **Google API Key** (Gemini) : [Google AI Studio](https://makersuite.google.com/app/apikey)
- ✅ **Telegram Bot Token** (dev/test) : [@BotFather](https://t.me/botfather)
- ⏳ **WhatsApp Business API** (production) : [Meta Business](https://business.facebook.com/)

---

## 📦 **Installation**

### **Option 1 : Docker (Recommandé)**
```bash
# 1. Cloner le repo
git clone https://github.com/genuka/genuka-kpi-engine.git
cd genuka-kpi-engine

# 2. Copier et configurer .env
cp .env.example .env
nano .env  # Configurer les variables

# 3. Démarrer la stack complète
docker-compose up -d

# 4. Vérifier les services
docker-composeps
```

### **Option 2 : Installation Manuelle**

```bash
# 1. Cloner le repo
git clone https://github.com/genuka/genuka-kpi-engine.git
cd genuka-kpi-engine

# 2. Créer un environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer .env
cp .env.example .env
nano .env

# 5. Créer les tables SQL
mysql -u root -p genuka < scripts/sql/create_report_tables.sql
mysql -u root -p genuka < scripts/sql/add_indexes.sql
mysql -u root -p genuka < scripts/sql/alter_companies.sql

# 6. (Optionnel) Données de test
mysql -u root -p genuka < scripts/sql/seed_test_data.sql
```

---

## ⚙️ **Configuration**

### **Fichier `.env`**

```bash
# ==================== APPLICATION ====================
APP_NAME=Genuka KPI Engine
ENVIRONMENT=development  # development / staging / production
DEBUG=True
SECRET_KEY=your-secret-key-here

# ==================== DATABASE ====================
DB_HOST=localhost
DB_PORT=3306
DB_NAME=genuka
DB_USER=root
DB_PASSWORD=your-password
DB_CHARSET=utf8mb4

# ==================== REDIS ====================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ==================== GEMINI AI ====================
GOOGLE_API_KEY=your-google-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MAX_TOKENS=300
GEMINI_TEMPERATURE=0.7

# ==================== WHATSAPP ====================
WHATSAPP_API_TOKEN=your-meta-token-here
WHATSAPP_PHONE_NUMBER_ID=your-phone-id-here
WHATSAPP_BUSINESS_ID=your-business-id-here
WHATSAPP_API_VERSION=v21.0

# ==================== TELEGRAM ====================
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# ==================== CELERY ====================
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TIMEZONE=Africa/Douala

# ==================== FEATURES ====================
ENABLE_LLM_RECOMMENDATIONS=True
ENABLE_WHATSAPP_NOTIFICATIONS=True
ENABLE_TELEGRAM_NOTIFICATIONS=True
MAX_INSIGHTS_PER_REPORT=3

# ==================== LOGGING ====================
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### **Obtenir les Credentials**

#### **1. Google Gemini API Key**

1. Aller sur [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Créer une clé API
3. Copier dans `GOOGLE_API_KEY`

#### **2. Telegram Bot**

1. Chercher [@BotFather](https://t.me/botfather) sur Telegram
2. Envoyer `/newbot`
3. Suivre les instructions
4. Copier le token dans `TELEGRAM_BOT_TOKEN`
5. Obtenir ton chat_id via [@userinfobot](https://t.me/userinfobot)

#### **3. WhatsApp Business API**

1. Créer un compte [Meta Business](https://business.facebook.com/)
2. Ajouter WhatsApp Business
3. Créer un numéro de téléphone
4. Récupérer `WHATSAPP_API_TOKEN` et `WHATSAPP_PHONE_NUMBER_ID`

---

## 🚀 **Démarrage**

### **Avec Docker**

```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f api
docker-compose logs -f worker

# Arrêter
docker-compose down
```

### **Manuel (Développement)**

**Terminal 1 : API**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 : Celery Worker**

```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```

**Terminal 3 : Celery Beat**

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

**Terminal 4 : Flower (Monitoring)**

```bash
celery -A app.workers.celery_app flower --port=5555
```

### **Vérifier que tout fonctionne**

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Health détaillé
curl http://localhost:8000/api/v1/health/detailed

# Documentation API
open http://localhost:8000/docs

# Monitoring Celery
open http://localhost:5555
```

---

## 📖 **Utilisation**

### **1. Configurer une Entreprise**

```bash
# Activer les rapports hebdomadaires
curl -X POST http://localhost:8000/api/v1/configs/company_123/activate \
  -H "Content-Type: application/json"\
  -d '{"frequency": "weekly"}'

# Mettre à jour le numéro WhatsApp
curl -X PATCH http://localhost:8000/api/v1/configs/company_123/phone \
  -H "Content-Type: application/json"\
  -d '{"phone": "+237658173627"}'
```

### **2. Tester un Rapport (Manuel)**

**Via API :**

```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json"\
  -d '{
    "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
    "frequency": "monthly",
    "end_date": "2025-07-31",
    "recipient": "123456789",
    "delivery_method": "telegram"
  }'
```

**Via Script Python :**

```bash
python scripts/test_telegram.py \
  --company-id 01hjt9qsj7b039ww1nyrn9kg5t \
  --chat-id 123456789\
  --end-date 2025-07-31 \
  --frequency monthly
```

### **3. Prévisualiser un Rapport (Sans Envoi)**

```bash
curl -X POST http://localhost:8000/api/v1/reports/preview \
  -H "Content-Type: application/json"\
  -d '{
    "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
    "frequency": "monthly",
    "end_date": "2025-07-31"
  }'
```

### **4. Voir l'Historique**

```bash
curl http://localhost:8000/api/v1/reports/history/company_123?limit=10
```

### **5. Tester les Clients Externes**

```bash
# Tester Telegram
python scripts/test_clients.py --client telegram --chat-id 123456789

# Tester WhatsApp
python scripts/test_clients.py --client whatsapp --phone +237658173627

# Tester Gemini
python scripts/test_clients.py --client gemini
```

---

## 📚 **API Documentation**

### **Endpoints Disponibles**

#### **Health**

-`GET /api/v1/health` - Health check basique
-`GET /api/v1/health/detailed` - Health détaillé (DB, Gemini, Redis, etc.)

#### **Companies**

-`GET /api/v1/companies` - Liste toutes les entreprises
-`GET /api/v1/companies/{id}` - Détails d'une entreprise
-`GET /api/v1/companies/stats/summary` - Statistiques globales

#### **Configurations**

-`GET /api/v1/configs/{company_id}` - Récupérer config
-`POST /api/v1/configs/{company_id}` - Créer/Mettre à jour config
-`POST /api/v1/configs/{company_id}/activate` - Activer rapports
-`POST /api/v1/configs/{company_id}/deactivate` - Désactiver rapports
-`PATCH /api/v1/configs/{company_id}/phone` - Mettre à jour téléphone

#### **Rapports**

-`POST /api/v1/reports/generate` - Génération manuelle (async)
-`GET /api/v1/reports/task/{task_id}` - Statut d'une tâche
-`POST /api/v1/reports/preview` - Aperçu sans envoi
-`GET /api/v1/reports/history/{company_id}` - Historique
-`GET /api/v1/reports/stats/global` - Stats globales

**Documentation interactive** : http://localhost:8000/docs

---

## 🏭 **Déploiement**

### **Production avec Docker**

```bash
# 1. Configurer .env pour production
ENVIRONMENT=production
DEBUG=False

# 2. Build et démarrer
docker-compose up -d --build

# 3. Vérifier
docker-composeps
docker-compose logs -f
```

### **Configuration Production**

**Sécurité :**

- ✅ Désactiver DEBUG (`DEBUG=False`)
- ✅ Utiliser un SECRET_KEY fort
- ✅ Configurer CORS restrictif
- ✅ HTTPS obligatoire (reverse proxy Nginx)
- ✅ Firewall (ports 8000, 5555 non exposés publiquement)

**Performance :**

- ✅ Augmenter workers API (`--workers 4`)
- ✅ Augmenter concurrency Celery (`--concurrency=4`)
- ✅ Ajouter indexes critiques (voir `scripts/sql/add_indexes.sql`)
- ✅ Redis persistance activée
- ✅ Connection pooling MySQL

**Monitoring :**

- ✅ Sentry pour erreurs (optionnel)
- ✅ Flower protégé par authentification
- ✅ Logs JSON structurés
- ✅ Alertes Celery (échecs répétés)

---

## 🔧 **Maintenance**

### **Commandes Utiles**

```bash
# Redémarrer un service
docker-compose restart api

# Rebuild après changements
docker-compose up -d --build

# Voir les logs en temps réel
docker-compose logs -f worker

# Nettoyer les conteneurs
docker-compose down -v  # ATTENTION: supprime les volumes

# Backup base de données
dockerexec genuka-mysql mysqldump -u root -p genuka > backup.sql

# Monitorer Celery
dockerexec -it genuka-worker celery -A app.workers.celery_app inspect active
```

### **Gestion des Tâches Celery**

```bash
# Lister les tâches actives
celery -A app.workers.celery_app inspect active

# Purger toutes les tâches en attente
celery -A app.workers.celery_app purge

# Révoquer une tâche
celery -A app.workers.celery_app revoke 
```

---

## 🐛 **Troubleshooting**

### **Problème : Collation MySQL**

**Erreur :**`Illegal mix of collations (utf8mb4_unicode_520_ci,IMPLICIT) and (utf8mb4_general_ci,IMPLICIT)`

**Solution :** Exécuter `scripts/sql/alter_companies.sql` ou utiliser les CAST dans les requêtes (déjà implémenté).

### **Problème : Gemini ne répond pas**

**Vérifications :**
1.`GOOGLE_API_KEY` correcte dans `.env`
2. Quota API non dépassé
3. Réseau autorise appels vers `generativelanguage.googleapis.com`

**Fallback :** Le système utilise automatiquement des recommandations basées sur règles.

### **Problème : Messages WhatsApp non envoyés**

**Vérifications :**
1.`WHATSAPP_API_TOKEN` et `WHATSAPP_PHONE_NUMBER_ID` corrects
2. Numéro destinataire au format international (+237...)
3. Template approuvé si utilisation de templates
4. Vérifier dans Meta Business Manager

**Alternative :** Utiliser Telegram pour les tests.

### **Problème : Celery Beat ne déclenche pas**

**Vérifications :**

1. Service `beat` en cours d'exécution
2. Timezone correcte (`CELERY_TIMEZONE=Africa/Douala`)
3. Horloge système synchronisée

```bash
# Vérifier le schedule
dockerexec -it genuka-beat celery -A app.workers.celery_app inspect scheduled
```

---

## 🤝 **Contributing**

### **Structure du Code**

```
app/
├── api/              # Endpoints FastAPI
├── core/             # Business logic (KPI, Insights, Recommendations)
├── domain/           # Models Pydantic
├── infrastructure/   # Repositories, Clients externes
├── services/         # Services orchestration
├── workers/          # Tâches Celery
└── utils/            # Utilitaires (formatters, validators)
```

### **Standards de Code**

- ✅ Type hints partout
- ✅ Docstrings complètes (Google style)
- ✅ Logging structuré (JSON)
- ✅ Tests unitaires (pytest)
- ✅ Gestion d'erreurs robuste

### **Workflow**

1. Fork le repo
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

---

## 📄 **License**

Propriétaire - Genuka © 2025

---

## 👥 **Équipe**

Développé avec ❤️ par l'équipe IA Genuka

**Support** : support@genuka.com

---

## 🎯 **Roadmap**

### **v1.0 (Actuel)**

- ✅ Génération automatique rapports
- ✅ 4 Insight Miners
- ✅ Recommandations Gemini
- ✅ WhatsApp + Telegram
- ✅ API REST complète

### **v1.1 (Q1 2025)**

- ⏳ Interface Admin Streamlit
- ⏳ Export PDF des rapports
- ⏳ Templates WhatsApp personnalisés
- ⏳ Webhooks pour événements

### **v2.0 (Q2 2025)**

- ⏳ Machine Learning pour prédictions
- ⏳ Analyse comparative entre entreprises
- ⏳ Dashboard analytics temps réel
- ⏳ Support multi-langues (EN, FR)

---

## 📊 **Statistiques**

```
Lignes de code:     ~8,000
Fichiers Python:    45+
Endpoints API:      15+
Insight Miners:     4
Tests:              Coming soon
Coverage:           Coming soon
```

---

**🚀 Bon déploiement !**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-12-11

### Added
- ✅ Automated report generation (weekly/monthly/quarterly)
- ✅ KPI calculation with period comparison
- ✅ 4 Insight Miners (Stock Alert, Churn Risk, Seasonality, Profit Margin)
- ✅ AI recommendations via Google Gemini 2.0 Flash
- ✅ Multi-channel delivery (WhatsApp Business API, Telegram Bot API)
- ✅ Complete REST API (FastAPI)
- ✅ Celery workers with Beat scheduler
- ✅ Report history tracking
- ✅ Docker deployment ready
- ✅ Comprehensive logging

### Technical Stack
- Python 3.11
- FastAPI
- Celery + Redis
- SQLAlchemy (async)
- MySQL 8.0
- Google Gemini API
- Meta WhatsApp API
- Telegram Bot API

### Database
-`report_configs` table
-`report_history` table
- 15+ critical indexes

### API Endpoints
- Health checks
- Company management
- Report configuration
- Manual report generation
- Report history
- Global statistics
```

---

### **`CONTRIBUTING.md`**

markdown

```markdown
# Contributing to Genuka KPI Engine

Thank you for your interest in contributing! 🎉

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the project

## How to Contribute

### Reporting Bugs
1. Check existing issues
2. Create a new issue with:
- Clear title
- Steps to reproduce
- Expected vs actual behavior
- Environment details

### Suggesting Features
1. Open an issue with `[FEATURE]` prefix
2. Describe the use case
3. Explain the benefits

### Submitting Code

#### Setup Development Environment
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/genuka-kpi-engine.git
cd genuka-kpi-engine

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Create branch
git checkout -b feature/my-feature
```

#### Code Standards

- ✅ Type hints on all functions
- ✅ Docstrings (Google style)
- ✅ Logging for important operations
- ✅ Error handling
- ✅ Unit tests for new features

#### Commit Messages

```
feat: Add new insight miner for inventory turnover
fix: Correct timezone handling in Celery Beat
docs: Update API documentation
refactor: Simplify KPI comparison logic
test: Add tests for WhatsApp client
```

#### Pull Request Process

1. Update documentation
2. Add/update tests
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Submit PR with clear description

## Development Tips

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black app/
ruff check app/
```

### Type Checking

```bash
mypy app/
```

## Questions?

Open an issue or contact: dev@genuka.com
