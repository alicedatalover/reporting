# 🔐 Guide de Sécurité - Genuka KPI Engine

## 📋 Checklist de Sécurité avant Production

### ✅ OBLIGATOIRE

- [ ] `ENVIRONMENT=production` dans `.env`
- [ ] `DEBUG=False` dans `.env`
- [ ] `SECRET_KEY` définie (minimum 32 caractères, générée aléatoirement)
- [ ] `DB_PASSWORD` définie et forte
- [ ] `CORS_ORIGINS` ne contient PAS localhost/127.0.0.1
- [ ] Fichier `.env` ajouté à `.gitignore` (ne JAMAIS commiter)

### ⚠️ FORTEMENT RECOMMANDÉ

- [ ] `REDIS_PASSWORD` définie
- [ ] HTTPS activé (reverse proxy Nginx)
- [ ] Firewall configuré (ports 8000, 5555 non publics)
- [ ] Logs centralisés (ELK, CloudWatch, etc.)
- [ ] Backup base de données automatisé
- [ ] Monitoring actif (uptime, alertes)

### 📝 SELON VOS FEATURES

Si `ENABLE_LLM_RECOMMENDATIONS=True` :
- [ ] `GOOGLE_API_KEY` définie
- [ ] Quota Gemini configuré

Si `ENABLE_WHATSAPP_NOTIFICATIONS=True` :
- [ ] `WHATSAPP_API_TOKEN` définie
- [ ] `WHATSAPP_PHONE_NUMBER_ID` définie

Si `ENABLE_TELEGRAM_NOTIFICATIONS=True` :
- [ ] `TELEGRAM_BOT_TOKEN` définie

---

## 🔑 Générer des Secrets Sécurisés

### SECRET_KEY (obligatoire)

```bash
# Méthode 1 : Python
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Méthode 2 : OpenSSL
openssl rand -base64 32
```

### DB_PASSWORD (recommandé)

```bash
# Générer un mot de passe fort (16 caractères)
python -c 'import secrets; print(secrets.token_urlsafe(16))'
```

---

## 🚨 Validations Automatiques

L'application effectue des validations au démarrage :

### ❌ ERREURS (Bloquent le démarrage en production)

- **SECRET_KEY manquante ou faible** → Application crash
- **SECRET_KEY < 32 caractères** → Application crash
- **CORS_ORIGINS contient localhost en prod** → Application crash

### ⚠️ WARNINGS (Affichés dans les logs)

- **DB_PASSWORD vide en production**
- **REDIS_PASSWORD vide en production**
- **DEBUG=True en production**
- **GOOGLE_API_KEY vide** (si LLM activé)
- **WHATSAPP_API_TOKEN vide** (si WhatsApp activé)
- **TELEGRAM_BOT_TOKEN vide** (si Telegram activé)

---

## 📖 Exemple de Configuration

### Développement (`.env`)

```bash
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=dev-secret-not-for-production

DB_HOST=localhost
DB_PASSWORD=  # Peut être vide en dev

GOOGLE_API_KEY=your-dev-key
TELEGRAM_BOT_TOKEN=your-test-bot-token

CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Production (`.env`)

```bash
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=votre-cle-secrete-generee-aleatoirement-minimum-32-caracteres

DB_HOST=prod-mysql.internal
DB_PASSWORD=mot-de-passe-tres-fort-et-long

REDIS_PASSWORD=redis-password-fort

GOOGLE_API_KEY=prod-google-api-key
WHATSAPP_API_TOKEN=prod-whatsapp-token
TELEGRAM_BOT_TOKEN=prod-telegram-bot-token

CORS_ORIGINS=https://app.genuka.com,https://www.genuka.com
```

---

## 🛡️ Bonnes Pratiques

### 1. Ne JAMAIS commiter de secrets

```bash
# Vérifier que .env est dans .gitignore
cat .gitignore | grep .env

# Si absent, ajouter
echo ".env" >> .gitignore
```

### 2. Utiliser différents secrets par environnement

- Dev : Secrets de test (peuvent être partagés en équipe via .env.example)
- Staging : Secrets intermédiaires
- Production : Secrets uniques et forts

### 3. Rotation régulière des secrets

- SECRET_KEY : Tous les 6 mois minimum
- DB_PASSWORD : Tous les 3 mois
- API_KEYS : Selon les recommandations des fournisseurs

### 4. Gestion des secrets en production

Options recommandées :
- **Docker Secrets** (si Docker Swarm)
- **Kubernetes Secrets** (si K8s)
- **AWS Secrets Manager** (si AWS)
- **HashiCorp Vault** (enterprise)
- **Variables d'environnement système** (minimum)

### 5. Audit de sécurité

```bash
# Vérifier les permissions du fichier .env
ls -la .env
# Devrait être : -rw------- (600) ou -rw-r----- (640)

# Corriger si nécessaire
chmod 600 .env
```

---

## 🔍 Vérifier Votre Configuration

Au démarrage, consultez les logs :

```bash
# Les logs afficheront :
✅ Starting Genuka KPI Engine (environment=production, debug=False)
✅ Features configuration (llm_recommendations=True, ...)

# Si erreurs de configuration :
❌ SECRET_KEY OBLIGATOIRE en production !
⚠️  DB_PASSWORD vide en production !
```

---

## 📞 Contact Sécurité

Pour signaler une vulnérabilité : security@genuka.com
