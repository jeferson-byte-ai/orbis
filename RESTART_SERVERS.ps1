# Script para reiniciar servidores completamente

Write-Host "🛑 Parando processos Node/Vite..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -like "*node*" -or $_.ProcessName -like "*vite*"} | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "⏳ Aguardando 3 segundos..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "🧹 Limpando cache do frontend..." -ForegroundColor Yellow
Set-Location frontend
Remove-Item -Recurse -Force node_modules/.vite -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

Write-Host "🔨 Fazendo build do frontend..." -ForegroundColor Cyan
npm run build

Write-Host "" 
Write-Host "✅ Build concluído!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 PRÓXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host "1. Abra um terminal e execute: python start.py" -ForegroundColor White
Write-Host "2. Abra outro terminal e execute: cd frontend && npm run dev" -ForegroundColor White
Write-Host "3. No navegador, pressione Ctrl+Shift+Delete e limpe o cache" -ForegroundColor White
Write-Host "4. Feche TODAS as abas do site e abra uma nova" -ForegroundColor White
Write-Host "5. Faça Ctrl+Shift+R para hard refresh" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Para verificar se o código novo está rodando, veja no console:" -ForegroundColor Cyan
Write-Host "   ✅ Deve aparecer: 'Updating WebRTC message handler'" -ForegroundColor Green
Write-Host "   ❌ NÃO deve aparecer: 'Has localStream: false'" -ForegroundColor Red
