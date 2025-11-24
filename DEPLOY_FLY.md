# 🪂 Deploy GRÁTIS no Fly.io (Alternativa 100% Gratuita)

## ⚠️ ATENÇÃO
Este guia é para quem quer deploy **100% GRÁTIS** mas está disposto a gastar **mais tempo** configurando.

**Se você pode pagar $5/mês, use Railway** (muito mais fácil) - Veja `DEPLOY_RAILWAY.md`

---

## 🎯 Por que Fly.io?

```
✅ 100% grátis (sem cartão de crédito)
✅ Redis customizado (via Dockerfile)
✅ 3GB storage permanente
✅ Persistência garantida
✅ Sempre ativo (sem sleep)

❌ Configuração mais complexa
❌ Precisa converter docker-compose
❌ Documentação confusa
```

---

## 📋 Pré-requisitos

- ✅ Código no GitHub
- ✅ Conta Fly.io (grátis)
- ✅ 1-2 horas de tempo
- ✅ Paciência 😅

---

## 🚀 PASSO 1: Instalar Fly CLI

### Windows (PowerShell):
```powershell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

### Linux/Mac:
```bash
curl -L https://fly.io/install.sh | sh
```

Verificar:
```bash
fly version
```

---

## 🔐 PASSO 2: Login

```bash
fly auth signup  # Primeira vez
# ou
fly auth login   # Se já tem conta
```

---

## 📝 PASSO 3: Criar fly.toml

Copie este arquivo na raiz do projeto:

`fly.toml`:

```toml
app = "orbis-production"  # Mude para nome único

[build]
  dockerfile = "Dockerfile.railway"

[env]
  ENVIRONMENT = "production"
  PORT = "8000"
  API_HOST = "0.0.0.0"
  
[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false  # Sempre ativo
  auto_start_machines = true
  min_machines_running = 1
  
  [http_service.concurrency]
    type = "requests"
    soft_limit = 200
    hard_limit = 250

[[services]]
  internal_port = 8000
  protocol = "tcp"
  
  [[services.ports]]
    port = 80
    handlers = ["http"]
    
  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[mounts]
  source = "orbis_data"
  destination = "/app/data"
```

---

## 🗄️ PASSO 4: Criar PostgreSQL

```bash
fly postgres create \
  --name orbis-postgres \
  --region gru \
  --initial-cluster-size 1 \
  --vm-size shared-cpu-1x \
  --volume-size 1
```

Copie a `DATABASE_URL` retornada.

---

## 🔴 PASSO 5: Criar Redis

Fly.io não tem Redis gerenciado, então vamos criar via Dockerfile:

`Dockerfile.redis`:

```dockerfile
FROM redis:7-alpine

# Copiar configuração customizada
COPY redis.conf /usr/local/etc/redis/redis.conf

# Expor porta
EXPOSE 6379

# Comando com configuração
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
```

Criar `fly.redis.toml`:

```toml
app = "orbis-redis"  # Nome único

[build]
  dockerfile = "Dockerfile.redis"

[[services]]
  internal_port = 6379
  protocol = "tcp"
  
[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"

[mounts]
  source = "redis_data"
  destination = "/data"
```

Deploy Redis:

```bash
fly apps create orbis-redis
fly volumes create redis_data --size 1 --app orbis-redis --region gru
fly deploy --config fly.redis.toml --app orbis-redis
```

Obter URL interna:
```bash
fly ips private --app orbis-redis
# Anote o IP: 10.x.x.x
```

---

## 🔧 PASSO 6: Configurar Secrets

```bash
# Database (copie URL do passo 4)
fly secrets set DATABASE_URL="postgres://..."

# Redis (use IP do passo 5)
fly secrets set REDIS_URL="redis://10.x.x.x:6379/0"

# Gerar senhas seguras
fly secrets set SECRET_KEY="$(openssl rand -base64 32)"
fly secrets set JWT_SECRET="$(openssl rand -base64 32)"

# CORS (atualize depois com Vercel)
fly secrets set CORS_ORIGINS="https://orbis.vercel.app"

# ML
fly secrets set ASR_MODEL="openai/whisper-base"
fly secrets set MT_MODEL="facebook/nllb-200-distilled-600M"
```

---

## 🚀 PASSO 7: Deploy Backend

```bash
# Criar app
fly apps create orbis-backend

# Criar volume para dados
fly volumes create orbis_data --size 3 --region gru

# Deploy!
fly deploy

# Ver logs
fly logs
```

Obter URL:
```bash
fly info
# URL: https://orbis-backend.fly.dev
```

---

## 🌐 PASSO 8: Deploy Frontend (Vercel)

Mesmo processo do Railway - veja `DEPLOY_RAILWAY.md` seção "PASSO 3"

Atualizar `frontend/src/config.ts`:
```typescript
export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://orbis-backend.fly.dev';  // URL do Fly.io
```

---

## ✅ PASSO 9: Testar

```bash
# Health check
curl https://orbis-backend.fly.dev/health

# Logs em tempo real
fly logs -a orbis-backend

# SSH no container
fly ssh console -a orbis-backend

# Verificar Redis
fly ssh console -a orbis-redis
> redis-cli ping
```

---

## 🔧 Comandos Úteis

```bash
# Ver apps
fly apps list

# Escalar (mudar RAM/CPU)
fly scale vm shared-cpu-2x --memory 512

# Ver métricas
fly dashboard

# Reiniciar
fly apps restart orbis-backend

# Destruir (cuidado!)
fly apps destroy orbis-backend
```

---

## 💰 Custos

```
Free Tier Fly.io:
  ✅ 3 apps grátis
  ✅ 3GB storage
  ✅ 160GB bandwidth/mês
  ✅ Shared CPU

Você vai usar:
  • 1 app: orbis-backend
  • 1 app: orbis-redis
  • 1 app: orbis-postgres (grátis)
  
Total: R$ 0/mês ✨

Limite:
  • 3 VMs máximo
  • Storage adicional: $0.15/GB
```

---

## 🐛 Troubleshooting

### **Redis não conecta:**
```bash
# Verificar rede privada
fly ips private -a orbis-redis

# Testar conexão
fly ssh console -a orbis-backend
> nc -zv 10.x.x.x 6379
```

### **App crashando:**
```bash
# Ver logs detalhados
fly logs -a orbis-backend

# SSH e debugar
fly ssh console -a orbis-backend
> cat /app/logs/*.log
```

### **Fora de recursos:**
```bash
# Ver uso
fly dashboard

# Escalar down
fly scale count 1 -a orbis-backend
```

---

## ⚖️ Fly.io vs Railway

| Feature | Fly.io | Railway |
|---------|--------|---------|
| **Preço** | Grátis | $5/mês |
| **Configuração** | 2h | 20min |
| **Complexidade** | Alta | Baixa |
| **Redis Config** | ✅ Sim | ✅ Sim |
| **Docker Compose** | ❌ Não | ✅ Sim |
| **Suporte** | Forum | Discord |

**Recomendação:** Se tem $5/mês, use Railway. Muito mais fácil!

---

## 🎉 PRONTO!

Agora você tem:
✅ Deploy 100% grátis
✅ Redis customizado (redis.conf)
✅ Persistência garantida
✅ Escalável quando crescer

**PORÉM** gastou 2h configurando vs 20min no Railway 😅

---

**Precisa de ajuda?**
- Docs: https://fly.io/docs
- Forum: https://community.fly.io
- Status: https://status.fly.io

---

**Última atualização:** 2025-11-24  
**Tempo de deploy:** ~2 horas  
**Custo:** R$ 0/mês 🆓
