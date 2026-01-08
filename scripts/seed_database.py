#!/usr/bin/env python3
"""
Script de seed pour créer des données de test dans la base de données.

Usage:
    python scripts/seed_database.py

Requirements:
    - MySQL en cours d'exécution
    - Base de données 'genuka' créée
    - Configuration .env correcte
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.infrastructure.database.connection import AsyncSessionLocal
from app.config import settings

async def seed_companies(session):
    """Crée des entreprises de test."""
    print("📊 Création des entreprises...")

    companies = [
        {
            'id': '01hjt9qsj7b039ww1nyrn9kg5t',
            'name': 'Boulangerie du Coin',
            'handle': 'boulangerie-du-coin',
            'company_code': 'BOUL001',
            'description': 'Boulangerie artisanale proposant pains et viennoiseries',
            'currency_code': 'XAF',
            'currency_name': 'Franc CFA',
            'type': 'retail'
        },
        {
            'id': 'company_123',
            'name': 'Boutique Mode Élégante',
            'handle': 'boutique-mode',
            'company_code': 'MODE001',
            'description': 'Boutique de vêtements et accessoires',
            'currency_code': 'XAF',
            'currency_name': 'Franc CFA',
            'type': 'retail'
        },
        {
            'id': 'company_456',
            'name': 'Restaurant Saveur Africaine',
            'handle': 'restaurant-saveur',
            'company_code': 'REST001',
            'description': 'Restaurant spécialisé en cuisine africaine',
            'currency_code': 'XAF',
            'currency_name': 'Franc CFA',
            'type': 'restaurant'
        }
    ]

    for company in companies:
        query = text("""
            INSERT INTO companies
            (id, name, handle, company_code, description, currency_code, currency_name, type, created_at, updated_at)
            VALUES
            (:id, :name, :handle, :company_code, :description, :currency_code, :currency_name, :type, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            updated_at = NOW()
        """)

        await session.execute(query, company)

    await session.commit()
    print(f"   ✅ {len(companies)} entreprises créées")


async def seed_customers(session):
    """Crée des clients de test."""
    print("👥 Création des clients...")

    for i in range(1, 51):
        query = text("""
            INSERT INTO customers
            (id, company_id, name, phone, email, created_at, updated_at, last_order_date)
            VALUES
            (:id, :company_id, :name, :phone, :email, :created_at, NOW(), :last_order_date)
            ON DUPLICATE KEY UPDATE
            name = VALUES(name)
        """)

        created_at = datetime.now() - timedelta(days=random.randint(30, 180))
        last_order = datetime.now() - timedelta(days=random.randint(0, 30))

        await session.execute(query, {
            'id': f'cust_{i}',
            'company_id': '01hjt9qsj7b039ww1nyrn9kg5t',
            'name': f'Client {i}',
            'phone': f'+23765{str(i).zfill(7)}',
            'email': f'client{i}@example.cm',
            'created_at': created_at,
            'last_order_date': last_order
        })

    await session.commit()
    print("   ✅ 50 clients créés")


async def seed_products(session):
    """Crée des produits de test."""
    print("📦 Création des produits...")

    products = [
        {'id': 'prod_1', 'company_id': '01hjt9qsj7b039ww1nyrn9kg5t', 'name': 'Pain Blanc', 'sku': 'PAIN001', 'price': 500},
        {'id': 'prod_2', 'company_id': '01hjt9qsj7b039ww1nyrn9kg5t', 'name': 'Croissant', 'sku': 'CROI001', 'price': 300},
        {'id': 'prod_3', 'company_id': '01hjt9qsj7b039ww1nyrn9kg5t', 'name': 'Baguette', 'sku': 'BAGU001', 'price': 400},
        {'id': 'prod_4', 'company_id': 'company_123', 'name': 'T-shirt', 'sku': 'TSHI001', 'price': 5000},
        {'id': 'prod_5', 'company_id': 'company_123', 'name': 'Pantalon', 'sku': 'PANT001', 'price': 12000},
    ]

    for product in products:
        query = text("""
            INSERT INTO products
            (id, company_id, name, sku, price, created_at, updated_at)
            VALUES
            (:id, :company_id, :name, :sku, :price, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            price = VALUES(price)
        """)

        await session.execute(query, product)

    await session.commit()
    print(f"   ✅ {len(products)} produits créés")


async def seed_stock(session):
    """Crée des stocks de test."""
    print("📊 Création des stocks...")

    stocks = [
        {'id': 'stock_1', 'company_id': '01hjt9qsj7b039ww1nyrn9kg5t', 'product_id': 'prod_1', 'quantity': 50, 'min_threshold': 20},
        {'id': 'stock_2', 'company_id': '01hjt9qsj7b039ww1nyrn9kg5t', 'product_id': 'prod_2', 'quantity': 5, 'min_threshold': 15},  # Stock bas
        {'id': 'stock_3', 'company_id': '01hjt9qsj7b039ww1nyrn9kg5t', 'product_id': 'prod_3', 'quantity': 35, 'min_threshold': 10},
        {'id': 'stock_4', 'company_id': 'company_123', 'product_id': 'prod_4', 'quantity': 120, 'min_threshold': 20},
        {'id': 'stock_5', 'company_id': 'company_123', 'product_id': 'prod_5', 'quantity': 45, 'min_threshold': 10},
    ]

    for stock in stocks:
        query = text("""
            INSERT INTO stock
            (id, company_id, product_id, quantity, min_threshold, created_at, updated_at)
            VALUES
            (:id, :company_id, :product_id, :quantity, :min_threshold, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
            quantity = VALUES(quantity)
        """)

        await session.execute(query, stock)

    await session.commit()
    print(f"   ✅ {len(stocks)} stocks créés")


async def seed_orders(session):
    """Crée des commandes de test."""
    print("🛒 Création des commandes...")

    order_count = 0

    # Commandes pour Boulangerie (50 commandes sur 30 jours)
    for i in range(50):
        order_id = f'order_boul_{i}'
        customer_id = f'cust_{random.randint(1, 50)}'
        amount = round(500 + random.random() * 4500, 2)
        days_ago = random.randint(0, 30)
        created_at = datetime.now() - timedelta(days=days_ago)

        query = text("""
            INSERT INTO orders
            (id, company_id, customer_id, total_amount, status, created_at, updated_at)
            VALUES
            (:id, :company_id, :customer_id, :total_amount, :status, :created_at, NOW())
            ON DUPLICATE KEY UPDATE
            total_amount = VALUES(total_amount)
        """)

        await session.execute(query, {
            'id': order_id,
            'company_id': '01hjt9qsj7b039ww1nyrn9kg5t',
            'customer_id': customer_id,
            'total_amount': amount,
            'status': 'completed',
            'created_at': created_at
        })

        order_count += 1

    # Commandes pour Boutique Mode (30 commandes)
    for i in range(30):
        order_id = f'order_mode_{i}'
        customer_id = f'cust_{random.randint(1, 40)}'
        amount = round(2000 + random.random() * 18000, 2)
        days_ago = random.randint(0, 30)
        created_at = datetime.now() - timedelta(days=days_ago)

        query = text("""
            INSERT INTO orders
            (id, company_id, customer_id, total_amount, status, created_at, updated_at)
            VALUES
            (:id, :company_id, :customer_id, :total_amount, :status, :created_at, NOW())
            ON DUPLICATE KEY UPDATE
            total_amount = VALUES(total_amount)
        """)

        await session.execute(query, {
            'id': order_id,
            'company_id': 'company_123',
            'customer_id': customer_id,
            'total_amount': amount,
            'status': 'completed',
            'created_at': created_at
        })

        order_count += 1

    await session.commit()
    print(f"   ✅ {order_count} commandes créées")


async def seed_report_config(session):
    """Crée des configurations de rapports."""
    print("⚙️ Création des configurations de rapports...")

    configs = [
        {
            'company_id': '01hjt9qsj7b039ww1nyrn9kg5t',
            'is_active': 1,
            'frequency': 'weekly',
            'delivery_method': 'whatsapp',
            'recipient': '+237658173627'
        },
        {
            'company_id': 'company_123',
            'is_active': 1,
            'frequency': 'monthly',
            'delivery_method': 'telegram',
            'recipient': '123456789'
        }
    ]

    for config in configs:
        # Générer un ID unique
        import uuid
        config_id = f"cfg_{uuid.uuid4().hex[:8]}"

        query = text("""
            INSERT INTO report_config
            (id, company_id, is_active, frequency, delivery_method, recipient, created_at, updated_at)
            VALUES
            (:id, :company_id, :is_active, :frequency, :delivery_method, :recipient, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
            is_active = VALUES(is_active)
        """)

        await session.execute(query, {
            'id': config_id,
            **config
        })

    await session.commit()
    print(f"   ✅ {len(configs)} configurations créées")


async def verify_data(session):
    """Vérifie que les données ont bien été insérées."""
    print("\n🔍 Vérification des données...")

    # Compter les entreprises
    result = await session.execute(text("SELECT COUNT(*) as count FROM companies"))
    companies_count = result.scalar()
    print(f"   📊 Entreprises: {companies_count}")

    # Compter les commandes
    result = await session.execute(text("SELECT COUNT(*) as count FROM orders"))
    orders_count = result.scalar()
    print(f"   🛒 Commandes: {orders_count}")

    # Compter les clients
    result = await session.execute(text("SELECT COUNT(*) as count FROM customers"))
    customers_count = result.scalar()
    print(f"   👥 Clients: {customers_count}")

    # Compter les produits
    result = await session.execute(text("SELECT COUNT(*) as count FROM products"))
    products_count = result.scalar()
    print(f"   📦 Produits: {products_count}")

    # Revenue total par entreprise
    result = await session.execute(text("""
        SELECT company_id, COUNT(*) as orders, SUM(total_amount) as revenue
        FROM orders
        GROUP BY company_id
    """))

    print("\n   💰 Revenus par entreprise:")
    for row in result:
        print(f"      • {row.company_id}: {row.orders} commandes, {row.revenue:,.0f} FCFA")


async def main():
    """Point d'entrée principal."""
    print("=" * 70)
    print("🚀 SEED DE LA BASE DE DONNÉES GENUKA")
    print("=" * 70)
    print(f"\n📋 Configuration:")
    print(f"   • Database: {settings.DB_NAME}")
    print(f"   • Host: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"   • User: {settings.DB_USER}")
    print()

    try:
        async with AsyncSessionLocal() as session:
            # Seed dans l'ordre (à cause des foreign keys)
            await seed_companies(session)
            await seed_customers(session)
            await seed_products(session)
            await seed_stock(session)
            await seed_orders(session)
            await seed_report_config(session)

            # Vérification
            await verify_data(session)

        print("\n" + "=" * 70)
        print("✅ SEED TERMINÉ AVEC SUCCÈS !")
        print("=" * 70)
        print("\n🧪 Vous pouvez maintenant tester l'API avec ces données:")
        print("   • Company ID: 01hjt9qsj7b039ww1nyrn9kg5t (Boulangerie)")
        print("   • Company ID: company_123 (Boutique Mode)")
        print("   • Company ID: company_456 (Restaurant)")
        print("\n📖 Test avec Swagger:")
        print("   http://localhost:8000/docs")
        print("   Endpoint: POST /api/v1/reports/preview")
        print('   Body: {"company_id": "company_123", "frequency": "monthly"}')
        print()

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        print("\n💡 Vérifiez que:")
        print("   1. MySQL est démarré")
        print("   2. La base 'genuka' existe (CREATE DATABASE genuka;)")
        print("   3. Le fichier .env est correctement configuré")
        print("   4. Les tables existent (migrations appliquées)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
