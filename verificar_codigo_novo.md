# 🔍 Como Verificar se o Código Novo Está Rodando

## 🚨 IMPORTANTE: O código com `negotiatingPeers` JÁ está no GitHub!

Último commit: `cc29ecb` às 09:45:34

## ✅ Checklist para Confirmar Deploy

### 1. Verificar Dashboard do Vercel
- Acesse: https://vercel.com/seu-projeto
- Veja se o último deploy (commit `cc29ecb`) está **"Ready"** ✅
- Se ainda estiver em "Building" ou "Deploying", aguarde

### 2. Limpar Cache do Navegador (CRÍTICO!)

**PC:**
```
1. Feche TODAS as abas do site
2. Pressione Ctrl + Shift + Delete
3. Selecione "Cached images and files"
4. Clique em "Clear data"
5. Abra nova aba
6. Pressione Ctrl + Shift + R (hard refresh)
```

**Mobile:**
```
1. Abra em aba ANÔNIMA/PRIVADA
2. Ou: Configurações > Limpar cache do navegador
```

### 3. Verificar Console (F12)

**Código NOVO (deve aparecer):**
```
⏭️ Skipping negotiation with [id] - already in progress
```
OU simplesmente **NÃO deve aparecer**:
```
❌ Negotiation failed with [id]: InvalidAccessError
❌ The order of m-lines in subsequent offer doesn't match
```

**E DEVE aparecer:**
```
📥 Received remote track: video from: [id]
📥 Received remote track: audio from: [id]
```

---

## 🐛 Se o Erro AINDA Aparecer

### Problema: Console.txt de teste ANTIGO
- Você pode ter coletado o console.txt **ANTES** do deploy
- Colete um **NOVO** console.txt **DEPOIS** de:
  1. ✅ Vercel deploy ready
  2. ✅ Cache limpo
  3. ✅ Hard refresh

### Problema: Vercel Cache
- Às vezes o Vercel cacheia o build antigo
- **Solução:** No dashboard do Vercel:
  1. Vá em "Deployments"
  2. Clique no último deployment
  3. Clique em "Redeploy"
  4. Marque "Use existing build cache" = **OFF**
  5. Clique em "Redeploy"

### Problema: Service Worker do navegador
- Service workers podem cachear código antigo
- **Solução PC:**
  1. F12 > Application tab
  2. Service Workers > Unregister
  3. Clear Storage > Clear site data
  4. Reload (Ctrl + Shift + R)

- **Solução Mobile:**
  1. Use aba anônima
  2. Ou desinstale/reinstale PWA se instalado

---

## 📊 Linha do Tempo Esperada

```
09:45 - Commit feito (cc29ecb)
09:46 - Vercel detecta push
09:47 - Vercel inicia build
09:48 - Build completa
09:49 - Deploy concluído ✅
09:50 - Cache CDN atualizado
09:51 - Código novo disponível globalmente
```

**Se você testou ANTES das 09:51**, estava usando código antigo!

---

## 🧪 Teste Final

### Passos:
1. ⏰ **Agora são 09:55** - já passou tempo suficiente
2. 🧹 **Limpe cache** do PC e Mobile
3. 🔄 **Hard refresh** (Ctrl + Shift + R)
4. 🧪 **Teste novamente**:
   - PC cria reunião
   - Mobile entra
5. 📝 **Colete NOVO console.txt** de ambos (PC e Mobile)

### O que deve acontecer:
- ✅ PC vê e ouve Mobile
- ✅ Mobile vê e ouve PC
- ✅ Sem erro de "m-lines order"
- ✅ Aparece "Received remote track"

---

## 💡 Dica: Como Coletar Console do Mobile

### Android Chrome:
1. No PC: chrome://inspect
2. Conecte celular via USB
3. Enable USB debugging no celular
4. Veja console do mobile no PC

### iPhone Safari:
1. Mac: Safari > Develop > [Seu iPhone]
2. Veja console

### Alternativa (qualquer mobile):
Cole isso no console do mobile:
```javascript
(function () { 
  var script = document.createElement('script'); 
  script.src="//cdn.jsdelivr.net/npm/eruda"; 
  document.body.appendChild(script); 
  script.onload = function () { eruda.init(); } 
})();
```

Isso abre um console dentro do próprio mobile!

---

## 🎯 Resumo

**Você precisa:**
1. ✅ Confirmar que Vercel deploy está "Ready"
2. ✅ Limpar cache (PC + Mobile)
3. ✅ Hard refresh
4. ✅ Coletar NOVO console.txt
5. ✅ Verificar se erro sumiu

**Se o erro AINDA aparecer no novo console.txt:**
- Então temos outro problema para investigar
- Mas primeiro, garanta que está testando com código NOVO!
