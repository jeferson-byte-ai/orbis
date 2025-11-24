# 🚀 Deploy COMPLETO Vercel + Upstash (100% Grátis, SEM Cartão!)

## ✅ **O QUE VOCÊ VAI TER**

```
Frontend: Vercel (React)
Backend: Vercel Functions (API Routes)
Database: Vercel Postgres (256MB grátis)
Redis: Upstash Redis (10k req/dia grátis)

Custo: R$ 0
Tempo: 20 minutos
Cartão: NÃO PRECISA! ✅
```

---

## 📋 **PRÉ-REQUISITOS**

- [x] Código no GitHub
- [x] Conta GitHub
- [ ] Conta Vercel (criar agora)
- [ ] Conta Upstash (criar agora)

---

## 🎯 **PASSO 1: Criar conta Upstash** (2 min)

### 1. Acesse:
👉 https://console.upstash.com/login

### 2. Login com GitHub
- Clique "Continue with GitHub"
- Autorize
- **NÃO pede cartão!** ✅

### 3. Criar Redis Database

No dashboard:
- Clique "Create Database"
- Name: `orbis-redis`
- Type: **Regional** (mais rápido)
- Region: **US-East-1** (Ohio)
- Plan: **Free** ✅
- Clique "Create"

### 4. Copiar credenciais

Após criar, copie:
- **UPSTASH_REDIS_REST_URL**: `https://xxx.upstash.io`
- **UPSTASH_REDIS_REST_TOKEN**: `AXXXxxx...`

**Guarde essas URLs!**

---

## 🗄️ **PASSO 2: Criar Vercel Postgres** (2 min)

### 1. Acesse Vercel:
👉 https://vercel.com/new

### 2. Login com GitHub

### 3. Criar Database

- Dashboard → Storage → Connect Store
- Postgres → Continue
- Database Name: `orbis-db`
- Region: `Washington D.C. (iad1)`
- Plan: **Hobby** (grátis)
- Create

**Credenciais são automáticas!** ✅

---

## 📦 **PASSO 3: Adaptar Backend para Vercel**

Vercel usa **API Routes** em vez de FastAPI tradicional.

### Estrutura:
```
backend/
  api/
    __.init__.py
    health.py       # GET /api/health
    rooms.py        # Rooms endpoints
    translate.py    # Translation endpoints
    auth.py         # Auth endpoints
```

Cada arquivo vira um endpoint!

---

## 🔧 **PASSO 4: Configurar projeto**

Vou criar os arquivos necessários para você:

### `vercel.json`:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/api/**/*.py",
      "use": "@vercel/python"
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "backend/api/$1"
    },
    {
      "src": "/(.*)",
      "dest": "frontend/$1"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.11"
  }
}
```

---

## ⚡ **PASSO 5: Deploy!**

### Via CLI (recomendado):

```bash
# Instalar Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod

# Responder prompts:
# Link to existing project? No
# Project name? orbis
# Directory? ./
# ...
```

### Via Dashboard:

1. https://vercel.com/new
2. Import Git Repository
3. Selecione "orbis"
4. Framework: `Vite`
5. Root: `./`
6. Deploy!

---

## 🔐 **PASSO 6: Configurar variáveis**

No Vercel Dashboard → Settings → Environment Variables:

```env
# Database (auto-preenchido se criou Vercel Postgres)
POSTGRES_URL=...
POSTGRES_PRISMA_URL=...
POSTGRES_URL_NON_POOLING=...

# Redis Upstash
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXXXxxx...

# Segurança
SECRET_KEY=<gerar>
JWT_SECRET=<gerar>

# ML (modelos leves ou APIs)
ASR_MODEL=openai/whisper-tiny
USE_OPENAI_API=true
OPENAI_API_KEY=<opcional>
```

Gerar chaves:
```bash
.\venv\Scripts\python.exe generate_secrets.py
```

---

## 🎨 **PASSO 7: Configurar Frontend**

`frontend/src/config.ts`:
```typescript
export const API_BASE_URL = 
  import.meta.env.MODE === 'development'
    ? 'http://localhost:8000'
    : '/api';  // Mesmo domínio!

// WebSockets via Pusher ou Ably (grátis)
export const WS_PROVIDER = 'ably';
export const ABLY_KEY = import.meta.env.VITE_ABLY_KEY;
```

---

## 📡 **PASSO 8: WebSockets** (Desafio)

Vercel Functions **não suportam WebSockets persistentes**.

### Soluções:

**Opção A: Ably** (grátis)
```
✅ 6 milhões msgs/mês grátis
✅ WebSocket managed
✅ Fácil integração
```

Cadastro: https://ably.com (GitHub login, sem cartão!)

**Opção B: Pusher** (grátis)
```
✅ 200k msgs/dia grátis
✅ WebSocket managed
```

**Opção C: Polling** (simples)
```
Frontend consulta /api/room/{id} a cada 1s
Não é real-time, mas funciona!
```

---

## 🧠 **PASSO 9: ML Models**

Vercel Functions têm limite de **250MB** e **10s** de execução.

### Soluções:

**Opção A: OpenAI API** (pago mas barato)
```python
# Whisper via API
response = openai.Audio.transcribe("whisper-1", audio)

# Translation via GPT
response = openai.ChatCompletion.create(...)
```

**Opção B: Modelos tiny locais**
```python
# Whisper tiny (39MB)
ASR_MODEL = "openai/whisper-tiny"

# NLLB distilled (600MB - não cabe!)
# Usar API externa
```

**Opção C: Replicate API** (serverless ML)
```
✅ Paga por uso
✅ Whisper, NLLB disponíveis
✅ Free tier: $50 crédito
```

---

## ✅ **RESUMO DOS LIMITES**

### Vercel Free:
- ✅ 100GB bandwidth/mês
- ✅ Functions: 10s timeout
- ✅ 250MB package size
- ✅ Domínio .vercel.app

### Upstash Free:
- ✅ 10.000 requests/dia
- ✅ 256MB storage
- ✅ Comandos Redis completos

### Vercel Postgres Free:
- ✅ 256MB storage
- ✅ 60h compute/mês
- ✅ Backups automáticos

---

## ⚠️ **LIMITAÇÕES vs LOCAL**

| Feature | Local | Vercel |
|---------|-------|--------|
| **Redis config** | ✅ redis.conf | ⚠️ Upstash (menos config) |
| **ML models** | ✅ Qualquer | ❌ Só tiny ou APIs |
| **WebSockets** | ✅ Direto | ⚠️ Via Ably/Pusher |
| **Request time** | ✅ Ilimitado | ❌ 10s max |
| **Package size** | ✅ Ilimitado | ❌ 250MB |

---

## 💡 **WORKAROUNDS**

### Para ML pesado:
```
Frontend → Vercel Functions → Replicate API
                            ↓
                    Whisper/NLLB rodando lá
```

### Para WebSockets:
```
Frontend → Ably → Backend polling Vercel
```

### Para persistência Redis:
```
Upstash = Redis completo na nuvem
Sincroniza com código local
```

---

## 🎯 **VALE A PENA?**

### ✅ SIM, se:
- Você quer algo NO AR rápido
- Não tem cartão de crédito
- Aceita adaptações (APIs externas)
- Tráfego baixo/médio

### ❌ NÃO, se:
- Precisa ML pesado local
- WebSockets críticos
- Muitas configurações Redis
- Alto volume

---

## 🚀 **PRÓXIMOS PASSOS**

**Quer que eu:**
1. Crie os arquivos adaptados pro Vercel?
2. Configure Upstash Redis?
3. Adapte o backend?

**OU prefere:**
- Tentar outro serviço?
- Deploy local + ngrok (temporário)?

**Me diz e eu faço AGORA!** ✅

---

**Tempo estimado se formos em frente:** 30-40 min  
**Custo:** R$ 0  
**Cartão:** NÃO PRECISA! 🎉
