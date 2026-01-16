"""
Test pour diagnostiquer le problème d'encodage UTF-8.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.database import execute_query, init_database
from app.notifications.telegram import send_telegram_message


async def test_encoding():
    """Test encodage depuis DB et envoi Telegram."""

    print("=" * 70)
    print("DIAGNOSTIC ENCODAGE UTF-8")
    print("=" * 70)
    print()

    init_database()

    # 1. Test avec texte hardcodé (pas de DB)
    print("1️⃣ TEST TEXTE HARDCODÉ (pas de base de données)")
    hardcoded_message = """Test encodage UTF-8 direct :

✅ Les Délices de Milly
✅ Verre à Vin
✅ Café
✅ Thé

Si vous voyez des '?' à la place des accents, le problème est l'envoi Telegram.
Si vous voyez correctement, le problème est la lecture de la base de données."""

    print("   Envoi du message hardcodé...")
    success1 = await send_telegram_message("1498227036", hardcoded_message)
    print(f"   {'✅' if success1 else '❌'} Message hardcodé envoyé")
    print()

    # 2. Test lecture depuis DB
    print("2️⃣ TEST LECTURE DEPUIS BASE DE DONNÉES")
    companies = await execute_query("""
        SELECT id, name
        FROM companies
        WHERE name LIKE '%Délice%' OR name LIKE '%à%'
        LIMIT 5
    """)

    print(f"   Trouvé {len(companies)} entreprises avec accents :")
    for company in companies:
        print(f"   - ID: {company['id']}")
        print(f"     Nom: {company['name']}")
        print(f"     Encodage: {company['name'].encode('utf-8')}")
    print()

    if companies:
        # 3. Test envoi depuis DB
        print("3️⃣ TEST ENVOI DEPUIS DB")
        db_message = f"""Test depuis base de données :

Entreprise : {companies[0]['name']}

Si vous voyez des '?', les données sont mal encodées dans MySQL."""

        print("   Envoi du message depuis DB...")
        success2 = await send_telegram_message("1498227036", db_message)
        print(f"   {'✅' if success2 else '❌'} Message DB envoyé")

    print()
    print("=" * 70)
    print("VÉRIFIEZ VOTRE TELEGRAM")
    print("=" * 70)
    print()
    print("Vous devriez avoir reçu 2 messages :")
    print("1. Message hardcodé avec accents corrects")
    print("2. Message depuis DB (peut avoir des '?')")


if __name__ == "__main__":
    asyncio.run(test_encoding())
