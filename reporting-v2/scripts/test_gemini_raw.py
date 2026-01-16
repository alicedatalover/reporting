"""
Script pour tester Gemini directement et voir pourquoi il coupe les recommandations.
"""
import sys
sys.path.insert(0, '/app')

import google.generativeai as genai
from app.config import settings

# Configurer Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

# Test simple
prompt = """Tu es un conseiller business pour PME. Donne 3-4 recommandations concrètes. Écris en phrases complètes sans markdown.

CONTEXTE :
- CA : 1,000,000 FCFA (-50%)
- 5 produits en rupture de stock
- Ventes concentrées jeudi-vendredi

RECOMMANDATIONS :"""

print("=" * 70)
print("TEST GEMINI - ANALYSE FINISH_REASON")
print("=" * 70)
print(f"Modèle : {settings.GEMINI_MODEL}")
print(f"Max tokens : {settings.GEMINI_MAX_TOKENS}")
print()

try:
    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            max_output_tokens=settings.GEMINI_MAX_TOKENS,
            temperature=settings.GEMINI_TEMPERATURE,
        )
    )

    print("📊 RESPONSE INFO:")
    print(f"  - finish_reason: {response.candidates[0].finish_reason}")
    print(f"  - finish_reason.name: {response.candidates[0].finish_reason.name}")
    print(f"  - safety_ratings: {response.candidates[0].safety_ratings}")
    print()

    text = response.text.strip()
    print(f"📝 TEXTE GÉNÉRÉ ({len(text)} caractères):")
    print("=" * 70)
    print(text)
    print("=" * 70)
    print()

    if response.candidates[0].finish_reason.name == "MAX_TOKENS":
        print("❌ PROBLÈME : Gemini a atteint la limite MAX_TOKENS !")
        print(f"   Augmentez GEMINI_MAX_TOKENS au-delà de {settings.GEMINI_MAX_TOKENS}")
    elif response.candidates[0].finish_reason.name == "SAFETY":
        print("❌ PROBLÈME : Filtres de sécurité Gemini activés !")
    elif response.candidates[0].finish_reason.name == "STOP":
        print("✅ OK : Gemini a terminé naturellement")
    else:
        print(f"⚠️  Finish reason inattendu : {response.candidates[0].finish_reason.name}")

except Exception as e:
    print(f"❌ ERREUR : {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
