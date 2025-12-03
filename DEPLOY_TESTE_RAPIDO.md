# 🚀 Deploy Rápido para Teste (com ngrok)

## 📋 Sua Configuração Atual

Você está usando:
- ✅ **Vercel** para hospedar o frontend
- ✅ **GitHub** para versionamento
- ✅ **ngrok** para expor o backend localmente
- ✅ **Produção** (não dev server)

## ⚡ Deploy Rápido

### Opção 1: Script Automático (RECOMENDADO)
```powershell
./deploy_test.ps1
```

### Opção 2: Manual
```bash
# 1. Build
cd frontend
npm run build
cd ..

# 2. Commit e Push
git add .
git commit -m "fix: WebRTC connection handler update"
git push

# 3. Aguarde Vercel fazer deploy (1-2 min)
```

## ⏱️ Tempo Total
- Build: ~30 segundos
- Push: ~5 segundos
- Deploy Vercel: ~1-2 minutos
- **Total: ~2-3 minutos por teste**

## 🔍 Como Verificar se Deploy Está Pronto

1. **No Vercel Dashboard:**
   - Acesse https://vercel.com/seu-projeto
   - Veja se o último deploy está "Ready" ✅

2. **No navegador:**
   - Pressione `Ctrl + Shift + R` para hard refresh
   - Ou abra aba anônima
   - Abra o console (F12)
   - Procure por: `🔄 Updating WebRTC message handler`

## 🐛 Se o Código Antigo Ainda Aparecer

1. **Cache do navegador:**
   - PC: `Ctrl + Shift + Delete` → Limpar cache → Fechar TODAS as abas
   - Mobile: Configurações → Limpar cache → Aba anônima

2. **Cache do Vercel:**
   - No dashboard do Vercel, força um novo deploy
   - Ou adicione um comentário vazio no código e faça push

3. **Cache do ngrok:**
   - Reinicie o ngrok
   - Use uma nova URL do ngrok

## 🎯 Deploy Atual (Iteração 9)

### Correções Incluídas:
1. ✅ useEffect de cleanup com deps vazias
2. ✅ endCall estabilizado
3. ✅ Sistema de participantes pendentes
4. ✅ **useEffect para re-registrar handler quando localStream muda** ⭐

### Logs Esperados (Código Novo):
```
🔄 Updating WebRTC message handler with latest localStream state
👋 Participant joined, creating offer for: [id] Has localStream: true
📊 Peer connection has 2 senders after creation
📤 Sent WebRTC offer to: [id]
📥 Received remote track: video from: [id]
📥 Received remote track: audio from: [id]
```

### ❌ Logs do Código Antigo (NÃO deve aparecer):
```
❌ Has localStream: false
❌ ⏳ LocalStream not ready yet
❌ (sem mensagem de "Updating WebRTC message handler")
```

## 🔄 Workflow de Teste

```
Fazer mudança no código
    ↓
Executar: ./deploy_test.ps1
    ↓
Aguardar Vercel deploy (1-2 min)
    ↓
Limpar cache do navegador (Ctrl+Shift+R)
    ↓
Testar novamente
    ↓
Coletar console.txt se não funcionar
```

## 💡 Dica: Deploy Mais Rápido

Para testes mais rápidos durante desenvolvimento, você pode:

1. **Usar servidor local (sem ngrok):**
   ```bash
   # Terminal 1
   python start.py
   
   # Terminal 2
   cd frontend
   npm run dev
   
   # Acesse: http://localhost:5173
   ```
   - Mudanças aparecem instantaneamente (Hot Module Replacement)
   - Sem necessidade de build/deploy

2. **Teste local primeiro, depois deploy para produção**

3. **Use ngrok apenas para teste final mobile**

## 🚨 IMPORTANTE

Cada vez que você fizer uma mudança:
1. ✅ Faça o build (`npm run build`)
2. ✅ Commit e push para GitHub
3. ✅ Aguarde Vercel fazer deploy
4. ✅ Limpe cache do navegador
5. ✅ Só ENTÃO teste

**Não adianta fazer mudança no código e testar sem fazer deploy!**

---

## 📊 Checklist de Deploy

- [ ] Código modificado
- [ ] Build executado (`npm run build`)
- [ ] Sem erros no build
- [ ] Commit feito
- [ ] Push para GitHub
- [ ] Deploy do Vercel concluído (check dashboard)
- [ ] Cache do navegador limpo (PC)
- [ ] Cache do navegador limpo (Mobile)
- [ ] Hard refresh feito (Ctrl+Shift+R)
- [ ] Console aberto para verificar logs
- [ ] Verificado que aparece "Updating WebRTC message handler"
- [ ] Testado

---

**Pronto para fazer deploy? Execute:**
```powershell
./deploy_test.ps1
```
