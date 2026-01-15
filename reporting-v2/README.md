# 📊 Genuka KPI Engine v2 - Simplifié

> Système de génération et d'envoi automatique de rapports d'activité avec insights et recommandations IA.

## 🎯 Objectif

Envoyer chaque semaine/mois aux entreprises clientes un rapport stratégique contenant :
- KPIs clés (CA, ventes, panier moyen, top produits)
- Insights data mining (stocks, churn, saisonnalité, marges)
- Recommandations personnalisées (Gemini AI)

## 🏗️ Architecture Simplifiée

**3 Services Docker :**
- `api` : API REST FastAPI
- `worker` : Worker Celery (génération + envoi rapports)
- `redis` : Broker Celery

## 🚀 Démarrage Rapide

```bash
# 1. Configurer .env.docker avec vos tokens API
cp .env.docker.example .env.docker
nano .env.docker

# 2. Lancer Docker
docker-compose up -d

# 3. Créer les tables DB
docker-compose exec api python -c "from migrations import run_migrations; run_migrations()"

# 4. Initialiser les configs entreprises
docker-compose exec api python scripts/init_report_configs.py

# 5. Tester
curl http://localhost:8000/api/v1/health
```

## 📁 Structure Projet

```
reporting-v2/
├── app/
│   ├── api/          # API REST endpoints
│   ├── worker/       # Celery tasks
│   ├── core/         # Business logic (KPIs, insights, recommendations)
│   ├── notifications/# WhatsApp, Telegram
│   ├── models.py     # Pydantic models
│   └── config.py     # Configuration
├── migrations/       # SQL migrations
└── docker-compose.yml
```

## 🔧 API Admin

**Gérer les configurations entreprises :**

```bash
# Activer une entreprise
POST /api/v1/admin/companies/{company_id}/config
{
  "frequency": "weekly",
  "enabled": true,
  "whatsapp_number": "+237658173627"
}

# Lister toutes les configs
GET /api/v1/admin/companies/configs

# Voir historique rapports
GET /api/v1/admin/companies/{company_id}/history
```

## 📊 Génération Manuelle

```bash
# Prévisualiser un rapport (sans envoi)
POST /api/v1/reports/preview
{
  "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
  "frequency": "weekly"
}

# Générer et envoyer
POST /api/v1/reports/generate
{
  "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
  "frequency": "weekly",
  "recipient": "+237658173627",
  "delivery_method": "whatsapp"
}
```

## ⚙️ Configuration

Variables essentielles dans `.env.docker` :

```bash
# Database
DB_HOST=host.docker.internal
DB_NAME=genuka
DB_USER=root
DB_PASSWORD=

# APIs externes
GOOGLE_API_KEY=xxx          # Gemini AI
WHATSAPP_API_TOKEN=xxx
TELEGRAM_BOT_TOKEN=xxx

# Règles métier
INACTIVE_DAYS_THRESHOLD=30  # Skip si pas de ventes depuis 30j
GEMINI_MAX_TOKENS=300
```

## 🎯 Focus Business Logic

**Priorités :**
1. 🥇 Calculs KPIs précis
2. 🥇 Insights pertinents
3. 🥇 Recommandations LLM de qualité
4. 🥈 Infrastructure stable
5. 🥉 Interface admin basique

## 📦 Déploiement Coolify

```bash
# Coolify détecte automatiquement docker-compose.yml
# Variables d'environnement à configurer dans Coolify UI
```

## 🐛 Debug

```bash
# Logs API
docker-compose logs -f api

# Logs Worker
docker-compose logs -f worker

# Tester connexion DB
docker-compose exec api python -c "from app.core.database import test_connection; test_connection()"

# Tester Gemini API
docker-compose exec api python -c "from app.core.recommendations import test_gemini; test_gemini()"
```
