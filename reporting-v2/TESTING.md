# Guide de Test - Genuka KPI Engine V2

Ce guide vous accompagne étape par étape pour tester le système reporting-v2.

## Prérequis

- Docker et Docker Compose installés
- MySQL en cours d'exécution (Windows host accessible via `host.docker.internal`)
- Les tokens API configurés dans `.env.docker`

## Étape 1 : Démarrer les services

```bash
cd /home/user/reporting-v2
docker compose up -d
```

Vérifier que tous les services sont démarrés :
```bash
docker compose ps
```

Vous devriez voir 4 services :
- `redis` (port 6379)
- `api` (port 8000)
- `worker` (Celery worker)
- `beat` (Celery Beat scheduler)

## Étape 2 : Vérifier les logs

```bash
# Logs de l'API
docker compose logs -f api

# Logs du worker
docker compose logs -f worker

# Logs du beat
docker compose logs -f beat
```

**Attendu** : Aucune erreur de connexion DB, messages de démarrage OK.

## Étape 3 : Exécuter les migrations (Créer les tables)

### 3a. Entrer dans le conteneur

```bash
docker exec -it genuka-api-v2 bash
```

### 3b. Créer les tables SQL

```bash
python << 'EOF'
import asyncio
from app.core.database import init_database, execute_insert

async def create_tables():
    init_database()

    # Table report_configs
    await execute_insert('''
        CREATE TABLE IF NOT EXISTS report_configs (
            company_id VARCHAR(26) PRIMARY KEY,
            frequency ENUM('weekly', 'monthly') NOT NULL DEFAULT 'weekly',
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            whatsapp_number VARCHAR(20) DEFAULT NULL,
            last_activity_date DATE DEFAULT NULL,
            next_report_date DATE DEFAULT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            INDEX idx_enabled (enabled),
            INDEX idx_frequency (frequency),
            INDEX idx_next_report_date (next_report_date),
            INDEX idx_last_activity (last_activity_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    print('✓ Table report_configs created')

    # Table report_history
    await execute_insert('''
        CREATE TABLE IF NOT EXISTS report_history (
            id VARCHAR(26) PRIMARY KEY,
            company_id VARCHAR(26) NOT NULL,
            frequency ENUM('weekly', 'monthly') NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            kpis JSON DEFAULT NULL,
            insights JSON DEFAULT NULL,
            recommendations TEXT DEFAULT NULL,
            status ENUM('success', 'failed', 'skipped') NOT NULL DEFAULT 'success',
            error_message TEXT DEFAULT NULL,
            delivery_method ENUM('whatsapp', 'telegram') DEFAULT NULL,
            recipient VARCHAR(50) DEFAULT NULL,
            execution_time_ms INT DEFAULT NULL,
            sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            INDEX idx_company_id (company_id),
            INDEX idx_status (status),
            INDEX idx_sent_at (sent_at),
            INDEX idx_period (period_start, period_end)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    print('✓ Table report_history created')

asyncio.run(create_tables())
EOF
```

**Attendu** :
```
✓ Table report_configs created
✓ Table report_history created
```

### 3c. Initialiser les configurations pour toutes les entreprises

```bash
python /app/scripts/init_configs.py
```

**Attendu** :
```
✓ Database initialized

Trouvé 15 entreprises

✓ Restaurant Kerma                       (dernière activité: 2026-01-10)
✓ Boutique Élégance                      (dernière activité: 2026-01-12)
...

======================================================================
✓ Initialisation terminée
  - 15 configurations créées
  - 0 configurations existantes (skipped)
  - Total: 15 entreprises
======================================================================
```

### 3d. Sortir du conteneur

```bash
exit
```

## Étape 4 : Health Check Détaillé

```bash
curl http://localhost:8000/api/v1/health/detailed | jq
```

**Attendu** :
```json
{
  "status": "healthy",
  "checks": {
    "database": {
      "status": "healthy",
      "host": "host.docker.internal",
      "database": "genuka"
    },
    "gemini": {
      "status": "healthy",
      "model": "gemini-1.5-flash",
      "configured": true
    },
    "whatsapp": {
      "status": "configured",
      "enabled": true
    },
    "telegram": {
      "status": "configured",
      "enabled": true
    }
  }
}
```

**⚠️ Si unhealthy** :
- `database`: Vérifier MySQL sur Windows, vérifier `DB_HOST=host.docker.internal`
- `gemini`: Vérifier `GOOGLE_API_KEY` dans `.env.docker`
- `whatsapp`/`telegram`: Vérifier les tokens respectifs

## Étape 5 : Test de Prévisualisation (sans envoi)

```bash
curl -X POST "http://localhost:8000/api/v1/reports/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
    "frequency": "weekly"
  }' | jq
```

**Attendu** :
- Statut 200
- JSON avec `company_name`, `period_range`, `kpis`, `kpis_comparison`, `insights`, `recommendations`, `formatted_message`
- Le `formatted_message` doit suivre le format validé :
  ```
  Bonjour {company_name} ! 👋

  Vous avez eu une {qualificatif} semaine du XX au XX janvier. Voici un recap rapide :

  💰 Chiffre d'affaires : X,XXX,XXX FCFA (+X%)
  📦 Nombre de ventes : XX commandes (+X%)
  🛒 Panier moyen : XX,XXX FCFA (+X%)
  ⭐ Top produits : ...
  [Insights avec emojis]

  Au vu de tout ça, nous pensons que ...
  ```

**⚠️ Si erreur 404** : Company not found → Vérifier que `company_id` existe dans la table `companies`

**⚠️ Si erreur 500** : Voir les logs API (`docker compose logs api`) pour identifier le problème

## Étape 6 : Test d'Envoi via Telegram (recommandé pour tests)

Utilisez votre chat_id Telegram personnel : `1498227036`

```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
    "frequency": "weekly",
    "recipient": "1498227036",
    "delivery_method": "telegram"
  }' | jq
```

**Attendu** :
- Statut 200
- JSON : `{"status": "success", "company_name": "...", "recipient": "1498227036", "delivery_method": "telegram", "period_range": "..."}`
- **MESSAGE REÇU sur Telegram** dans les 5 secondes

**⚠️ Si status: "skipped", reason: "inactive"** :
- L'entreprise n'a pas eu de vente depuis 30 jours
- C'est le comportement attendu (filtrage activité)
- Tester avec une entreprise active ou ajuster `INACTIVE_DAYS_THRESHOLD` dans `.env.docker`

**⚠️ Si status: "failed"** :
- Vérifier les logs worker : `docker compose logs worker`
- Vérifier `TELEGRAM_BOT_TOKEN` dans `.env.docker`

## Étape 7 : Vérifier l'Historique

```bash
curl "http://localhost:8000/api/v1/admin/companies/01hjt9qsj7b039ww1nyrn9kg5t/history?limit=5" | jq
```

**Attendu** :
- Liste des rapports générés pour cette entreprise
- Chaque entrée contient : `id`, `frequency`, `period_start`, `period_end`, `status`, `delivery_method`, `recipient`, `sent_at`

## Étape 8 : Test des Configs Admin

### Lister toutes les configs
```bash
curl "http://localhost:8000/api/v1/admin/companies/configs" | jq
```

### Créer/Modifier une config
```bash
curl -X POST "http://localhost:8000/api/v1/admin/companies/01hjt9qsj7b039ww1nyrn9kg5t/config" \
  -H "Content-Type: application/json" \
  -d '{
    "frequency": "weekly",
    "enabled": true,
    "whatsapp_number": "+237658173627"
  }' | jq
```

### Lister uniquement les configs actives
```bash
curl "http://localhost:8000/api/v1/admin/companies/configs?enabled=true" | jq
```

## Étape 9 : Test du Scheduling Automatique (Celery Beat)

Vérifier que Celery Beat est configuré correctement :

```bash
docker compose logs beat | grep "Scheduler"
```

**Attendu** :
```
Scheduler: Sending due task weekly-reports (app.worker.tasks.generate_scheduled_reports)
Scheduler: Sending due task monthly-reports (app.worker.tasks.generate_scheduled_reports)
```

**Note** : Les rapports ne s'exécuteront qu'aux heures programmées :
- **Rapports hebdomadaires** : Tous les lundis à 8h00 (heure Douala)
- **Rapports mensuels** : 1er de chaque mois à 9h00

Pour tester immédiatement, vous pouvez modifier le cron dans `app/worker/scheduler.py` :

```python
# Test : toutes les 2 minutes
"schedule": crontab(minute="*/2"),
```

Puis redémarrer :
```bash
docker compose restart beat
docker compose logs -f beat
```

## Étape 10 : Test d'Envoi via WhatsApp (Production)

**⚠️ Attention** : Cela enverra un vrai message au client !

```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "01hjt9qsj7b039ww1nyrn9kg5t",
    "frequency": "weekly",
    "recipient": "+237658173627",
    "delivery_method": "whatsapp"
  }' | jq
```

**Attendu** :
- Message reçu sur WhatsApp Business
- Format conforme au template validé

## Dépannage

### Erreur : "connect() got an unexpected keyword argument 'ssl_mode'"
**Solution** : Cette erreur a été corrigée dans v2. Si elle persiste, vérifier que `app/core/database.py` utilise bien `connect_args={"ssl": None}` dans `create_async_engine()`.

### Erreur : "Task received but never executed"
**Causes possibles** :
1. Worker ne peut pas se connecter à MySQL → Vérifier `docker compose logs worker`
2. Worker ne peut pas se connecter à Redis → Vérifier `docker compose ps redis`
3. Erreur Python dans le code de la tâche → Vérifier les logs worker pour les tracebacks

### Erreur : "No module named 'pydantic_settings'"
**Solution** : Les dépendances ne sont pas installées dans le conteneur. Reconstruire les images :
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Messages non reçus malgré status "success"
**Vérifications** :
1. Tester la connexion API directement :
   ```bash
   # Telegram
   curl "https://api.telegram.org/bot<TOKEN>/getMe"

   # WhatsApp
   curl -H "Authorization: Bearer <TOKEN>" \
     "https://graph.facebook.com/v18.0/<PHONE_ID>"
   ```
2. Vérifier que le numéro/chat_id est correct
3. Vérifier les logs worker pour voir la réponse de l'API

### Entreprise toujours "skipped" (inactive)
**Vérifications** :
1. Vérifier la date de dernière activité :
   ```sql
   SELECT MAX(DATE(created_at))
   FROM orders
   WHERE company_id = '01hjt9qsj7b039ww1nyrn9kg5t'
   AND deleted_at IS NULL;
   ```
2. Si > 30 jours, c'est normal (comportement attendu)
3. Pour tester quand même, réduire `INACTIVE_DAYS_THRESHOLD=90` dans `.env.docker`

## Validation Complète

✅ Tous les checks passent si :
1. Health check détaillé = "healthy"
2. Preview génère un rapport complet avec KPIs, insights, recommendations
3. Envoi Telegram fonctionne (message reçu)
4. Historique est sauvegardé correctement
5. Configs admin fonctionnent (CRUD)
6. Beat scheduler est actif et planifié

## Prochaines Étapes

Une fois les tests locaux validés :
1. **Commit et push** sur la branche Git
2. **Déployer sur Coolify** :
   - Créer un nouveau projet
   - Importer le `docker-compose.yml`
   - Configurer les variables d'environnement depuis `.env.docker`
   - Déployer
3. **Tester en production** avec une vraie entreprise
4. **Monitorer** les rapports automatiques (lundis 8h, 1er du mois 9h)

## Support

En cas de problème persistant :
1. Partager les logs : `docker compose logs > logs.txt`
2. Vérifier la configuration : `.env.docker`
3. Tester la connectivité : health check détaillé
