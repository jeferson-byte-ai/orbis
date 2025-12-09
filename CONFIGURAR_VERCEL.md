# 🚀 CONFIGURAÇÃO COMPLETA - VERCEL + NGROK

## ✅ **CONFIGURADO PARA VOCÊ!**

URLs configuradas:
- **API:** `https://convolutionary-staminal-caren.ngrok-free.dev`
- **WebSocket:** `wss://convolutionary-staminal-caren.ngrok-free.dev`

---

## 📋 **PASSO A PASSO**

### **1. Configurar ambiente Local** ✅

**Opção A - Automático:**
```bash
# Clique duas vezes neste arquivo:
setup-env.bat
```

**Opção B - Manual:**
```bash
cd c:\Users\Jeferson\Documents\orbis\frontend
copy .env.example .env
```

Depois **reinicie o dev server:**
```bash
# Parar atual (Ctrl+C)
npm run dev
```

---

### **2. Configurar no Vercel** 🌐

#### **Acesse o Vercel Dashboard:**
1. Vá em: https://vercel.com/dashboard
2. Selecione seu projeto: **orbis**
3. Clique em: **Settings** (no menu lateral)
4. Clique em: **Environment Variables**

#### **Adicione estas variáveis:**

**Variável 1:**
```
Name: VITE_API_BASE_URL
Value: https://convolutionary-staminal-caren.ngrok-free.dev
Environments: ✅ Production  ✅ Preview  ✅ Development
```

**Variável 2:**
```
Name: VITE_WS_BASE_URL
Value: wss://convolutionary-staminal-caren.ngrok-free.dev
Environments: ✅ Production  ✅ Preview  ✅ Development
```

**Variável 3:**
```
Name: VITE_APP_NAME
Value: Orbis
Environments: ✅ Production  ✅ Preview  ✅ Development
```

**Variável 4:**
```
Name: VITE_ENABLE_DEBUG
Value: false
Environments: ✅ Production  ✅ Preview  ✅ Development
```

#### **Salvar e Redeploy:**
1. Clique em **Save** em cada variável
2. Vá em: **Deployments**
3. Clique nos **"..."** da última deployment
4. Clique em: **Redeploy**

---

## 🎯 **VERIFICAR SE FUNCIONOU**

### **Local (localhost:5173):**

Depois de reiniciar `npm run dev`, o console **NÃO deve mostrar:**
```diff
- ⚠️ Nenhuma variável VITE_API_* definida
- ⚠️ Nenhuma variável VITE_WS_* definida
```

**Deve mostrar:**
```
🔧 Orbis Config: {
  apiUrl: "https://convolutionary-staminal-caren.ngrok-free.dev",
  wsUrl: "wss://convolutionary-staminal-caren.ngrok-free.dev",
  ...
}
```

---

### **Produção (orbis-omega.vercel.app):**

Após redeploy no Vercel:

1. Abra: https://orbis-omega.vercel.app
2. Abra console (F12)
3. Procure por: `🔧 Orbis Config:`
4. **Deve mostrar as URLs do ngrok!**

---

## 🔄 **SE MUDAR O NGROK**

Quando você reiniciar o ngrok e a URL mudar:

### **1. Atualizar Local:**
```bash
# Editar arquivo:
c:\Users\Jeferson\Documents\orbis\frontend\.env

# Trocar URL antiga pela nova
```

### **2. Atualizar Vercel:**
1. Settings → Environment Variables
2. Editar `VITE_API_BASE_URL` e `VITE_WS_BASE_URL`
3. Salvar
4. Redeploy

---

## 📝 **RESUMO RÁPIDO**

```bash
# 1. LOCAL
cd frontend
copy .env.example .env
npm run dev

# 2. VERCEL
# Acesse: vercel.com/dashboard
# Settings → Environment Variables
# Adicione VITE_API_BASE_URL e VITE_WS_BASE_URL
# Redeploy
```

---

## ✅ **CHECKLIST**

- [ ] ✅ Executei `setup-env.bat` OU copiei `.env.example` → `.env`
- [ ] ✅ Reiniciei servidor local (`npm run dev`)
- [ ] ✅ Warnings sumiram no console local
- [ ] ✅ Adicionei variáveis no Vercel
- [ ] ✅ Fiz redeploy no Vercel
- [ ] ✅ Abri `orbis-omega.vercel.app` e testei
- [ ] ✅ Warnings sumiram no site de produção

---

## 🎉 **RESULTADO ESPERADO**

**Antes:**
```
⚠️ Nenhuma variável VITE_API_* definida
```

**Depois:**
```
🔧 Orbis Config: { apiUrl: "https://convolutionary-staminal-caren..." }
```

**No site de produção:**
- ✅ Sem warnings
- ✅ Conecta no backend ngrok
- ✅ WebSocket funciona
- ✅ Voz clonada carrega
- ✅ Tradução funciona!

---

**PRONTO!** Agora é só executar os passos! 🚀
