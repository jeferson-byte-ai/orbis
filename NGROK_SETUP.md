# 🌐 Setup Ngrok - Orbis Backend

## 📦 PASSO 1: Baixar e Instalar Ngrok

### **1.1 Download**

1. Acesse: https://ngrok.com/download
2. Clique em **"Download for Windows"**
3. Salve o arquivo `ngrok.zip`

### **1.2 Extrair**

1. Vá para a pasta `Downloads`
2. Clique com botão direito em `ngrok.zip`
3. **Extrair aqui** ou **Extrair para ngrok/**
4. Você terá um arquivo `ngrok.exe`

### **1.3 Mover para pasta do projeto (opcional)**

Copie `ngrok.exe` para:
```
c:\Users\Jeferson\Documents\orbis\
```

---

## 🔧 PASSO 2: Criar Conta Ngrok (Grátis)

1. Acesse: https://dashboard.ngrok.com/signup
2. **Sign up** com Google ou GitHub (rápido)
3. Após login, copie seu **Authtoken**
4. Vai estar em: https://dashboard.ngrok.com/get-started/your-authtoken

**Exemplo de authtoken:**
```
2aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5
```

---

## ⚙️ PASSO 3: Configurar Ngrok

Abra PowerShell/CMD na pasta onde está o `ngrok.exe` e execute:

```powershell
.\ngrok config add-authtoken SEU_TOKEN_AQUI
```

Troque `SEU_TOKEN_AQUI` pelo token que você copiou!

---

## 🚀 PASSO 4: Rodar Backend + Ngrok

### **4.1 Terminal 1: Rodar Backend**

Abra um terminal e rode:

```powershell
cd c:\Users\Jeferson\Documents\orbis
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Aguarde aparecer:**
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### **4.2 Terminal 2: Rodar Ngrok**

Abra OUTRO terminal e rode:

```powershell
cd c:\Users\Jeferson\Documents\orbis
.\ngrok http 8000
```

**Vai aparecer algo assim:**

```
ngrok

Session Status                online
Account                       Seu Nome (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       50ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123def456.ngrok.io -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**COPIE A URL:**
```
https://abc123def456.ngrok.io
```

**⚠️ IMPORTANTE:**
- A URL muda cada vez que você reinicia o Ngrok
- No plano FREE, a sessão dura até você fechar o terminal
- Quando fechar e abrir de novo, a URL será diferente

---

## 🧪 PASSO 5: Testar Backend

Abra no navegador:
```
https://abc123def456.ngrok.io/health
```

**Deve retornar:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production"
}
```

✅ **Se aparecer isso, seu backend está online!**

---

## 🌐 PASSO 6: Atualizar Frontend

Edite: `frontend/src/config.ts`

```typescript
const PRODUCTION_BACKEND_URL = 'https://abc123def456.ngrok.io';
```

**⚠️ Troque pela sua URL real do Ngrok!**

Salve e faça commit:

```powershell
git add frontend/src/config.ts
git commit -m "feat: configurar URL do Ngrok"
git push origin main
```

---

## 📊 PASSO 7: Deploy Frontend (Vercel)

1. Acesse: https://vercel.com
2. Login com GitHub
3. **Import Git Repository**
4. Selecione: **orbis**
5. Configure:
   - Framework: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
6. **Deploy!**

Após deploy, copie a URL:
```
https://orbis.vercel.app
```

---

## ✅ PASSO 8: Atualizar CORS

No arquivo `.env` local, adicione a URL do Vercel:

```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://orbis.vercel.app,https://*.ngrok.io
```

**Reinicie o backend** (Ctrl+C e rodar de novo)

---

## 🎉 TUDO FUNCIONANDO!

**Seu setup:**
```
Usuário acessa → https://orbis.vercel.app (Frontend)
                      ↓
                 https://abc123.ngrok.io (seu PC via Ngrok)
                      ↓
                 Backend rodando local (seu PC)
                      ↓
         PostgreSQL (Neon) + Redis (Upstash)
```

---

## 💡 DICAS:

### **Manter Ngrok sempre rodando:**

Crie um script `start_ngrok.bat`:

```batch
@echo off
cd c:\Users\Jeferson\Documents\orbis
start cmd /k "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3
start cmd /k "ngrok http 8000"
```

Duplo clique para rodar tudo de uma vez!

### **URL fixa (pago):**

Plano pago do Ngrok ($8/mês) permite URL fixa:
```
https://orbis.ngrok.io (sempre a mesma)
```

---

## ⚠️ LIMITAÇÕES (Plano FREE):

- ❌ URL muda toda vez que reinicia
- ❌ Sessões de 2 horas (depois reconecta)
- ❌ 40 conexões/minuto
- ✅ Suficiente para demos e testes!

---

## 🚀 UPGRADE FUTURO:

Quando tiver cartão:
1. Deploy backend no Render ($0, mas pede cartão)
2. URL fixa permanente
3. Always-on (não precisa PC ligado)

---

**Criado:** 2025-11-25  
**Versão:** Orbis v2.0  
**Setup:** Local + Ngrok + Vercel ✨
