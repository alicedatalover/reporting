# ============================================================
# scripts/start_stack.ps1
# Script de démarrage de la stack Genuka KPI Engine (Windows)
# ============================================================

Write-Host "🚀 Démarrage de Genuka KPI Engine..." -ForegroundColor Green

# Vérifier que .env existe
if (-not (Test-Path .env)) {
    Write-Host "❌ Fichier .env manquant. Copiez .env.example vers .env et configurez-le." -ForegroundColor Red
    exit 1
}

# Build des images
Write-Host "📦 Building Docker images..." -ForegroundColor Yellow
docker-compose build

# Démarrer les services
Write-Host "🐳 Starting services..." -ForegroundColor Yellow
docker-compose up -d

# Attendre que les services soient prêts
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Vérifier la santé des services
Write-Host "🏥 Health checks..." -ForegroundColor Yellow
docker-compose ps

# Résumé
Write-Host ""
Write-Host "✅ Stack démarrée avec succès !" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Services disponibles:" -ForegroundColor Cyan
Write-Host "   - API:    http://localhost:8000"
Write-Host "   - Docs:   http://localhost:8000/docs"
Write-Host "   - Flower: http://localhost:5555"
Write-Host ""
Write-Host "📋 Commandes utiles:" -ForegroundColor Cyan
Write-Host "   - Logs API:    docker-compose logs -f api"
Write-Host "   - Logs Worker: docker-compose logs -f worker"
Write-Host "   - Arrêter:     docker-compose down"
Write-Host ""