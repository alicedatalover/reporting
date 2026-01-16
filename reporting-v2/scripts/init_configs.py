"""
Script d'initialisation des configurations de rapports.
Récupère toutes les entreprises et crée leur configuration dans report_configs.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.database import init_database, execute_query, execute_insert


async def init_report_configs():
    """Initialise les configurations pour toutes les entreprises."""
    init_database()
    print("✓ Database initialized\n")

    # 1. Récupérer toutes les entreprises
    companies = await execute_query("SELECT id, name FROM companies")
    print(f"Trouvé {len(companies)} entreprises\n")

    inserted = 0
    skipped = 0

    # 2. Pour chaque entreprise, créer sa config
    for company in companies:
        company_id = company['id']
        company_name = company['name']

        # Récupérer la dernière activité (date de dernière vente non supprimée)
        last_activity_result = await execute_query("""
            SELECT MAX(DATE(created_at)) as last_date
            FROM orders
            WHERE company_id = :company_id AND deleted_at IS NULL
        """, {'company_id': company_id})

        last_date = last_activity_result[0]['last_date'] if last_activity_result and last_activity_result[0]['last_date'] else None

        # Vérifier si la config existe déjà
        existing = await execute_query("""
            SELECT company_id FROM report_configs WHERE company_id = :company_id
        """, {'company_id': company_id})

        if existing:
            print(f"⊘ {company_name[:40]:40} (déjà configuré)")
            skipped += 1
            continue

        # Insérer dans report_configs
        await execute_insert("""
            INSERT INTO report_configs (company_id, frequency, enabled, last_activity_date)
            VALUES (:company_id, 'weekly', TRUE, :last_date)
        """, {
            'company_id': company_id,
            'last_date': last_date
        })

        activity_status = f"(dernière activité: {last_date})" if last_date else "(aucune activité)"
        print(f"✓ {company_name[:40]:40} {activity_status}")
        inserted += 1

    print(f"\n{'='*70}")
    print(f"✓ Initialisation terminée")
    print(f"  - {inserted} configurations créées")
    print(f"  - {skipped} configurations existantes (skipped)")
    print(f"  - Total: {len(companies)} entreprises")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(init_report_configs())
