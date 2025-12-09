@echo off
REM Script para configurar variáveis de ambiente
echo ========================================
echo CONFIGURANDO ORBIS - FRONTEND
echo ========================================
echo.

cd /d "%~dp0frontend"

echo Copiando .env.example para .env...
copy /Y .env.example .env

echo.
echo ========================================
echo CONFIGURAÇÃO CONCLUÍDA!
echo ========================================
echo.
echo Conteúdo do .env:
type .env
echo.
echo ========================================
echo PRÓXIMOS PASSOS:
echo 1. Reinicie o servidor: npm run dev
echo 2. Configure no Vercel também
echo ========================================
pause
