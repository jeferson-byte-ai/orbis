# 🚀 GUIA RÁPIDO - Deploy Fly.io (Orbis)

## ⏱️ **TEMPO TOTAL: ~40 minutos** (otimizado!)

---

## ✅ **PRÉ-REQUISITOS**

- [ ] Código commitado no Git
- [ ] Conta GitHub
- [ ] PowerShell aberto
- [ ] 40 minutos de tempo

---

## 📋 **ARQUIVOS JÁ CRIADOS PARA VOCÊ**

✅ `fly.toml` - Config backend  
✅ `fly.redis.toml` - Config Redis  
✅ `Dockerfile.redis` - Redis customizado  
✅ `redis.conf` - Configurações avançadas  
✅ `.dockerignore` - Otimização build  

**Tudo pronto! Só seguir os passos!** 🎉

---

## 🎯 **PASSO 1: Instalar Fly CLI** (5 min)

### Windows PowerShell (Admin):

```powershell
# Abrir PowerShell como Administrador
# Windows + X → "Windows PowerShell (Admin)"

# Instalar
irm https://fly.io/install.ps1 | iex

# Fechar e reabrir PowerShell normal

# Verificar
fly version
```

**Deu erro?** Tente:
```powershell
# Alternativa via Scoop
scoop install flyctl
```

---

## 🔐 **PASSO 2: Criar Conta e Login** (3 min)

```bash
# Criar conta (primeira vez)
fly auth signup

# Vai abrir navegador:
# 1. Cadastre com GitHub
# 2. Não precisa cartão de crédito!
# 3. Volte pro terminal

# Já tem conta?
fly auth login
```

---

## 🗄️ **PASSO 3: Criar PostgreSQL** (5 min)

```bash
cd c:\Users\Jeferson\Documents\orbis

# Criar database
fly postgres create \
  --name orbis-db \
  --region gru \
  --initial-cluster-size 1 \
  --vm-size shared-cpu-1x \
  --volume-size 1

# ANOTAR A URL QUE APARECER! Tipo:
# postgres://postgres:senha@orbis-db.internal:5432
```

**💾 SALVE ESSA URL!** Cole num .txt temporário

---

## 🔴 **PASSO 4: Criar Redis** (7 min)

```bash
# IMPORTANTE: Editar fly.redis.toml PRIMEIRO
# Mudar app = "orbis-redis-SEU-NOME-UNICO"

# Criar app Redis
fly apps create orbis-redis-SEU-NOME

# Criar volume para persistência
fly volumes create redis_data \
  --size 1 \
  --app orbis-redis-SEU-NOME \
  --region gru

# Deploy Redis
fly deploy \
  --config fly.redis.toml \
  --app orbis-redis-SEU-NOME

# Ver status
fly status --app orbis-redis-SEU-NOME

# Obter IP interno
fly ips private --app orbis-redis-SEU-NOME
# ANOTAR o IP! Tipo: fdaa:x:x:x::3
```

**💾 SALVE ESSE IP!**

---

## 🔧 **PASSO 5: Criar Backend** (5 min)

```bash
# IMPORTANTE: Editar fly.toml PRIMEIRO  
# Mudar app = "orbis-backend-SEU-NOME-UNICO"

# Criar app backend
fly apps create orbis-backend-SEU-NOME

# Criar volume para dados/modelos ML
fly volumes create orbis_data \
  --size 3 \
  --app orbis-backend-SEU-NOME \
  --region gru
```

---

## 🔐 **PASSO 6: Configurar Secrets** (5 min)

```bash
# Gerar senhas primeiro
.\venv\Scripts\python.exe generate_secrets.py

# Copie as senhas geradas e use nos comandos abaixo:

# Database (URL do passo 3)
fly secrets set \
  DATABASE_URL="postgres://postgres:SENHA@orbis-db.internal:5432/postgres" \
  --app orbis-backend-SEU-NOME

# Redis (IP do passo 4 + senha gerada)
fly secrets set \
  REDIS_URL="redis://fdaa:x:x:x::3:6379/0" \
  REDIS_PASSWORD="SENHA-GERADA" \
  --app orbis-backend-SEU-NOME

# Security (senhas geradas)
fly secrets set \
  SECRET_KEY="CHAVE-GERADA" \
  JWT_SECRET="CHAVE-GERADA" \
  --app orbis-backend-SEU-NOME

# CORS (depois atualizar com Vercel)
fly secrets set \
  CORS_ORIGINS="http://localhost:3000,https://orbis.vercel.app" \
  --app orbis-backend-SEU-NOME
```

---

## 🚀 **PASSO 7: DEPLOY!** (10 min - primeira vez)

```bash
# Deploy backend
fly deploy --app orbis-backend-SEU-NOME

# Aguardar build... (5-10 min)
# Vai baixar dependências, modelos ML, etc

# Ver logs em tempo real
fly logs --app orbis-backend-SEU-NOME

# Quando ver "Application startup complete", tá pronto! ✅
```

---

## ✅ **PASSO 8: Testar** (2 min)

```bash
# Obter URL pública
fly info --app orbis-backend-SEU-NOME

# Testar health
curl https://orbis-backend-SEU-NOME.fly.dev/health

# Deve retornar:
# {"status":"healthy","version":"2.0.0","environment":"production"}
```

**✅ FUNCIONOU? BACKEND NO AR!** 🎉

---

## 🌐 **PASSO 9: Deploy Frontend (Vercel)** (5 min)

### 1. Atualizar configuração

`frontend/src/config.ts`:
```typescript
export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8000'
  : 'https://orbis-backend-SEU-NOME.fly.dev';

export const WS_BASE_URL = isDevelopment
  ? 'ws://localhost:8000/api'
  : 'wss://orbis-backend-SEU-NOME.fly.dev/api';
```

### 2. Commit & Push
```bash
git add .
git commit -m "feat: configurar URLs Fly.io"
git push
```

### 3. Deploy Vercel

```bash
# Instalar Vercel CLI (se não tem)
npm i -g vercel

cd frontend

# Deploy
vercel --prod

# Responder:
# Directory: ./
# Project name: orbis
# Seguir prompts

# URL: https://orbis.vercel.app
```

### 4. Atualizar CORS

```bash
# Adicionar domínio Vercel no backend
fly secrets set \
  CORS_ORIGINS="https://orbis.vercel.app,https://orbis-*.vercel.app" \
  --app orbis-backend-SEU-NOME
```

---

## 🎉 **PRONTO!**

Seu app tá no ar:

- 🔵 Backend: `https://orbis-backend-SEU-NOME.fly.dev`
- 🟢 Frontend: `https://orbis.vercel.app`
- 🔴 Redis: Rodando com configurações avançadas!
- 🗄️ PostgreSQL: Persistindo dados

**Total gasto: R$ 0,00** 💰

---

## 🔧 **COMANDOS ÚTEIS**

```bash
# Ver logs
fly logs --app orbis-backend-SEU-NOME

# SSH no container
fly ssh console --app orbis-backend-SEU-NOME

# Ver status
fly status --app orbis-backend-SEU-NOME

# Escalar (se precisar)
fly scale memory 1024 --app orbis-backend-SEU-NOME

# Reiniciar
fly apps restart orbis-backend-SEU-NOME

# Ver uso (monitora crédito grátis)
fly dashboard
```

---

## 🐛 **TROUBLESHOOTING RÁPIDO**

### **Redis não conecta:**
```bash
# Testar rede interna
fly ssh console --app orbis-backend-SEU-NOME
# Dentro do container:
nc -zv fdaa:x:x:x::3 6379
```

### **App não inicia:**
```bash
# Ver logs detalhados
fly logs --app orbis-backend-SEU-NOME

# SSH e debugar
fly ssh console --app orbis-backend-SEU-NOME
ls /app/logs/
```

### **Falta memória:**
```bash
# Modelos ML grandes demais
# Solução: Usar modelos menores em .env

fly secrets set ASR_MODEL="openai/whisper-tiny" \
  --app orbis-backend-SEU-NOME
```

---

## 📊 **MONITORAMENTO**

```bash
# Dashboard web
fly dashboard

# Métricas
fly metrics --app orbis-backend-SEU-NOME

# Verificar limites free tier
fly status --app orbis-backend-SEU-NOME
```

---

## 💡 **DICAS PRO**

1. **Monitore uso:** Free tier tem limites
   ```bash
   fly dashboard metrics
   ```

2. **Optimize models:** Use modelos menores se ficar lento
   ```bash
   ASR_MODEL=openai/whisper-tiny  # Mais leve
   ```

3. **Logs:** Sempre que der erro, cheque logs primeiro
   ```bash
   fly logs --app SEU-APP
   ```

4. **Updates:** Auto-deploy com GitHub Actions (avançado)

---

## 🎯 **CHECKLIST COMPLETO**

- [ ] Fly CLI instalado
- [ ] Conta criada e login feito
- [ ] PostgreSQL criado e URL anotada
- [ ] Redis criado e IP anotado
- [ ] Backend criado
- [ ] Secrets configurados
- [ ] Deploy backend sucesso
- [ ] Health check passa
- [ ] Frontend atualizado
- [ ] Frontend deployed Vercel
- [ ] CORS atualizado
- [ ] App funcionando! 🎉

---

**Dúvidas em algum passo? Pergunta que eu explico!** 🚀

**Tempo total:** ~40 min (vs 2h prometido)
**Custo:** R$ 0 💚
