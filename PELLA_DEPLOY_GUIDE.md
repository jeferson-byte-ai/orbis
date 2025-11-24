# 🚀 DEPLOY NO PELLA.APP - GUIA PASSO A PASSO

## 📋 Antes de começar

✅ Conta criada no Pella.app  
✅ Repositório no GitHub: https://github.com/jeferson-byte-ai/Orbis  
✅ Variáveis de ambiente prontas (ver `.deploy_config.txt`)

---

## 🎯 PASSO 1: Acessar Dashboard

1. Abra: **https://pella.app/dashboard**
2. Faça login se necessário

---

## 🎯 PASSO 2: Criar Nova Aplicação

1. Clique em **"Create New App"** ou **"New Project"**
2. Conecte com GitHub:
   - Clique em **"Connect with GitHub"**
   - Autorize o Pella a acessar seus repositórios
   - Se pedir permissões específicas, aceite

---

## 🎯 PASSO 3: Selecionar Repositório

1. Na lista de repositórios, encontre: **"Orbis"** ou **"jeferson-byte-ai/Orbis"**
2. Clique em **"Select"** ou **"Import"**

---

## 🎯 PASSO 4: Configurar Aplicação

Preencha os campos:

```
App Name: orbis-backend
(ou: orbis-api, orbis-server - escolha o que preferir)

Branch: main

Root Directory: ./
(deixe assim, raiz do projeto)

Runtime: Python 3.11
(ou deixe detectar automaticamente)
```

---

## 🎯 PASSO 5: Comandos de Build

```bash
Build Command:
pip install --upgrade pip && pip install -r requirements.txt

Start Command:
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**⚠️ IMPORTANTE:**
- O `$PORT` é fornecido automaticamente pelo Pella
- Não mude para um port fixo!

---

## 🎯 PASSO 6: Variáveis de Ambiente

Clique em **"Add Environment Variables"** ou **"Environment"**

**COPIE E COLE TODAS essas variáveis:**

(Abra o arquivo `.deploy_config.txt` e copie a seção completa)

```bash
ENVIRONMENT=production
DEBUG=false
PYTHON_VERSION=3.11
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=postgresql://neondb_owner:npg_OBmJPexT0v9y@ep-noisy-morning-ac52efim-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require
REDIS_URL=redis://default:AaAoAAIncDI0YTg4OGM5ZTM3MmM0YzA2YmFjYzgyYTU2MWQxODg5ZnAyNDEwMDA@living-liger-41000.upstash.io:6379
SECRET_KEY=lrmwIEZm5TUceGwJS7O6fogm_uIBVG76cJtoPh-QGMw
JWT_SECRET=A87-TNMDtAjfSjOyKgaqVwOMDO2g5gYqyFRKLaaBFr4
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://*.vercel.app
ASR_MODEL=openai/whisper-base
ASR_DEVICE=cpu
MT_MODEL=facebook/nllb-200-distilled-600M
MT_DEVICE=cpu
TTS_DEVICE=cpu
TARGET_LATENCY_MS=800
MAX_ROOM_PARTICIPANTS=50
ML_LAZY_LOAD=true
ML_AUTO_UNLOAD_ENABLED=true
ML_UNLOAD_AFTER_IDLE_SECONDS=3600
RATE_LIMIT_PER_MINUTE=60
MAX_CONNECTIONS_PER_ROOM=50
```

**💡 DICA:** Algumas plataformas permitem colar em formato `.env`. Outras precisam adicionar uma por uma.

---

## 🎯 PASSO 7: Deploy!

1. Revise todas as configurações
2. Clique em **"Deploy"** ou **"Create App"**
3. **Aguarde 5-15 minutos** (primeira vez demora mais)

### Durante o Deploy:

Você verá logs assim:

```
📦 Cloning repository...
🔧 Installing dependencies...
📥 Downloading models... (se ML_LAZY_LOAD=false)
🚀 Starting server...
✅ Deployed!
```

---

## 🎯 PASSO 8: Copiar URL do Backend

Após o deploy bem-sucedido:

1. Procure por **"Your app is live at:"** ou similar
2. Copie a URL completa, exemplo:
   ```
   https://orbis-backend.pella.app
   ou
   https://orbis-backend-xyz123.pella.app
   ```

3. **SALVE ESSA URL!** Você vai precisar para:
   - Configurar frontend
   - Atualizar CORS
   - Testar API

---

## 🎯 PASSO 9: Testar Backend

Abra no navegador:

```
https://SUA_URL_AQUI/health
```

**✅ Deve retornar:**

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production"
}
```

**❌ Se der erro:**
- Verifique os logs no Pella Dashboard
- Verifique variáveis de ambiente
- Verifique se DATABASE_URL e REDIS_URL estão corretas

---

## 🎯 PASSO 10: Atualizar Frontend

Após obter a URL do backend:

1. Abra: `frontend/src/config.ts`
2. Substitua:
   ```typescript
   const PRODUCTION_BACKEND_URL = 'SEU_BACKEND_URL';
   ```
   Por:
   ```typescript
   const PRODUCTION_BACKEND_URL = 'https://orbis-backend.pella.app';
   ```
   (use sua URL real)

3. Salve o arquivo

---

## ✅ CHECKLIST

- [ ] Aplicação criada no Pella
- [ ] Repositório conectado
- [ ] Comandos de build configurados
- [ ] TODAS variáveis de ambiente adicionadas
- [ ] Deploy concluído com sucesso
- [ ] URL do backend copiada
- [ ] Endpoint /health responde OK
- [ ] Frontend atualizado com URL do backend

---

## 🐛 TROUBLESHOOTING

### Erro: "Module not found"
```
Solução: Verificar requirements.txt está na raiz
```

### Erro: "Port already in use"
```
Solução: Usar $PORT nas variáveis, não port fixo
```

### Erro: "Database connection failed"
```
Solução: 
1. Verificar DATABASE_URL
2. Verificar se tem ?sslmode=require
3. Testar conexão no Neon dashboard
```

### Erro: "Build timeout"
```
Solução:
1. Adicionar ML_LAZY_LOAD=true (modelos baixam sob demanda)
2. Reduzir tamanho de dependências
```

---

## 📞 Próximo Passo

Após completar o Pella:
- Ver: `DEPLOY_NO_CREDIT_CARD.md` - Parte 4 (Deploy Vercel)

---

**Boa sorte! 🚀**
