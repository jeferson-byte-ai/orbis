# 🚀 Guia de Deploy - Orbis em Produção

## 📋 Pré-requisitos

- ✅ Código no GitHub
- ✅ Conta no Render.com (grátis)
- ✅ Conta no Vercel (grátis)
- ✅ 30 minutos de tempo

---

## 🎯 Arquitetura de Deploy

```
USUÁRIOS (Qualquer lugar do mundo)
    ↓
Frontend (Vercel) → https://orbis.vercel.app
    ↓ API calls
Backend (Render) → https://orbis-backend.onrender.com
    ↓
Redis (Render) - Cache interno
Postgres (Render) - Database interno
Modelos ML - Baixados automaticamente no primeiro uso
```

---

## 📦 PARTE 1: Preparar Código

### **1. Criar arquivos de configuração**

#### `render.yaml` (raiz do projeto)

```yaml
services:
  # Backend API
  - type: web
    name: orbis-backend
    runtime: python
    region: oregon
    plan: free
    buildCommand: |
      pip install --upgrade pip
      pip install -r requirements.txt
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      - key: PORT
        value: 8000
      - key: ENVIRONMENT
        value: production
      - key: DEBUG
        value: false
      - fromGroup: orbis-secrets

  # Redis Cache
  - type: redis
    name: orbis-redis
    region: oregon
    plan: free
    maxmemoryPolicy: allkeys-lru
    ipAllowList: []

databases:
  # PostgreSQL Database
  - name: orbis-postgres
    region: oregon
    plan: free
    databaseName: orbis
    user: orbis
```

#### `Procfile` (para Heroku, opcional)

```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

#### `.env.production.example`

```env
# PRODUCTION CONFIGURATION
ENVIRONMENT=production
DEBUG=false

# API
API_HOST=0.0.0.0
API_PORT=$PORT
CORS_ORIGINS=https://orbis.vercel.app,https://orbis.app

# Database (Render fornece automaticamente)
DATABASE_URL=$DATABASE_URL

# Redis (Render fornece automaticamente)
REDIS_URL=$REDIS_URL

# Security (GERAR NOVAS CHAVES!)
SECRET_KEY=CHANGE_ME_IN_PRODUCTION
JWT_SECRET=CHANGE_ME_IN_PRODUCTION

# ML Models (download automático)
ASR_MODEL=openai/whisper-base
ASR_DEVICE=cpu
MT_MODEL=facebook/nllb-200-distilled-600M
MT_DEVICE=cpu

# Features
TARGET_LATENCY_MS=800
MAX_ROOM_PARTICIPANTS=50
ML_LAZY_LOAD=true
ML_AUTO_UNLOAD_ENABLED=true

# Optional (se tiver)
OPENAI_API_KEY=
```

### **2. Atualizar .gitignore**

```gitignore
# Environment
.env
.env.local
.env.production
!.env.example
!.env.production.example

# Sensitive
*.pem
*.key
secrets.json

# Models (não commitar modelos grandes)
data/models/
*.pt
*.bin
*.onnx

# Logs
logs/
*.log
```

### **3. Criar script de health check**

Já existe em `backend/main.py`:

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": settings.api_version,
        "environment": settings.environment
    }
```

### **4. Commit e push**

```bash
git add .
git commit -m "chore: preparar deploy para produção"
git push origin main
```

---

## ☁️ PARTE 2: Deploy do Backend (Render)

### **1. Criar conta no Render**

```
https://render.com
Sign Up with GitHub (recomendado)
```

### **2. Criar Redis**

```
Dashboard → New → Redis
  Name: orbis-redis
  Region: Oregon (ou mais próximo de você)
  Plan: Free (25MB)
  
Criar e copiar REDIS_URL:
  redis://red-xxxxx:6379
```

### **3. Criar PostgreSQL**

```
Dashboard → New → PostgreSQL
  Name: orbis-postgres
  Database: orbis
  User: orbis
  Region: Oregon
  Plan: Free (1GB)
  
Criar e copiar Database URL interno:
  postgres://orbis:...@...
```

### **4. Criar Web Service**

```
Dashboard → New → Web Service
  
Connect repository:
  → Conectar GitHub
  → Selecionar repositório "orbis"
  → Branch: main

Configure:
  Name: orbis-backend
  Region: Oregon
  Branch: main
  Runtime: Python 3
  
Build Command:
  pip install --upgrade pip && pip install -r requirements.txt
  
Start Command:
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT

Plan: Free
```

### **5. Adicionar variáveis de ambiente**

No Web Service, aba **Environment**:

```
AUTO_DEPLOY=yes
PYTHON_VERSION=3.11
ENVIRONMENT=production
DEBUG=false

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://orbis.vercel.app

# Database (colar URL do Postgres criado)
DATABASE_URL=postgres://orbis:...@postgres.render.com/orbis

# Redis (colar URL do Redis criado)
REDIS_URL=redis://red-xxxxx:6379

# Security (gerar novas chaves!)
SECRET_KEY=<gerar nova chave>
JWT_SECRET=<gerar nova chave>

# ML
ASR_MODEL=openai/whisper-base
ASR_DEVICE=cpu
MT_MODEL=facebook/nllb-200-distilled-600M
MT_DEVICE=cpu
TTS_DEVICE=cpu

# Features
TARGET_LATENCY_MS=800
MAX_ROOM_PARTICIPANTS=50
ML_LAZY_LOAD=true
ML_AUTO_UNLOAD_ENABLED=true
ML_UNLOAD_AFTER_IDLE_SECONDS=3600

# Email (se configurado)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app
FROM_EMAIL=seu-email@gmail.com

# OpenAI (opcional)
OPENAI_API_KEY=sk-...
```

**Para gerar chaves seguras:**

```bash
# No seu terminal local
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copiar e usar como SECRET_KEY

python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copiar e usar como JWT_SECRET
```

### **6. Deploy! 🚀**

```
Clicar em "Create Web Service"

Render vai:
  1. Clonar repositório
  2. Instalar dependências (pip install)
  3. Iniciar servidor
  4. Monitorar health check (/health)
  
Status: Deploy in progress...
Aguardar 5-10 minutos (primeira vez demora)

Deploy bem-sucedido:
  URL: https://orbis-backend.onrender.com
  Status: Live
```

### **7. Testar Backend**

```bash
# Health check
curl https://orbis-backend.onrender.com/health

# Resposta esperada:
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production"
}
```

---

## 🌐 PARTE 3: Deploy do Frontend (Vercel)

### **1. Atualizar URLs no Frontend**

`frontend/src/config.ts` (criar se não existir):

```typescript
const isDevelopment = import.meta.env.MODE === 'development';

export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://orbis-backend.onrender.com';

export const WS_BASE_URL = isDevelopment
  ? 'ws://localhost:8000/api'
  : 'wss://orbis-backend.onrender.com/api';
```

Atualizar hooks para usar essas URLs:

`frontend/src/hooks/useTranslation.ts`:

```typescript
import { API_BASE_URL, WS_BASE_URL } from '../config';

// ...

const wsUrl = `${WS_BASE_URL}/ws/audio/${roomId}?token=${token}`;
```

### **2. Criar conta no Vercel**

```
https://vercel.com
Sign Up with GitHub
```

### **3. Deploy via Dashboard**

```
Dashboard → Add New → Project

Import Git Repository:
  → Conectar GitHub
  → Selecionar repositório "orbis"

Configure Project:
  Framework Preset: Vite
  Root Directory: frontend
  
Build Settings:
  Build Command: npm run build
  Output Directory: dist
  Install Command: npm install

Environment Variables:
  VITE_API_URL=https://orbis-backend.onrender.com
  VITE_WS_URL=wss://orbis-backend.onrender.com

Deploy!
```

### **4. Ou Deploy via CLI**

```bash
cd frontend

# Instalar Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod

# Responder perguntas:
# Set up and deploy: Y
# Which scope: sua-conta
# Link to existing project: N
# Project name: orbis
# Directory: ./ (current)
# Override settings: N

# Deploy completo!
# URL: https://orbis.vercel.app
```

### **5. Testar Frontend**

```
Abrir: https://orbis.vercel.app
  → Deve carregar homepage
  → Criar conta/login
  → Criar sala
  → Testar tradução em tempo real
```

---

## 🔐 PARTE 4: Configurações de Segurança

### **1. CORS no Backend**

Atualizar `backend/main.py`:

```python
# Adicionar domínio de produção
CORS_ORIGINS = [
    "https://orbis.vercel.app",
    "https://orbis-xxxx.vercel.app",  # Vercel preview URLs
    "http://localhost:3000",
    "http://localhost:5173",
]
```

### **2. Variáveis sensíveis**

```
✅ NUNCA commitar:
  - .env
  - Chaves API
  - Senhas
  - Tokens

✅ Usar variáveis de ambiente:
  - No Render: Environment tab
  - No Vercel: Settings → Environment Variables
  
✅ Gerar novas chaves para produção:
  - Não usar as mesmas de desenvolvimento
```

### **3. Rate Limiting**

Já implementado em `backend/core/security_middleware.py`:

```python
# Ajustar limites para produção no .env
RATE_LIMIT_PER_MINUTE=60
```

---

## 📊 PARTE 5: Monitoramento

### **Logs do Backend (Render)**

```
Render Dashboard → orbis-backend → Logs
  
Filtrar:
  • Errors
  • Warnings
  • Performance

Comandos úteis:
  • Pesquisar "ERROR"
  • Pesquisar "⚠️"
  • Ver latência de requisições
```

### **Métricas do Frontend (Vercel)**

```
Vercel Dashboard → orbis → Analytics
  
Ver:
  • Page views
  • Unique visitors
  • Performance metrics
  • Error rates
```

### **Health Checks**

Configurar monitoramento externo (opcional):

```
UptimeRobot (grátis):
  Monitor: https://orbis-backend.onrender.com/health
  Interval: 5 minutos
  Alert: Email se down

Notificações:
  • Email
  • Slack
  • Telegram
```

---

## 💰 CUSTOS

### **Configuração Gratuita (Hobby):**

```
✅ Frontend (Vercel): Grátis
   • 100GB bandwidth/mês
   • Serverless functions
   • Auto HTTPS

✅ Backend (Render): Grátis
   • 750 horas/mês
   • Sleep após 15min inativo
   • 512MB RAM
   • CPU compartilhado

✅ Redis (Render): Grátis
   • 25MB storage
   • Sem persistência em reboot

✅ Postgres (Render): Grátis
   • 1GB storage
   • Backup manual

Total: R$ 0/mês ✨

Limitações:
  • Sleep em 15min (primeira req demora ~30s)
  • Máx 1GB de dados
  • CPU only (latência ~800ms)
```

### **Configuração Paga (Produção):**

```
✅ Frontend (Vercel Pro): US$ 20/mês
   • 1TB bandwidth
   • Mais serverless resources

✅ Backend (Render Starter): US$ 7/mês
   • Sempre ativo (sem sleep)
   • 1GB RAM
   • CPU dedicado

✅ Redis (Render): US$ 7/mês
   • 1GB storage
   • Persistência garantida

✅ Postgres (Render): US$ 7/mês
   • 10GB storage
   • Backups automáticos

Total: US$ 41/mês (~R$ 210/mês)

Benefícios:
  • Sem sleep (sempre rápido)
  • Mais storage
  • Backups automáticos
  • Suporte prioritário
```

---

## 🔄 PARTE 6: CI/CD (Deploy Automático)

### **Auto-deploy configurado:**

```
1. Fazer alteração no código
2. Commit: git commit -m "feat: nova feature"
3. Push: git push origin main

4. Render detecta push
   → Rebuild backend automaticamente
   → Deploy em ~5 minutos

5. Vercel detecta push
   → Rebuild frontend automaticamente
   → Deploy em ~2 minutos

Resultado: Deploy completo em ~7 minutos! 🚀
```

### **Preview Deployments (Vercel):**

```
Branch feature/nova-feature
  → Vercel cria URL preview
  → https://orbis-git-feature-nova-feature.vercel.app
  
Testar feature isoladamente antes de merge!
```

---

## ✅ CHECKLIST DE DEPLOY

### **Antes do Deploy:**

- [ ] Código commitado e pushed para GitHub
- [ ] `.gitignore` atualizado (sem .env)
- [ ] URLs de API configuradas no frontend
- [ ] Variáveis de ambiente documentadas
- [ ] Health check funcionando localmente
- [ ] Testes passando

### **Durante o Deploy:**

- [ ] Render: Redis criado e URL copiada
- [ ] Render: Postgres criado e URL copiada
- [ ] Render: Web Service configurado
- [ ] Render: Variáveis de ambiente adicionadas
- [ ] Render: Deploy bem-sucedido (green checkmark)
- [ ] Vercel: Projeto importado
- [ ] Vercel: Variáveis de ambiente configuradas
- [ ] Vercel: Deploy bem-sucedido

### **Após o Deploy:**

- [ ] Backend: `/health` responde 200 OK
- [ ] Frontend: Abre sem erros
- [ ] Frontend: Consegue fazer login
- [ ] Frontend: Consegue criar sala
- [ ] WebSocket: Conecta ao backend
- [ ] Tradução: Funciona em tempo real
- [ ] Logs: Sem erros críticos

---

## 🐛 TROUBLESHOOTING

### **Backend não inicia:**

```
Verificar logs no Render:
  → Dashboard → orbis-backend → Logs

Erros comuns:
  • "ModuleNotFoundError" → requirements.txt desatualizado
  • "Connection refused" → DATABASE_URL incorreta
  • "Port already in use" → Usar $PORT do Render

Solução:
  → Verificar variáveis de ambiente
  → Re-deploy manual
```

### **Frontend não conecta ao backend:**

```
Console do navegador (F12):
  → Buscar por "Failed to fetch"
  → Verificar URL da API

Erros comuns:
  • CORS error → Adicionar domínio no CORS_ORIGINS
  • 404 Not Found → API_URL incorreta
  • WebSocket failed → WS_URL incorreta

Solução:
  → Verificar config.ts
  → Verificar CORS no backend
  → Re-deploy frontend
```

### **Modelos ML não carregam:**

```
Logs mostram:
  "Failed to load model"
  "Out of memory"

Problema: Free tier Render tem 512MB RAM

Soluções:
  1. Usar modelos menores (base ao invés de large)
  2. Aumentar para Render Starter (1GB RAM)
  3. Desabilitar lazy loading (pre-load na startup)
```

---

## 🎯 PRÓXIMOS PASSOS

### **Melhorias de Performance:**

1. **Adicionar CDN** para assets estáticos
2. **Configurar caching** de respostas API
3. **Otimizar bundle** do frontend
4. **Adicionar Service Worker** para offline support

### **Melhorias de Segurança:**

1. **Rate limiting** mais agressivo
2. **Validação de inputs** mais rigorosa
3. **Logs de auditoria** de ações sensíveis
4. **2FA** para contas de usuário

### **Melhorias de Escalabilidade:**

1. **Load balancer** para múltiplas instâncias
2. **Database read replicas** para leituras
3. **Redis cluster** para cache distribuído
4. **GPU workers** para tradução ultra-rápida

---

## 📞 SUPORTE

**Render:**
- Docs: https://render.com/docs
- Status: https://status.render.com
- Community: https://community.render.com

**Vercel:**
- Docs: https://vercel.com/docs
- Status: https://vercel-status.com
- Discord: https://vercel.com/discord

**Orbis:**
- GitHub Issues: https://github.com/seu-usuario/orbis/issues
- Logs: Render Dashboard → Logs

---

**Última atualização:** 2025-11-18  
**Versão:** Orbis v2.0  
**Deploy time:** ~30 minutos  
**Custo inicial:** R$ 0 (free tier) 🎉
