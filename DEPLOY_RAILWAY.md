# 🚂 Deploy GRATUITO Orbis no Railway.app
## **Com Redis AVANÇADO via Docker**

---

## 🎯 **POR QUE RAILWAY?**

```
✅ Deploy via docker-compose (configurações avançadas!)
✅ Redis completo com redis.conf personalizado
✅ 512MB RAM gratuito
✅ $5 crédito grátis/mês (suficiente para hobby)
✅ Persistência de dados em volumes
✅ PostgreSQL grátis também
✅ CI/CD automático com GitHub
```

---

## 📋 **PRÉ-REQUISITOS**

- ✅ Código no GitHub
- ✅ Conta GitHub (para login)
- ✅ 20 minutos de tempo

---

## 🚀 **PASSO 1: Preparar Projeto**

### **1.1 Atualizar docker-compose para produção**

O `docker-compose.yml` atual já está bom, mas vamos criar uma versão otimizada:

`docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-orbis}
      POSTGRES_USER: ${POSTGRES_USER:-orbis}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U orbis"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server /usr/local/etc/redis/redis.conf --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD}

  backend:
    build:
      context: .
      dockerfile: Dockerfile.railway
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      # Database
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      
      # Redis
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      
      # Security
      SECRET_KEY: ${SECRET_KEY}
      JWT_SECRET: ${JWT_SECRET}
      
      # API
      ENVIRONMENT: production
      DEBUG: false
      API_HOST: 0.0.0.0
      API_PORT: ${PORT:-8000}
      
      # CORS
      CORS_ORIGINS: ${CORS_ORIGINS}
      
      # ML Models
      ASR_MODEL: openai/whisper-base
      ASR_DEVICE: cpu
      MT_MODEL: facebook/nllb-200-distilled-600M
      MT_DEVICE: cpu
      TTS_DEVICE: cpu
      
      # Features
      TARGET_LATENCY_MS: 800
      MAX_ROOM_PARTICIPANTS: 50
      ML_LAZY_LOAD: true
      ML_AUTO_UNLOAD_ENABLED: true
      ML_UNLOAD_AFTER_IDLE_SECONDS: 3600
      
    ports:
      - "${PORT:-8000}:${PORT:-8000}"
    command: >
      sh -c "
        echo 'Aguardando serviços...' &&
        sleep 5 &&
        echo 'Iniciando backend...' &&
        uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
      "

volumes:
  postgres_data:
  redis_data:
```

### **1.2 Criar Dockerfile otimizado**

`Dockerfile.railway`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY backend/ ./backend/
COPY data/ ./data/

# Criar diretórios necessários
RUN mkdir -p data/models data/voices data/uploads logs

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Comando padrão
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **1.3 Commit mudanças**

```bash
git add .
git commit -m "feat: adicionar configuração Railway com Redis avançado"
git push origin main
```

---

## ☁️ **PASSO 2: Deploy no Railway**

### **2.1 Criar conta**

1. Acesse: **https://railway.app**
2. Clique em **"Login with GitHub"**
3. Autorize Railway no GitHub

### **2.2 Criar novo projeto**

1. Dashboard → **"New Project"**
2. Escolha: **"Deploy from GitHub repo"**
3. Selecione: **"orbis"** (seu repositório)
4. Railway detecta automaticamente o `docker-compose.yml`

### **2.3 Configurar serviços**

Railway vai criar 3 serviços automaticamente:
- ✅ **postgres** (database)
- ✅ **redis** (cache)
- ✅ **backend** (API)

### **2.4 Adicionar variáveis de ambiente**

Clique em **backend** → **Variables**:

```bash
# GERAR SENHAS SEGURAS PRIMEIRO!
# No terminal local:
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
```

Adicione no Railway:

```env
# Database
POSTGRES_DB=orbis
POSTGRES_USER=orbis
POSTGRES_PASSWORD=<senha-gerada-acima>

# Redis
REDIS_PASSWORD=<senha-gerada-acima>

# Security
SECRET_KEY=<chave-gerada-acima>
JWT_SECRET=<chave-gerada-acima>

# API
ENVIRONMENT=production
DEBUG=false
PORT=8000

# CORS (atualize com seu domínio Vercel depois)
CORS_ORIGINS=https://orbis.vercel.app,http://localhost:3000

# ML
ASR_MODEL=openai/whisper-base
ASR_DEVICE=cpu
MT_MODEL=facebook/nllb-200-distilled-600M
MT_DEVICE=cpu

# Features
TARGET_LATENCY_MS=800
MAX_ROOM_PARTICIPANTS=50
ML_LAZY_LOAD=true
ML_AUTO_UNLOAD_ENABLED=true
```

### **2.5 Configurar Redis customizado**

1. Clique no serviço **redis**
2. Vá em **Settings** → **Deploy**
3. Altere **Start Command** para:
   ```bash
   redis-server /app/redis.conf --requirepass $REDIS_PASSWORD
   ```

4. Em **Volumes**, adicione:
   - **Mount Path**: `/app/redis.conf`
   - **Source**: `./redis.conf` (do repositório)

### **2.6 Deploy!**

1. Railway vai detectar mudanças e fazer deploy automático
2. Aguarde ~5-10 minutos (primeira vez)
3. Status deve ficar **verde** ✅

### **2.7 Obter URL pública**

1. Clique em **backend**
2. Vá em **Settings** → **Networking**
3. Clique em **Generate Domain**
4. Copie URL: `https://orbis-backend-production.up.railway.app`

---

## 🌐 **PASSO 3: Deploy Frontend (Vercel)**

### **3.1 Atualizar configuração**

`frontend/src/config.ts`:

```typescript
const isDevelopment = import.meta.env.MODE === 'development';

export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://orbis-backend-production.up.railway.app'; // URL do Railway

export const WS_BASE_URL = isDevelopment
  ? 'ws://localhost:8000/api'
  : 'wss://orbis-backend-production.up.railway.app/api';
```

Commit:
```bash
git add frontend/src/config.ts
git commit -m "feat: configurar URLs de produção Railway"
git push
```

### **3.2 Deploy no Vercel**

1. Acesse: **https://vercel.com**
2. Login with GitHub
3. **New Project** → Importar **"orbis"**
4. Configurar:
   ```
   Framework: Vite
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: dist
   ```

5. Environment Variables:
   ```env
   VITE_API_URL=https://orbis-backend-production.up.railway.app
   VITE_WS_URL=wss://orbis-backend-production.up.railway.app
   ```

6. **Deploy**!

7. Copiar URL: `https://orbis.vercel.app`

### **3.3 Atualizar CORS no Railway**

Volte ao Railway → **backend** → **Variables**:

```env
CORS_ORIGINS=https://orbis.vercel.app,https://orbis-git-*.vercel.app
```

Re-deploy vai acontecer automaticamente.

---

## ✅ **PASSO 4: Testar Tudo**

### **4.1 Backend**

```bash
# Health check
curl https://orbis-backend-production.up.railway.app/health

# Esperado:
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production"
}
```

### **4.2 Redis (via backend)**

```bash
# Teste de cache
curl -X POST https://orbis-backend-production.up.railway.app/api/test-redis

# Esperado:
{
  "redis": "ok",
  "ping": "PONG"
}
```

### **4.3 Frontend**

1. Abra `https://orbis.vercel.app`
2. Registre uma conta
3. Faça login
4. Crie uma sala
5. Teste tradução em tempo real

---

## 🔧 **CONFIGURAÇÕES AVANÇADAS DO REDIS**

### **Verificar que redis.conf está ativo:**

No Railway → Redis → **Logs**:

```
Server initialized
Reading the configuration file
Configuration loaded
Ready to accept connections
```

### **Configurações disponíveis no seu redis.conf:**

```bash
✅ Persistência (RDB + AOF)
   • Backups automáticos a cada 15min
   • AOF para recuperação instantânea

✅ Memory Management
   • maxmemory: 256MB
   • eviction: allkeys-lru (remove menos usado)

✅ Performance
   • Lazy freeing (não bloqueia)
   • Pipeline otimizado
   • TCP keepalive

✅ Monitoring
   • Slow log ativado
   • Latency monitor

✅ Security
   • Password via env var
   • Bind 0.0.0.0 (interno Railway)
```

### **Personalizar ainda mais:**

Edite `redis.conf` e commit:

```bash
# Aumentar maxmemory (se pagar)
maxmemory 512mb

# Mudar política de eviction
maxmemory-policy volatile-lru  # Remove apenas keys com TTL

# Aumentar persistência
save 60 1000  # Salvar mais frequentemente

git add redis.conf
git commit -m "feat: otimizar Redis config"
git push
```

Railway faz re-deploy automático!

---

## 💰 **CUSTOS**

### **Plano FREE (Recomendado para testes):**

```
Railway:
  ✅ $5 crédito/mês
  ✅ ~140h uptime (suficiente para testes)
  ✅ 512MB RAM
  ✅ Redis + Postgres inclusos
  
Vercel:
  ✅ 100% grátis
  ✅ 100GB bandwidth
  
TOTAL: R$ 0/mês
```

### **Plano HOBBY (Produção leve):**

```
Railway:
  💰 $5/mês (fixo, sem consumo)
  ✅ Uptime ilimitado
  ✅ 512MB RAM
  ✅ Redis + Postgres
  ✅ Todas configurações avançadas
  
Vercel:
  ✅ Grátis (ou $20 Pro para analytics)
  
TOTAL: $5/mês (~R$ 25/mês) 🎉
```

---

## 🎯 **VANTAGENS vs RENDER**

| Feature | Render Free | Railway Hobby |
|---------|-------------|---------------|
| **Redis Config** | ✅ Básico | ✅ **Avançado (redis.conf)** |
| **Persistência** | ❌ Não | ✅ **Sim (RDB + AOF)** |
| **Docker Compose** | ❌ Separado | ✅ **Direto** |
| **Memory** | 25MB | ✅ **512MB** |
| **Preço** | Grátis | 💰 **$5/mês** |
| **Sleep** | ✅ Sim (15min) | ❌ **Sempre on** |

---

## 🔄 **CI/CD AUTOMÁTICO**

```
1. Editar código
2. git push origin main
3. Railway detecta
4. Build automático
5. Deploy em ~3 minutos
6. Zero downtime!
```

---

## 🐛 **TROUBLESHOOTING**

### **Redis não conecta:**

```bash
# Ver logs
Railway → redis → Logs

# Verificar se redis.conf foi carregado
grep "Configuration loaded" nos logs

# Testar conexão
Railway → redis → Connect → Copy URL
redis-cli -u <REDIS_URL> ping
```

### **Backend não inicia:**

```bash
# Ver logs
Railway → backend → Logs

# Erros comuns:
"Connection refused" → REDIS_URL incorreta
"Unable to connect" → Senhas diferentes

# Solução:
Verificar que REDIS_PASSWORD é igual em todos serviços
```

---

## 📊 **MONITORAMENTO**

### **Railway Dashboard:**

```
1. Métricas de CPU/RAM em tempo real
2. Logs de cada serviço
3. Network usage
4. Deployment history
```

### **Redis Insights (Opcional):**

```bash
# Instalar localmente
docker run -d -p 8001:8001 redislabs/redisinsight

# Conectar ao Railway Redis
URL: <copiar do Railway>
Password: <REDIS_PASSWORD>

# Ver:
• Comandos/segundo
• Hit rate
• Memory usage
• Slow queries
```

---

## 🎉 **PRONTO!**

Agora você tem:

✅ **Deploy 100% gratuito** (ou $5/mês para sempre on)  
✅ **Redis AVANÇADO** com seu `redis.conf` personalizado  
✅ **Configurações iguais** ao desenvolvimento local  
✅ **Persistência** de dados garantida  
✅ **CI/CD** automático  
✅ **Escalável** (fácil upgrade quando crescer)

---

## 🔗 **LINKS ÚTEIS**

- **Railway Docs:** https://docs.railway.app
- **Railway Status:** https://status.railway.app
- **Vercel Docs:** https://vercel.com/docs
- **Redis Config:** https://redis.io/docs/management/config/

---

**Última atualização:** 2025-11-24  
**Tempo de deploy:** ~20 minutos  
**Custo inicial:** R$ 0 (ou R$ 25/mês para produção) 🚂
