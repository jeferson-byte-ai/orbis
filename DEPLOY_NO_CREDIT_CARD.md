# 🚀 Deploy Orbis - 100% Grátis SEM Cartão de Crédito

## 📋 Plataformas Utilizadas

✅ **Frontend:** Vercel  
✅ **Backend:** Pella.app  
✅ **PostgreSQL:** Neon  
✅ **Redis:** Upstash  

**Tempo estimado:** 45 minutos  
**Custo:** R$ 0,00 💰

---

## 🎯 PARTE 1: Configurar PostgreSQL (Neon)

### **1.1 Acessar Dashboard do Neon**

```
https://console.neon.tech
```

### **1.2 Criar Projeto (se ainda não criou)**

```
Project name: Orbis
Postgres version: 17
Cloud provider: AWS
Region: South America (São Paulo) ou US East 1
Neon Auth: DESMARCADO ❌
```

### **1.3 Copiar Connection String**

No dashboard do Neon:

```
1. Clique no projeto "Orbis"
2. Vá em "Dashboard" ou "Connection Details"
3. Copie a "Connection String" completa

Exemplo:
postgresql://orbis_owner:AbC123xyz@ep-cool-name.aws.neon.tech/orbis?sslmode=require
```

**💾 SALVE ESSA STRING NUM ARQUIVO DE TEXTO!**

```
DATABASE_URL=postgresql://orbis_owner:AbC123xyz@ep-cool-name.aws.neon.tech/orbis?sslmode=require
```

---

## 🗄️ PARTE 2: Configurar Redis (Upstash)

### **2.1 Acessar Console do Upstash**

```
https://console.upstash.com
```

### **2.2 Criar Redis Database**

```
1. Clique em "Create Database"
2. Preencha:
   Name: orbis-redis
   Type: Regional (grátis)
   Region: US-East-1 ou South America (se disponível)
   TLS: Enabled ✅
   
3. Clique em "Create"
```

### **2.3 Copiar Redis URL**

No dashboard do Redis criado:

```
1. Clique em "orbis-redis"
2. Aba "Details"
3. Procure por: "Redis Connection URL"
4. Copie a URL completa

Exemplo:
redis://default:AbCdEf123xyz@gusc1-cool-name.upstash.io:6379
```

**💾 SALVE ESSA URL NO MESMO ARQUIVO!**

```
REDIS_URL=redis://default:AbCdEf123xyz@gusc1-cool-name.upstash.io:6379
```

---

## 🐍 PARTE 3: Deploy do Backend (Pella.app)

### **3.1 Acessar Dashboard do Pella**

```
https://pella.app/dashboard
```

### **3.2 Criar Nova Aplicação**

```
1. Clique em "Create New App" ou "New Project"
2. Conectar com GitHub:
   - Autorize o Pella a acessar seu GitHub
   - Selecione o repositório "orbis"
   - Branch: main
```

### **3.3 Configurar Build Settings**

```
App Name: orbis-backend
Root Directory: ./ (raiz do projeto)
Build Command: pip install -r requirements.txt
Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Python Version: 3.11
```

### **3.4 Adicionar Variáveis de Ambiente**

**⚠️ IMPORTANTE:** Adicione TODAS essas variáveis:

```bash
# === AMBIENTE ===
ENVIRONMENT=production
DEBUG=false
PYTHON_VERSION=3.11

# === API ===
API_HOST=0.0.0.0
API_PORT=8000

# === DATABASE (colar do Neon) ===
DATABASE_URL=postgresql://orbis_owner:SUA_STRING_AQUI@ep-xxx.aws.neon.tech/orbis?sslmode=require

# === REDIS (colar do Upstash) ===
REDIS_URL=redis://default:SUA_STRING_AQUI@xxx.upstash.io:6379

# === SEGURANÇA (gerar chaves novas) ===
SECRET_KEY=GERAR_NOVA_CHAVE_AQUI
JWT_SECRET=GERAR_NOVA_CHAVE_AQUI

# === CORS (atualizar depois com URL do Vercel) ===
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://*.vercel.app

# === MODELOS ML ===
ASR_MODEL=openai/whisper-base
ASR_DEVICE=cpu
MT_MODEL=facebook/nllb-200-distilled-600M
MT_DEVICE=cpu
TTS_DEVICE=cpu

# === FEATURES ===
TARGET_LATENCY_MS=800
MAX_ROOM_PARTICIPANTS=50
ML_LAZY_LOAD=true
ML_AUTO_UNLOAD_ENABLED=true
ML_UNLOAD_AFTER_IDLE_SECONDS=3600

# === RATE LIMITING ===
RATE_LIMIT_PER_MINUTE=60
MAX_CONNECTIONS_PER_ROOM=50
```

### **3.5 Gerar Chaves Secretas**

No seu terminal local (Windows PowerShell):

```powershell
# Gerar SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Copiar resultado e colar em SECRET_KEY

# Gerar JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Copiar resultado e colar em JWT_SECRET
```

### **3.6 Deploy!**

```
1. Clique em "Deploy" ou "Create App"
2. Aguarde 5-10 minutos
3. Status: "Live" ✅

Sua URL será algo como:
https://orbis-backend.pella.app
ou
https://orbis-backend-xyz.pella.app
```

**💾 COPIE E SALVE ESSA URL!**

```
BACKEND_URL=https://orbis-backend.pella.app
```

### **3.7 Testar Backend**

Abra no navegador:

```
https://orbis-backend.pella.app/health

Deve retornar:
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production"
}
```

✅ **Se aparecer isso, backend está funcionando!**

---

## 🌐 PARTE 4: Deploy do Frontend (Vercel)

### **4.1 Criar arquivo de configuração**

Primeiro, vamos criar o arquivo de configuração no seu projeto local.

**Arquivo:** `frontend/src/config.ts`

```typescript
const isDevelopment = import.meta.env.MODE === 'development';

export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://orbis-backend.pella.app'; // ⚠️ COLE SUA URL DO PELLA AQUI

export const WS_BASE_URL = isDevelopment
  ? 'ws://localhost:8000'
  : 'wss://orbis-backend.pella.app'; // ⚠️ COLE SUA URL DO PELLA AQUI (com wss://)

export const config = {
  apiUrl: API_BASE_URL,
  wsUrl: WS_BASE_URL,
  environment: isDevelopment ? 'development' : 'production',
};
```

### **4.2 Atualizar hooks para usar config**

**Arquivo:** `frontend/src/hooks/useTranslation.ts` (ou similar)

Adicione no topo:

```typescript
import { API_BASE_URL, WS_BASE_URL } from '../config';
```

E troque URLs hardcoded por:

```typescript
// Antes:
const wsUrl = `ws://localhost:8000/api/ws/audio/${roomId}`;

// Depois:
const wsUrl = `${WS_BASE_URL}/api/ws/audio/${roomId}?token=${token}`;
```

### **4.3 Commit e Push**

```bash
cd c:\Users\Jeferson\Documents\orbis

git add .
git commit -m "feat: configurar URLs para deploy em produção"
git push origin main
```

### **4.4 Acessar Dashboard do Vercel**

```
https://vercel.com/dashboard
```

### **4.5 Importar Projeto**

```
1. Clique em "Add New..." → "Project"
2. Clique em "Import Git Repository"
3. Conecte sua conta GitHub (se ainda não conectou)
4. Procure por "orbis" na lista
5. Clique em "Import"
```

### **4.6 Configurar Projeto**

```
Framework Preset: Vite (detecta automaticamente)
Root Directory: frontend
Build Command: npm run build (ou deixe default)
Output Directory: dist (ou deixe default)
Install Command: npm install (ou deixe default)
```

### **4.7 Adicionar Variáveis de Ambiente (opcional)**

Se precisar:

```
VITE_API_URL=https://orbis-backend.pella.app
VITE_WS_URL=wss://orbis-backend.pella.app
```

**Mas como você já colocou no `config.ts`, não é obrigatório.**

### **4.8 Deploy!**

```
1. Clique em "Deploy"
2. Aguarde 2-5 minutos
3. Status: "Ready" ✅

Sua URL será:
https://orbis.vercel.app
ou
https://orbis-xyz.vercel.app
```

**🎉 COPIE ESSA URL - É SEU SITE OFICIAL!**

---

## 🔐 PARTE 5: Atualizar CORS no Backend

### **5.1 Voltar ao Pella.app**

```
Dashboard → orbis-backend → Settings → Environment Variables
```

### **5.2 Atualizar CORS_ORIGINS**

Edite a variável `CORS_ORIGINS` e adicione a URL do Vercel:

```bash
CORS_ORIGINS=https://orbis.vercel.app,https://orbis-xyz.vercel.app,https://*.vercel.app,http://localhost:3000,http://localhost:5173
```

**⚠️ Troque `orbis-xyz.vercel.app` pela sua URL real do Vercel!**

### **5.3 Re-deploy Backend**

```
1. No Pella, clique em "Redeploy" ou "Restart"
2. Aguarde 1-2 minutos
```

---

## ✅ PARTE 6: Testar Tudo Funcionando

### **6.1 Abrir seu site**

```
https://orbis.vercel.app (sua URL)
```

### **6.2 Checklist de Testes**

- [ ] Site carrega sem erros
- [ ] Console do navegador (F12) sem erros de CORS
- [ ] Consegue criar conta / fazer login
- [ ] Consegue criar sala de tradução
- [ ] WebSocket conecta (ver no Network tab do F12)
- [ ] Tradução em tempo real funciona
- [ ] Áudio funciona

### **6.3 Verificar Logs**

**Backend (Pella):**
```
Dashboard → orbis-backend → Logs
```

**Frontend (Vercel):**
```
Dashboard → orbis → Deployments → Logs
```

---

## 📊 RESUMO - Suas URLs

```
🌐 Site Oficial:    https://orbis.vercel.app
🔧 Backend API:     https://orbis-backend.pella.app
🗄️ PostgreSQL:      (gerenciado no Neon)
📮 Redis:           (gerenciado no Upstash)
```

---

## 🐛 TROUBLESHOOTING

### **Erro: CORS policy**

```
Solução:
1. Verificar CORS_ORIGINS no Pella
2. Adicionar URL exata do Vercel
3. Re-deploy backend
```

### **Erro: Backend não conecta**

```
Solução:
1. Verificar se backend está "Live" no Pella
2. Testar /health endpoint
3. Verificar URL no frontend/src/config.ts
```

### **Erro: Database connection failed**

```
Solução:
1. Verificar DATABASE_URL no Pella
2. Verificar se tem `?sslmode=require` no final
3. Testar conexão no Neon dashboard
```

### **Erro: Redis connection failed**

```
Solução:
1. Verificar REDIS_URL no Pella
2. Verificar se URL tem `redis://` não `rediss://`
3. Testar no Upstash console
```

---

## 🎯 PRÓXIMOS PASSOS

✅ **Deploy completo!**

Agora você pode:

1. **Compartilhar o link:** `https://orbis.vercel.app`
2. **Adicionar domínio customizado** (opcional)
3. **Monitorar uso** nas plataformas
4. **Fazer atualizações:** Só dar push no GitHub!

---

## 💰 CUSTOS MENSAIS

```
Frontend (Vercel):  R$ 0,00
Backend (Pella):    R$ 0,00
PostgreSQL (Neon):  R$ 0,00
Redis (Upstash):    R$ 0,00
─────────────────────────
TOTAL:              R$ 0,00 ✨
```

**Limitações do Free Tier:**
- Pella: 100 MB RAM, 0.1 CPU
- Neon: 0.5 GB storage, 10 projetos
- Upstash: 10k comandos/dia
- Vercel: 100 GB bandwidth/mês

**Suficiente para:**
- ✅ MVP e testes
- ✅ Portfólio
- ✅ Dezenas de usuários simultâneos
- ✅ Prototipação

---

**Data:** 2025-11-24  
**Versão:** Orbis v2.0  
**Deploy sem cartão:** 100% ✅
