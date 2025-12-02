# 🚀 Deploy Rápido do Backend no Railway

## ✅ **Passo 1: Criar Conta no Railway**

1. Acesse: https://railway.app/
2. Clique em **"Start a New Project"**
3. Faça login com GitHub (é grátis, sem cartão)

## ✅ **Passo 2: Conectar o Repositório**

1. No Railway, clique em **"Deploy from GitHub repo"**
2. Selecione o repositório: `jeferson-byte-ai/orbis`
3. Clique em **"Deploy Now"**

## ✅ **Passo 3: Configurar Variáveis de Ambiente**

No Railway, vá em **Variables** e adicione:

```env
# Database (Railway fornece automaticamente)
DATABASE_URL=postgresql://...  # Railway vai preencher isso

# JWT Secret (gere um novo)
JWT_SECRET_KEY=sua-chave-secreta-aqui-min-32-chars

# Configurações
ENVIRONMENT=production
DEBUG=False
API_HOST=0.0.0.0
API_PORT=8000

# CORS (adicione seu domínio do Vercel)
CORS_ORIGINS=https://orbis-omega.vercel.app,http://localhost:3000

# ML Services (desabilitar para economizar recursos)
ENABLE_TRANSCRIPTION=true
ENABLE_TRANSLATION=true
ENABLE_VOICE_CLONING=true
ML_LAZY_LOAD=true
```

## ✅ **Passo 4: Adicionar PostgreSQL**

1. No Railway, clique em **"+ New"**
2. Selecione **"Database" → "PostgreSQL"**
3. Railway vai conectar automaticamente

## ✅ **Passo 5: Pegar a URL do Backend**

1. Vá em **Settings** do seu serviço
2. Copie a **Public URL** (algo como: `https://orbis-backend-production.up.railway.app`)

## ✅ **Passo 6: Atualizar o Frontend**

Edite `frontend/vercel.json`:

```json
{
    "env": {
        "VITE_API_BASE_URL": "https://SUA-URL-DO-RAILWAY.up.railway.app",
        "VITE_WS_BASE_URL": "wss://SUA-URL-DO-RAILWAY.up.railway.app"
    },
    "rewrites": [
        {
            "source": "/(.*)",
            "destination": "/index.html"
        }
    ]
}
```

## ✅ **Passo 7: Fazer Redeploy do Frontend**

```bash
git add frontend/vercel.json
git commit -m "Update: Use Railway backend in production"
git push origin main
```

---

## 🎉 **Pronto!**

Agora seu backend está em produção e o WebSocket vai funcionar perfeitamente no mobile!

**Vantagens:**
- ✅ Sem limitações de WebSocket
- ✅ Gratuito (500h/mês)
- ✅ HTTPS automático
- ✅ PostgreSQL incluído
- ✅ Deploy automático no git push

**Próximos passos:**
1. Siga os passos acima
2. Me avise quando terminar
3. Vou te ajudar a testar!
