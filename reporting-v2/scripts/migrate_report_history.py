"""
Script pour migrer la table report_history de v1 vers v2.
Ajoute les colonnes manquantes sans perdre les données existantes.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.database import execute_insert, init_database


async def migrate_report_history():
    """Migre la table report_history de v1 vers v2."""

    print("=" * 70)
    print("MIGRATION report_history : v1 → v2")
    print("=" * 70)
    print()

    init_database()

    # 1. Vérifier la structure actuelle
    print("1. Vérification de la structure actuelle...")
    try:
        from app.core.database import execute_query
        columns = await execute_query("DESCRIBE report_history")
        existing_columns = [col['Field'] for col in columns]
        print(f"   Colonnes existantes : {', '.join(existing_columns)}")
        print()
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return

    # 2. Ajouter la colonne frequency si elle n'existe pas
    if 'frequency' not in existing_columns:
        print("2. Ajout de la colonne 'frequency'...")
        try:
            await execute_insert("""
                ALTER TABLE report_history
                ADD COLUMN frequency ENUM('weekly', 'monthly') NOT NULL DEFAULT 'weekly'
                COMMENT 'Fréquence du rapport'
                AFTER company_id
            """)
            print("   ✅ Colonne 'frequency' ajoutée")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
    else:
        print("2. ✓ Colonne 'frequency' existe déjà")

    print()
    print("=" * 70)
    print("MIGRATION TERMINÉE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(migrate_report_history())
