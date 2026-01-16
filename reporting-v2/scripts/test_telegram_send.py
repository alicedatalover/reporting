"""
Test simple d'envoi de message Telegram.
Vérifie que l'envoi fonctionne sans passer par tout le flux de génération.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.notifications.telegram import send_telegram_message
from app.config import settings


async def test_telegram_send():
    """Test direct d'envoi Telegram."""

    print("=" * 70)
    print("TEST ENVOI TELEGRAM")
    print("=" * 70)
    print()

    print(f"📱 Configuration:")
    print(f"   Bot Token: {settings.TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"   Chat ID: 1498227036")
    print()

    # Message de test simple
    test_message = """🧪 TEST REPORTING V2

Bonjour ! Ceci est un message de test pour vérifier que l'envoi Telegram fonctionne.

✅ Si vous recevez ce message, l'intégration Telegram est OK !

KPIs de test :
💰 CA : 1,000,000 FCFA
📦 Ventes : 100 commandes
🛒 Panier moyen : 10,000 FCFA

Recommandation test : Continuez comme ça !"""

    print("📤 Envoi du message de test...")
    print()

    try:
        success = await send_telegram_message("1498227036", test_message)

        if success:
            print("✅ MESSAGE ENVOYÉ AVEC SUCCÈS !")
            print()
            print("👉 Vérifiez votre Telegram (@alicedatalover)")
            print("   Vous devriez avoir reçu un message de test.")
        else:
            print("❌ ÉCHEC DE L'ENVOI")
            print()
            print("Le message n'a pas pu être envoyé.")
            print("Vérifiez les logs ci-dessus pour plus de détails.")

    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_telegram_send())
