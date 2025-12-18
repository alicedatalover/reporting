# scripts/test_clients.py
"""
Script pour tester les clients externes.

Usage:
    python scripts/test_clients.py --client whatsapp --phone +237658173627
    python scripts/test_clients.py --client telegram --chat-id 123456789
    python scripts/test_clients.py --client gemini
"""

import asyncio
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.infrastructure.external import GeminiClient, WhatsAppClient, TelegramClient


async def test_whatsapp(phone: str):
    """Teste le client WhatsApp."""
    
    print("=" * 80)
    print("🧪 TEST WHATSAPP CLIENT")
    print("=" * 80)
    
    if not settings.WHATSAPP_API_TOKEN:
        print("❌ WHATSAPP_API_TOKEN non configuré dans .env")
        return
    
    try:
        client = WhatsAppClient(settings)
        
        # Test connexion
        print("\n1. Test de connexion...")
        profile = await client.get_business_profile()
        if profile:
            print(f"✅ Profil récupéré: {profile.get('verified_name')}")
        else:
            print("⚠️  Impossible de récupérer le profil")
        
        # Test envoi message
        print(f"\n2. Envoi message de test à {phone}...")
        message = (
            "📊 *Test Genuka KPI Engine*\n\n"
            "Ceci est un message de test.\n\n"
            "Si vous recevez ce message, l'intégration WhatsApp fonctionne ! ✅"
        )
        
        success = await client.send_message(phone, message)
        
        if success:
            print(f"✅ Message envoyé avec succès à {phone}")
        else:
            print(f"❌ Échec de l'envoi à {phone}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")


async def test_telegram(chat_id: str):
    """Teste le client Telegram."""
    
    print("=" * 80)
    print("🧪 TEST TELEGRAM CLIENT")
    print("=" * 80)
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN non configuré dans .env")
        return
    
    try:
        client = TelegramClient(settings)
        
        # Test connexion
        print("\n1. Test de connexion...")
        bot_info = await client.get_bot_info()
        if bot_info:
            print(f"✅ Bot connecté: @{bot_info.get('username')}")
        else:
            print("⚠️  Impossible de récupérer les infos du bot")
        
        # Test envoi message
        print(f"\n2. Envoi message de test à {chat_id}...")
        message = (
            "📊 *Test Genuka KPI Engine*\n\n"
            "Ceci est un message de test.\n\n"
            "Si vous recevez ce message, l'intégration Telegram fonctionne ! ✅"
        )
        
        success = await client.send_message(chat_id, message)
        
        if success:
            print(f"✅ Message envoyé avec succès à {chat_id}")
        else:
            print(f"❌ Échec de l'envoi à {chat_id}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")


async def test_gemini():
    """Teste le client Gemini."""
    
    print("=" * 80)
    print("🧪 TEST GEMINI CLIENT")
    print("=" * 80)
    
    if not settings.GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY non configuré dans .env")
        return
    
    try:
        client = GeminiClient(settings)
        
        # Test connexion
        print("\n1. Test de connexion...")
        connected = await client.test_connection()
        
        if connected:
            print("✅ Gemini API connectée")
        else:
            print("❌ Échec de connexion à Gemini")
            return
        
        # Test génération
        print("\n2. Test génération de recommandations...")
        prompt = """Tu es un conseiller financier.
        
Une entreprise a réalisé un CA de 10M XAF ce mois avec 150 ventes.
Ses dépenses sont de 12M XAF (résultat: -2M XAF).

Donne 2 recommandations concrètes en 50 mots max."""
        
        recommendations = await client.generate_recommendations(
            prompt=prompt,
            max_tokens=350,
            temperature=0.7
        )
        
        if recommendations:
            print(f"✅ Recommandations générées:\n{recommendations}")
        else:
            print("❌ Échec de génération")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Teste les clients externes"
    )
    
    parser.add_argument(
        "--client",
        choices=["whatsapp", "telegram", "gemini", "all"],
        required=True,
        help="Client à tester"
    )
    
    parser.add_argument(
        "--phone",
        help="Numéro WhatsApp (format: +237XXXXXXXXX)"
    )
    
    parser.add_argument(
        "--chat-id",
        help="Chat ID Telegram"
    )
    
    args = parser.parse_args()
    
    if args.client == "whatsapp":
        if not args.phone:
            print("❌ --phone requis pour WhatsApp")
            return
        await test_whatsapp(args.phone)
        
    elif args.client == "telegram":
        if not args.chat_id:
            print("❌ --chat-id requis pour Telegram")
            return
        await test_telegram(args.chat_id)
        
    elif args.client == "gemini":
        await test_gemini()
        
    elif args.client == "all":
        await test_gemini()
        if args.chat_id:
            await test_telegram(args.chat_id)
        if args.phone:
            await test_whatsapp(args.phone)


if __name__ == "__main__":
    asyncio.run(main())