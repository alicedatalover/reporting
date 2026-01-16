"""
Script de diagnostic pour tester les connexions aux services externes.
Vérifie si les variables d'environnement sont chargées et si les APIs répondent.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.config import settings
from app.core.recommendations import test_gemini_connection
from app.notifications.whatsapp import test_whatsapp_connection
from app.notifications.telegram import test_telegram_connection


async def main():
    print("=" * 70)
    print("DIAGNOSTIC DES CONNEXIONS")
    print("=" * 70)
    print()

    # 1. Variables d'environnement
    print("📋 CONFIGURATION CHARGÉE:")
    print(f"  - GOOGLE_API_KEY: {'✓ Configuré' if settings.GOOGLE_API_KEY else '✗ Non configuré'}")
    if settings.GOOGLE_API_KEY:
        print(f"    → {settings.GOOGLE_API_KEY[:20]}...{settings.GOOGLE_API_KEY[-10:]}")
    print(f"  - GEMINI_MODEL: {settings.GEMINI_MODEL}")
    print()

    print(f"  - WHATSAPP_API_TOKEN: {'✓ Configuré' if settings.WHATSAPP_API_TOKEN else '✗ Non configuré'}")
    if settings.WHATSAPP_API_TOKEN:
        print(f"    → {settings.WHATSAPP_API_TOKEN[:20]}...{settings.WHATSAPP_API_TOKEN[-10:]}")
    print(f"  - WHATSAPP_PHONE_NUMBER_ID: {settings.WHATSAPP_PHONE_NUMBER_ID if settings.WHATSAPP_PHONE_NUMBER_ID else '✗ Non configuré'}")
    print()

    print(f"  - TELEGRAM_BOT_TOKEN: {'✓ Configuré' if settings.TELEGRAM_BOT_TOKEN else '✗ Non configuré'}")
    if settings.TELEGRAM_BOT_TOKEN:
        print(f"    → {settings.TELEGRAM_BOT_TOKEN[:20]}...{settings.TELEGRAM_BOT_TOKEN[-10:]}")
    print()

    # 2. Test des connexions
    print("🔌 TEST DES CONNEXIONS:")
    print()

    # Gemini
    print("  Testing Gemini AI...")
    try:
        gemini_ok = await test_gemini_connection()
        if gemini_ok:
            print(f"    ✓ Gemini: Connexion OK")
        else:
            print(f"    ✗ Gemini: Échec de connexion")
            print(f"      → Vérifiez que le modèle '{settings.GEMINI_MODEL}' existe")
            print(f"      → Vérifiez que votre API key est valide")
    except Exception as e:
        print(f"    ✗ Gemini: Erreur - {e}")
    print()

    # WhatsApp
    print("  Testing WhatsApp API...")
    try:
        whatsapp_ok = await test_whatsapp_connection()
        if whatsapp_ok:
            print(f"    ✓ WhatsApp: Connexion OK")
        else:
            print(f"    ✗ WhatsApp: Échec de connexion")
            print(f"      → Vérifiez que votre token est valide")
            print(f"      → Vérifiez que le phone_number_id est correct")
    except Exception as e:
        print(f"    ✗ WhatsApp: Erreur - {e}")
    print()

    # Telegram
    print("  Testing Telegram API...")
    try:
        telegram_ok = await test_telegram_connection()
        if telegram_ok:
            print(f"    ✓ Telegram: Connexion OK")
        else:
            print(f"    ✗ Telegram: Échec de connexion")
            print(f"      → Vérifiez que votre bot token est valide")
    except Exception as e:
        print(f"    ✗ Telegram: Erreur - {e}")
    print()

    print("=" * 70)
    print("DIAGNOSTIC TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
