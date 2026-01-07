# 🧪 Guide de Test - Genuka KPI Engine

## 📋 Problèmes Corrigés

### 1. **Fichier .env manquant** ✅
**Problème :** Le projet utilisait Pydantic Settings avec `env_file=".env"` mais le fichier .env n'existait pas.

**Solution :** Création d'un fichier `.env` basé sur `.env.example` avec des valeurs de test valides.

**Comment ça fonctionne :**
- Pydantic Settings (app/config.py ligne 91-96) charge automatiquement `.env`
- Les variables sont validées et typées automatiquement
- Si .env manque, les valeurs par défaut sont utilisées (souvent incorrectes)

### 2. **Dockerfile défectueux** ✅
**Problème :** Le Dockerfile essayait d'installer les dépendances avant de copier `requirements.txt`

**Solution :** Réorganisation du Dockerfile pour copier `requirements.txt` en premier

### 3. **test_generate_report_telegram.py vide** ✅
**Problème :** Le fichier était complètement vide (0 lignes)

**Solution :** Création d'un script de test complet pour générer et envoyer des rapports via Telegram

### 4. **Pas de structure de tests pytest** ✅
**Problème :** Aucun répertoire tests/ avec des tests unitaires

**Solution :** Création de tests/ avec test_config.py et configuration pytest.ini

### 5. **Dépendances manquantes** ✅
**Problème :** pytest et cffi n'étaient pas installés

**Solution :** Installation complète des dépendances depuis requirements.txt

---

## 🚀 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Créer le fichier .env

```bash
# Si le fichier .env n'existe pas, le créer à partir de .env.example
cp .env.example .env

# Puis éditer .env avec vos vraies valeurs
nano .env
```

**Variables importantes à configurer :**
- `SECRET_KEY`: Clé secrète pour la production
- `DB_PASSWORD`: Mot de passe MySQL
- `GOOGLE_API_KEY`: Clé API Google Gemini (pour les recommandations)
- `TELEGRAM_BOT_TOKEN`: Token du bot Telegram
- `WHATSAPP_API_TOKEN`: Token WhatsApp Business API

---

## 🧪 Exécution des Tests

### Tests unitaires (pytest)

```bash
# Exécuter tous les tests
python -m pytest

# Exécuter avec verbosité
python -m pytest -v

# Exécuter un fichier spécifique
python -m pytest tests/test_config.py -v

# Exécuter avec couverture de code
python -m pytest --cov=app --cov-report=html
```

### Tests des clients externes

#### Test Gemini (IA)
```bash
python scripts/test_clients.py --client gemini
```

#### Test Telegram
```bash
python scripts/test_clients.py --client telegram --chat-id VOTRE_CHAT_ID
```

#### Test WhatsApp
```bash
python scripts/test_clients.py --client whatsapp --phone +237XXXXXXXXX
```

#### Test tous les clients
```bash
python scripts/test_clients.py --client all --chat-id CHAT_ID --phone +237XXX
```

### Test génération de rapports Telegram

```bash
# Rapport hebdomadaire
python scripts/test_generate_report_telegram.py \
    --company-id 1 \
    --chat-id VOTRE_CHAT_ID \
    --period weekly

# Rapport mensuel
python scripts/test_generate_report_telegram.py \
    --company-id 1 \
    --chat-id VOTRE_CHAT_ID \
    --period monthly

# Rapport trimestriel
python scripts/test_generate_report_telegram.py \
    --company-id 1 \
    --chat-id VOTRE_CHAT_ID \
    --period quarterly
```

---

## 🔍 Vérification de la Configuration

### Vérifier que les variables d'environnement sont chargées

```bash
python -c "from app.config import settings; \
print(f'✅ Config chargée'); \
print(f'APP_NAME: {settings.APP_NAME}'); \
print(f'ENVIRONMENT: {settings.ENVIRONMENT}'); \
print(f'DEBUG: {settings.DEBUG}');"
```

### Vérifier les URLs construites

```bash
python -c "from app.config import settings; \
print(f'DATABASE_URL: {settings.DATABASE_URL}'); \
print(f'REDIS_URL: {settings.REDIS_URL}');"
```

---

## 🐳 Docker

### Build et run avec Docker Compose

```bash
# Build les images
docker-compose build

# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter les services
docker-compose down
```

### Vérifier les services

```bash
# Vérifier que l'API fonctionne
curl http://localhost:8000/api/v1/health

# Vérifier Redis
docker exec genuka-redis redis-cli ping

# Vérifier les workers Celery
docker exec genuka-worker celery -A app.workers.celery_app inspect active
```

---

## 📝 Structure des Tests

```
tests/
├── __init__.py
└── test_config.py          # Tests de configuration (7 tests)
    ├── test_settings_loading()          # Chargement .env
    ├── test_database_url()              # Construction URL DB
    ├── test_redis_url()                 # Construction URL Redis
    ├── test_environment_helpers()       # Helpers environnement
    ├── test_temperature_validation()    # Validation Gemini temp
    ├── test_max_insights_validation()   # Validation insights
    └── test_celery_broker_url_computed() # URL Celery/Redis
```

---

## ✅ Résultats Attendus

### Tests pytest
```
============================= test session starts ==============================
platform linux -- Python 3.11.14, pytest-7.4.4, pluggy-1.6.0
rootdir: /home/user/reporting
configfile: pytest.ini
collected 7 items

tests/test_config.py::test_settings_loading PASSED                       [ 14%]
tests/test_config.py::test_database_url PASSED                           [ 28%]
tests/test_config.py::test_redis_url PASSED                              [ 42%]
tests/test_config.py::test_environment_helpers PASSED                    [ 57%]
tests/test_config.py::test_temperature_validation PASSED                 [ 71%]
tests/test_config.py::test_max_insights_validation PASSED                [ 85%]
tests/test_config.py::test_celery_broker_url_computed PASSED             [100%]

============================== 7 passed in 0.20s ===============================
```

### Test clients
```
================================================================================
🧪 TEST GEMINI CLIENT
================================================================================

1. Test de connexion...
✅ Gemini API connectée

2. Test génération de recommandations...
✅ Recommandations générées:
[Recommandations générées par l'IA]
```

---

## 🐛 Troubleshooting

### Erreur "No module named 'pydantic_settings'"
```bash
pip install pydantic-settings
```

### Erreur "No module named '_cffi_backend'"
```bash
pip install cffi
```

### Erreur "Cannot uninstall packaging"
```bash
pip install -r requirements.txt --ignore-installed packaging
```

### Tests ne trouvent pas les modules
Utiliser `python -m pytest` au lieu de `pytest` directement

### Variables d'environnement non chargées
Vérifier que le fichier `.env` existe à la racine du projet

---

## 📚 Ressources

- **Documentation FastAPI :** https://fastapi.tiangolo.com/
- **Pydantic Settings :** https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **pytest :** https://docs.pytest.org/
- **Google Gemini API :** https://ai.google.dev/docs
- **Telegram Bot API :** https://core.telegram.org/bots/api
- **WhatsApp Business API :** https://developers.facebook.com/docs/whatsapp
