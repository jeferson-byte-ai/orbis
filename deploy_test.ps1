# Script para deploy rápido de teste

Write-Host "🚀 Iniciando deploy de teste..." -ForegroundColor Cyan
Write-Host ""

# 1. Build do frontend
Write-Host "📦 1/4 - Fazendo build do frontend..." -ForegroundColor Yellow
Set-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro no build!" -ForegroundColor Red
    exit 1
}
Set-Location ..
Write-Host "   ✅ Build concluído!" -ForegroundColor Green
Write-Host ""

# 2. Git add
Write-Host "📝 2/4 - Adicionando arquivos ao Git..." -ForegroundColor Yellow
git add .
Write-Host "   ✅ Arquivos adicionados!" -ForegroundColor Green
Write-Host ""

# 3. Git commit
Write-Host "💾 3/4 - Fazendo commit..." -ForegroundColor Yellow
$commitMsg = "fix: WebRTC connection issue - update handler when localStream changes"
git commit -m $commitMsg
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ⚠️  Nada para commitar ou erro no commit" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ Commit feito!" -ForegroundColor Green
}
Write-Host ""

# 4. Git push
Write-Host "🚢 4/4 - Fazendo push para GitHub..." -ForegroundColor Yellow
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Erro no push!" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Push concluído!" -ForegroundColor Green
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ Deploy enviado para GitHub!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "⏳ Aguarde o Vercel fazer o deploy (geralmente 1-2 minutos)" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔍 Para verificar o status do deploy:" -ForegroundColor Cyan
Write-Host "   1. Acesse: https://vercel.com/seu-projeto" -ForegroundColor White
Write-Host "   2. Veja se o deploy está 'Ready'" -ForegroundColor White
Write-Host ""
Write-Host "📱 Depois que o deploy estiver pronto:" -ForegroundColor Cyan
Write-Host "   1. No navegador (PC e Mobile), pressione Ctrl+Shift+R" -ForegroundColor White
Write-Host "   2. Ou abra em aba anônima" -ForegroundColor White
Write-Host "   3. Verifique no console se aparece:" -ForegroundColor White
Write-Host "      ✅ 'Updating WebRTC message handler'" -ForegroundColor Green
Write-Host "      ✅ 'Has localStream: true'" -ForegroundColor Green
Write-Host ""
