# 🚀 Guide de Démarrage Rapide

## ✅ Prérequis

Avant de commencer, assurez-vous d'avoir :

- **Python 3.11+** installé
- **MySQL** installé et en cours d'exécution
- **Redis** installé et en cours d'exécution (pour Celery)
- Un terminal ouvert dans le répertoire du projet

---

## 📦 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

Le fichier `.env` a déjà été créé avec des valeurs par défaut pour le développement.

**Éditez `.env` et remplissez au minimum :**

```bash
# Base de données MySQL
DB_HOST=localhost
DB_PORT=3306
DB_NAME=genuka          # ⚠️ Créez cette base : CREATE DATABASE genuka;
DB_USER=root
DB_PASSWORD=            # Votre mot de passe MySQL

# Redis (requis pour Celery)
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Optionnel (pour les fonctionnalités complètes) :**

```bash
# Pour les recommandations IA
GOOGLE_API_KEY=your_gemini_api_key
ENABLE_LLM_RECOMMENDATIONS=true

# Pour WhatsApp
WHATSAPP_API_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
ENABLE_WHATSAPP_NOTIFICATIONS=true

# Pour Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ENABLE_TELEGRAM_NOTIFICATIONS=true
```

### 3. Créer la base de données

```bash
# Se connecter à MySQL
mysql -u root -p

# Créer la base
CREATE DATABASE genuka CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Quitter MySQL
exit;
```

**Note :** Les migrations de schéma doivent être appliquées (si vous utilisez Alembic, sinon créez les tables manuellement selon votre schéma).

---

## 🧪 Lancer les Tests

### Tests unitaires et d'intégration

```bash
# Lancer TOUS les tests
pytest

# Avec verbose (détails)
pytest -v

# Tests spécifiques
pytest tests/repositories/test_order_repo.py
pytest tests/services/test_report_service.py
pytest tests/api/test_reports_endpoints.py
pytest tests/integration/test_end_to_end.py

# Avec couverture de code
pytest --cov=app --cov-report=html
```

### Tests avec logs

```bash
# Voir les logs pendant les tests
pytest -v -s

# Tests d'un fichier spécifique avec logs
pytest tests/services/test_notification_service.py -v -s
```

### Tests rapides (skip slow)

```bash
# Skip les tests d'intégration lents
pytest -v -m "not slow"
```

---

## 🚀 Lancer l'API

### Méthode 1 : Docker Compose (Recommandée)

**Lance automatiquement : API + Redis + Workers + Scheduler**

```bash
# Démarrer tout le stack
docker-compose up -d

# Voir les logs de l'API
docker-compose logs -f api

# Voir les logs du worker Celery
docker-compose logs -f worker

# Arrêter tout
docker-compose down
```

**L'API sera accessible sur :** `http://localhost:8000`

### Méthode 2 : Lancement Manuel (Développement)

**Nécessite 3 terminaux ouverts :**

#### Terminal 1 : API FastAPI

```bash
# Avec hot-reload (redémarre automatiquement au changement de code)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# OU directement via Python
python app/main.py
```

**L'API sera accessible sur :** `http://localhost:8000`

#### Terminal 2 : Celery Worker (Traitement des tâches)

```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```

#### Terminal 3 : Celery Beat (Scheduler pour rapports automatiques)

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

**Note :** Redis doit être en cours d'exécution sur `localhost:6379`

```bash
# Démarrer Redis (si pas déjà lancé)
redis-server

# Ou avec Docker
docker run -d -p 6379:6379 redis:7-alpine
```

---

## 🧪 Vérifier que tout fonctionne

### 1. Tester l'API

```bash
# Health check basique
curl http://localhost:8000/api/v1/health

# Health check détaillé (vérifie DB, Redis, Gemini, etc.)
curl http://localhost:8000/api/v1/health/detailed
```

**Réponse attendue :**

```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T...",
  "version": "1.0.0"
}
```

### 2. Voir la documentation interactive

Ouvrez dans votre navigateur :

- **Swagger UI :** `http://localhost:8000/docs`
- **ReDoc :** `http://localhost:8000/redoc`

### 3. Générer un rapport de test

```bash
# Prévisualiser un rapport (sans envoi)
curl -X POST http://localhost:8000/api/v1/reports/preview \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
    "frequency": "monthly",
    "end_date": "2026-01-31"
  }'
```

### 4. Vérifier Redis

```bash
# Se connecter à Redis
redis-cli

# Tester
127.0.0.1:6379> PING
PONG

# Quitter
127.0.0.1:6379> exit
```

### 5. Vérifier Celery

```bash
# Vérifier que le worker répond
celery -A app.workers.celery_app inspect ping

# Voir les tâches actives
celery -A app.workers.celery_app inspect active

# Voir les tâches planifiées (Beat)
celery -A app.workers.celery_app inspect scheduled
```

---

## 🐛 Dépannage Rapide

### Problème : "Database connection failed"

```bash
# Vérifier que MySQL est lancé
mysql -u root -p -e "SHOW DATABASES;"

# Vérifier que la base genuka existe
mysql -u root -p -e "USE genuka;"

# Vérifier les credentials dans .env
cat .env | grep DB_
```

### Problème : "Celery broker unavailable"

```bash
# Vérifier que Redis est lancé
redis-cli ping

# Si PONG s'affiche, Redis fonctionne
# Sinon, démarrer Redis :
redis-server
```

### Problème : "Module not found"

```bash
# Réinstaller les dépendances
pip install -r requirements.txt

# Vérifier que vous êtes dans le bon environnement virtuel
which python
```

### Problème : Tests échouent

```bash
# Certains tests nécessitent des mocks
# Si un test échoue à cause d'APIs externes, c'est normal
# Vérifiez que les fixtures dans tests/conftest.py sont correctes

# Lancer les tests avec plus de détails
pytest -v -s --tb=short
```

### Problème : "Port 8000 already in use"

```bash
# Tuer le processus sur le port 8000
# Linux/Mac
lsof -ti:8000 | xargs kill -9

# Ou changer le port
uvicorn app.main:app --port 8001
```

---

## 📖 Prochaines Étapes

1. **Configurer les API externes** (voir `.env.example`)
   - Google Gemini pour les recommandations IA
   - WhatsApp Business API pour les notifications
   - Telegram Bot pour les notifications

2. **Créer des configurations de rapports**

```bash
# Activer les rapports pour une entreprise
curl -X POST http://localhost:8000/api/v1/configs/company_123/activate \
  -H "Content-Type: application/json" \
  -d '{"frequency": "weekly"}'
```

3. **Tester l'envoi de rapports**

```bash
# Générer et envoyer un rapport
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "company_123",
    "frequency": "monthly",
    "recipient": "+237658173627",
    "delivery_method": "whatsapp"
  }'
```

4. **Consulter les logs**

```bash
# Logs dans le dossier logs/
tail -f logs/app.log

# Ou avec Docker
docker-compose logs -f api
```

---

## 🎯 Commandes Utiles

```bash
# Lancer l'API en dev (hot-reload)
uvicorn app.main:app --reload

# Lancer les tests
pytest -v

# Lancer avec Docker
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter tout
docker-compose down

# Vérifier la config
python -c "from app.config import settings; print(settings.DATABASE_URL)"

# Générer une SECRET_KEY forte
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

**🎉 Vous êtes prêt ! L'API tourne et est accessible par d'autres applications.**
