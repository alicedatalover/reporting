"""
Script pour migrer la table report_history de v1 vers v2.
Ajoute toutes les colonnes manquantes sans perdre les données existantes.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.database import execute_insert, execute_query, init_database


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
        columns = await execute_query("DESCRIBE report_history")
        existing_columns = [col['Field'] for col in columns]
        print(f"   Colonnes existantes : {', '.join(existing_columns)}")
        print()
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return

    # 2. Définir les colonnes requises pour v2
    required_columns = {
        'frequency': "ENUM('weekly', 'monthly') NOT NULL DEFAULT 'weekly' COMMENT 'Fréquence du rapport' AFTER company_id",
        'sent_at': "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Date d''envoi du rapport'"
    }

    # 3. Ajouter chaque colonne manquante
    for col_name, col_definition in required_columns.items():
        if col_name not in existing_columns:
            print(f"2. Ajout de la colonne '{col_name}'...")
            try:
                await execute_insert(f"""
                    ALTER TABLE report_history
                    ADD COLUMN {col_definition}
                """)
                print(f"   ✅ Colonne '{col_name}' ajoutée")
            except Exception as e:
                print(f"   ❌ Erreur : {e}")
        else:
            print(f"2. ✓ Colonne '{col_name}' existe déjà")

    print()
    print("=" * 70)
    print("MIGRATION TERMINÉE")
    print("=" * 70)
    print()
    print("Vérification finale...")
    columns_after = await execute_query("DESCRIBE report_history")
    print(f"Colonnes finales : {', '.join([col['Field'] for col in columns_after])}")


if __name__ == "__main__":
    asyncio.run(migrate_report_history())
