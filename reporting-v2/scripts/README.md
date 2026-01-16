# Scripts d'Initialisation et Maintenance

Ce dossier contient les scripts Python pour initialiser et maintenir le système reporting-v2.

## 📋 Scripts Disponibles

### `init_configs.py` - Initialisation des Configurations

**Quand l'utiliser** : Après avoir créé les tables `report_configs` et `report_history` via les migrations SQL.

**Ce qu'il fait** :
- Récupère toutes les entreprises de la table `companies`
- Crée une configuration dans `report_configs` pour chaque entreprise
- Calcule automatiquement la `last_activity_date` depuis la table `orders`
- Skip les entreprises déjà configurées (idempotent)

**Comment l'exécuter** :

```bash
# Depuis votre machine (Windows/Linux/Mac)
docker-compose exec api python /app/scripts/init_configs.py

# OU depuis le conteneur directement
docker exec -it genuka-api-v2 bash
python /app/scripts/init_configs.py
exit
```

**Sortie attendue** :
```
✓ Database initialized

Trouvé 15 entreprises

✓ Restaurant Kerma                       (dernière activité: 2026-01-10)
✓ Boutique Élégance                      (dernière activité: 2026-01-12)
✓ Supermarché Delta                      (aucune activité)
...

======================================================================
✓ Initialisation terminée
  - 15 configurations créées
  - 0 configurations existantes (skipped)
  - Total: 15 entreprises
======================================================================
```

**Configuration créée par défaut** :
- `frequency`: `weekly` (peut être changé via l'API)
- `enabled`: `TRUE` (actif)
- `last_activity_date`: Calculé depuis les commandes

---

## 🔄 Ordre d'Exécution Recommandé

1. **Créer les tables** (première fois uniquement)
   ```bash
   docker-compose exec api python -c "..."  # Voir TESTING.md
   ```

2. **Initialiser les configs**
   ```bash
   docker-compose exec api python /app/scripts/init_configs.py
   ```

3. **Tester l'API**
   ```bash
   curl http://localhost:8000/api/v1/health/detailed
   ```

---

## ⚙️ Développement

### Ajouter un nouveau script

1. Créez un fichier `.py` dans ce dossier
2. Ajoutez le shebang et le path :
   ```python
   import sys
   sys.path.insert(0, '/app')
   from app.core.database import ...
   ```
3. Documentez-le dans ce README
4. Testez depuis le conteneur

### Structure type

```python
"""
Description du script.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.database import init_database

async def main():
    init_database()
    # Votre logique ici
    print("✓ Done")

if __name__ == "__main__":
    asyncio.run(main())
```
