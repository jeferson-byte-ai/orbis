# 🚨 IMPORTANTE: Como Testar Corretamente

## ✅ Build Novo Gerado com Sucesso!

O código foi corrigido e o build foi feito. Mas você precisa **forçar o navegador a usar o novo código**.

## 🔄 Passos para Testar:

### 1️⃣ Limpar Cache do Navegador

**No PC (Chrome/Edge):**
1. Pressione `Ctrl + Shift + Delete`
2. Selecione "Cached images and files" 
3. Clique em "Clear data"

**OU simplesmente:**
- Pressione `Ctrl + Shift + R` (Hard Refresh)
- Ou `Ctrl + F5`

**No Mobile:**
1. Vá em Configurações do navegador
2. Limpar cache e dados de navegação
3. Ou abra em aba anônima

### 2️⃣ Reinicie os Servidores

**Terminal 1 - Backend:**
```bash
# Pare o servidor (Ctrl+C) e reinicie
python start.py
```

**Terminal 2 - Frontend:**
```bash
# Pare o servidor (Ctrl+C) e reinicie
cd frontend
npm run dev
```

### 3️⃣ Teste Novamente

1. **PC**: Abra o navegador, pressione `Ctrl + Shift + R` para forçar reload
2. **Mobile**: Abra em aba anônima ou limpe o cache
3. Crie uma reunião no PC
4. Entre no mobile (ou vice-versa)

### 4️⃣ Verifique o Console (IMPORTANTE!)

**Abra o DevTools (F12) e procure por:**

✅ **Deve aparecer (código NOVO):**
```
🚀 Starting WebRTC call in room: [room-id]
📹 Requesting user media (camera + microphone)...
✅ User media obtained successfully
📹 Local stream ready with tracks: audio, video
```

❌ **NÃO deve aparecer (código ANTIGO):**
```
🧹 useWebRTC unmounting, cleaning up...
🛑 Ending WebRTC call
```

Se você ainda vir "useWebRTC unmounting" no console = **código antigo ainda carregado**!

## 🎯 Teste Específico: PC vs Mobile

Já que você mencionou que o problema é entre PC e Mobile, vamos investigar:

### Informações que preciso:

1. **Qual dispositivo criou a reunião?** PC ou Mobile?
2. **Qual dispositivo entrou depois?** PC ou Mobile?
3. **Status WebRTC em cada um:**
   - PC: "Ready" ✅
   - Mobile: "Offline" ❌
4. **Navegador usado:**
   - PC: Chrome? Edge? Firefox?
   - Mobile: Chrome? Safari? Samsung Internet?
5. **Rede:**
   - Mesma rede Wi-Fi ou redes diferentes?
   - Mobile está em 4G/5G?

## 🔍 Debug Mobile Específico

Para ver o console no Mobile:

### Android Chrome:
1. No PC, abra Chrome e vá em `chrome://inspect`
2. Conecte o celular via USB
3. Habilite "USB Debugging" no celular
4. Você verá o console do mobile no PC!

### iPhone Safari:
1. No Mac, abra Safari > Develop > [Seu iPhone]
2. Selecione a aba da reunião
3. Verá o console

### Alternativa (mais fácil):
Use o **Eruda** (console mobile):
```javascript
// Cole isso no console do mobile:
(function () { var script = document.createElement('script'); script.src="//cdn.jsdelivr.net/npm/eruda"; document.body.appendChild(script); script.onload = function () { eruda.init(); } })();
```

Isso abrirá um console no próprio mobile!

## 📊 Checklist Antes de Coletar Novo Log:

- [ ] Build novo gerado (✅ já feito)
- [ ] Cache do navegador limpo (PC)
- [ ] Cache do navegador limpo (Mobile)
- [ ] Hard refresh feito (Ctrl+Shift+R)
- [ ] Servidores reiniciados
- [ ] Console aberto (F12)
- [ ] Verificou que NÃO aparece "useWebRTC unmounting"

## 🐛 Se Ainda Não Funcionar

Cole o **NOVO console.txt** com:
1. Log do PC (DevTools > Console > Copiar tudo)
2. Log do Mobile (usando método acima)
3. Informe qual dispositivo é qual

---

**Teste agora e me avisa se ainda aparece "useWebRTC unmounting" no console!**

Se não aparecer mais, mas ainda não conectar, é outro problema (provavelmente ICE/STUN/TURN).
