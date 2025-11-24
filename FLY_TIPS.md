# 💰 Economizando no Fly.io - Truques e Dicas

## 🎯 **Free Tier Limits**

```
✅ 3 VMs (256MB cada)
✅ 3GB volumes persistentes
✅ 160GB bandwidth/mês
✅ Shared CPU

Você vai usar:
• 1 VM: Backend (512MB)
• 1 VM: Redis (256MB)
• 1 DB: Postgres (grátis)

Total: 2 VMs = ✅ DENTRO DO LIMITE!
```

---

## ⚠️ **CUIDADOS PARA NÃO SER COBRADO**

### **1. NÃO crie VMs extras**
```bash
# Sempre usar flag --app
fly deploy --app orbis-backend-SEU-NOME

# NUNCA fazer só:
fly deploy  # ❌ Pode criar app duplicado
```

### **2. Monitore uso de bandwidth**
```bash
# Ver uso atual
fly dashboard

# Se passar 160GB/mês → cobrado!
# Solução: Otimizar assets, CDN para imagens
```

### **3. Cuidado com volumes grandes**
```bash
# Free tier: 3GB total
# Você alocou:
# - Backend: 3GB (modelos ML)
# - Redis: 1GB
# - Postgres: Não conta

# CUIDADO: Não criar volumes extras!
```

---

## 🚀 **OTIMIZAÇÕES PARA ECONOMIZAR RECURSOS**

### **1. Modelos ML menores**

Em vez de:
```env
ASR_MODEL=openai/whisper-large-v3  # 3GB
```

Use:
```env
ASR_MODEL=openai/whisper-base  # 500MB ✅
MT_MODEL=facebook/nllb-200-distilled-600M  # 1GB ✅
```

**Economia:** ~2GB de storage + RAM

---

### **2. Lazy Loading sempre ON**

```env
ML_LAZY_LOAD=true
ML_AUTO_UNLOAD_ENABLED=true
ML_UNLOAD_AFTER_IDLE_SECONDS=600  # 10min

# Modelos carregam só quando usar
# Descarregam quando ocioso
# Economia: ~1GB RAM
```

---

### **3. Cache agressivo**

`redis.conf`:
```conf
# Já configurado para você:
maxmemory 256mb
maxmemory-policy allkeys-lru  # Remove menos usado

# Redis limpa automaticamente
# Não precisa fazer nada!
```

---

### **4. Compress responses**

Backend já faz! Mas confirme:
```python
# backend/main.py
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Economia:** ~70% bandwidth

---

## 📊 **MONITORAMENTO PROATIVO**

### **Dashboard semanal:**
```bash
# Toda semana, verificar:
fly dashboard

Ver:
• CPU usage < 80%
• Memory < 90%
• Bandwidth < 100GB/mês
• No. de VMs = 2
```

### **Alertas (manual):**
```
Se bandwidth > 120GB:
  ⚠️ Investigar o que tá consumindo
  🔧 Otimizar assets
  🔧 Adicionar CDN (Cloudflare grátis)
```

---

## 💡 **TRUQUES AVANÇADOS**

### **1. Cloudflare como CDN (grátis)**

```
Frontend (Vercel) → Cloudflare → Backend (Fly.io)

Vantagens:
✅ Cache de assets
✅ Reduz bandwidth Fly
✅ DDoS protection
✅ SSL grátis

Como:
1. Adicionar domínio no Cloudflare
2. Apontar DNS para Fly
3. Ativar cache
```

### **2. Comprimir uploads**

```javascript
// Frontend - antes de enviar áudio
const compressedAudio = await compressAudio(audioBlob);

// Economia: ~50% bandwidth uploads
```

### **3. Schedule deploys**

```bash
# Evitar deploys durante horário pico
# Fly pode throttle builds

Melhor horário: Madrugada (menos recursos usados)
```

---

## 🎯 **PLANO DE CRESCIMENTO**

### **0-100 usuários:** FREE
```
✅ Mantém no free tier
✅ Monitora semanalmente
✅ Otimiza quando necessário
```

### **100-500 usuários:** UPGRADE
```
💰 ~$5-10/mês
• Aumentar VM: 512MB → 1GB
• Mais bandwidth
• Backups automáticos
```

### **500+ usuários:** SÉRIO
```
💰 $20-50/mês
• Múltiplas VMs (load balancing)
• PostgreSQL pago (backups)
• Redis maior
• CDN dedicado
```

---

## ⚡ **OTIMIZAÇÃO EXTREMA (Avançado)**

### **1. Shared database connection pool**

```python
# backend/core/database.py
DATABASE_POOL_SIZE = 5  # Baixo para free tier
DATABASE_MAX_OVERFLOW = 2
```

### **2. Rate limiting agressivo**

```python
# Protege contra abuso
RATE_LIMIT_PER_MINUTE = 30  # Em vez de 100
```

### **3. Auto-cleanup**

```python
# Cron job para limpar dados antigos
# Evita crescimento descontrolado do DB

@app.on_event("startup")
async def cleanup_old_data():
    # Deletar salas > 30 dias
    # Deletar uploads > 7 dias
    pass
```

---

## 🚨 **O QUE EVITAR**

❌ **Criar múltiplas apps para teste**
```bash
# Cada app conta no limite!
fly apps list  # Ver todas
fly apps destroy APP-NAME  # Deletar que não usa
```

❌ **Deixar logs acumularem**
```bash
# Fly cobra por storage de logs > 30 dias
# Configure retenção curta
```

❌ **Manter VMs paradas ligadas**
```bash
# Se tá testando e vai parar:
fly scale count 0 --app APP-NAME  # Desliga
fly scale count 1 --app APP-NAME  # Liga depois
```

---

## 📈 **CALCULADORA DE CUSTOS**

```
Cenário atual (FREE):
• 2 VMs (backend + redis)
• 4GB storage total
• 50GB bandwidth/mês (estimado)
• Uptime: 100%

Custo: R$ 0 ✅

---

Cenário crescimento (100 users):
• 2 VMs (512MB cada)
• 5GB storage
• 120GB bandwidth/mês

Custo: R$ 0 (ainda no free tier!) ✅

---

Cenário viralizou (500 users):
• 3 VMs (1GB cada)
• 10GB storage
• 300GB bandwidth

Custo: ~$10-15/mês (~R$ 50-75) 💰
```

---

## ✅ **CHECKLIST DE ECONOMIA**

Setup inicial:
- [ ] Usando modelos ML menores
- [ ] Lazy loading ativado
- [ ] Apenas 2 VMs criadas
- [ ] Volumes ≤ 3GB total
- [ ] GZip compression ativo

Semanal:
- [ ] Verificar dashboard
- [ ] Bandwidth < 150GB
- [ ] Deletar uploads antigos
- [ ] Limpar cache desnecessário

Mensal:
- [ ] Revisar apps criadas
- [ ] Deletar não usadas
- [ ] Otimizar queries lentas
- [ ] Testar performance

---

## 🎁 **BONUS: Migração para Railway (futuro)**

Quando crescer e puder pagar $5/mês:

```bash
# Exportar dados do Fly
fly ssh console --app orbis-backend
pg_dump > backup.sql

# Deploy Railway (5 min)
# Seguir DEPLOY_RAILWAY.md

# Importar dados
psql $DATABASE_URL < backup.sql

# Atualizar DNS
# Frontend aponta para Railway

# Deletar Fly apps
fly apps destroy orbis-backend
fly apps destroy orbis-redis
```

**Migração total: ~30 minutos** 🚀

---

## 💬 **COMUNIDADE FLY.IO**

Se tiver problemas:

- 🌐 Forum: https://community.fly.io
- 📖 Docs: https://fly.io/docs
- 🐦 Twitter: @flydotio
- 💬 Discord: flyio (não oficial)

Pessoal é bem receptivo! 🙂

---

**Lembre-se:** Free tier é GENEROSO, mas tem limites. Monitore e otimize! 🎯
