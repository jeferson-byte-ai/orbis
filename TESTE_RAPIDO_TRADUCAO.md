# ⚡ Teste Rápido - Tradução em Tempo Real

## 🎯 Teste em 3 Minutos

### 1️⃣ Configure o Usuário 1 (PT → EN)
```bash
# Este usuário fala Português e quer ouvir Inglês
curl -X PUT http://localhost:8000/api/profile/languages \
  -H "Authorization: Bearer SEU_TOKEN_USER1" \
  -H "Content-Type: application/json" \
  -d '{"speaks_languages":["pt"],"understands_languages":["en"]}'
```

### 2️⃣ Configure o Usuário 2 (EN → PT)
```bash
# Este usuário fala Inglês e quer ouvir Português
curl -X PUT http://localhost:8000/api/profile/languages \
  -H "Authorization: Bearer SEU_TOKEN_USER2" \
  -H "Content-Type: application/json" \
  -d '{"speaks_languages":["en"],"understands_languages":["pt"]}'
```

### 3️⃣ Entre na Reunião
- Ambos entram na mesma sala
- Verifique os logs do backend:
```bash
tail -f console.txt | grep -E "🌐|🎤|📢|✅"
```

### 4️⃣ Fale e Teste!
- **User1 fala**: "Olá, tudo bem?"
- **User2 ouve**: "Hello, how are you?" (traduzido em tempo real)
- **User2 fala**: "Hello, how are you?"
- **User1 ouve**: "Olá, como você está?" (traduzido em tempo real)

## ✅ Logs Esperados

```
🌐 Loaded user languages from DB: speaks=pt, wants_to_hear=en
🌐 Loaded user languages from DB: speaks=en, wants_to_hear=pt

🎤 User XXX spoke in pt: 'Olá, tudo bem?'
📢 Processing for listener YYY: pt → en
🌐 Translated to en: 'Hello, how are you?'
✅ User XXX audio processed in 250.5ms | Sent to 1 listener(s)

🎤 User YYY spoke in en: 'Hello, how are you?'
📢 Processing for listener XXX: en → pt
🌐 Translated to pt: 'Olá, como você está?'
✅ User YYY audio processed in 250.5ms | Sent to 1 listener(s)
```

## 🐛 Se Não Funcionar

### Problema: "pt→pt" nos logs
**Causa**: Configurou para falar PT e ouvir PT (mesma língua)
**Solução**: Configure `understands_languages` diferente de `speaks_languages`

### Problema: "No listeners in room"
**Causa**: Você está sozinho na sala
**Solução**: Precisa de pelo menos 2 usuários

### Problema: "Model not loaded"
**Causa**: Modelos ML não carregaram
**Solução**: 
```bash
pip install -r requirements-ml.txt
# Reinicie o servidor
```

### Problema: "No speech detected"
**Causa**: Áudio não está chegando ou muito baixo
**Solução**: 
- Verifique permissão do microfone no navegador
- Fale mais alto ou mais próximo do microfone
- Verifique logs do WebSocket no navegador (F12)

## 📱 Via Interface Web

### Configurar Idiomas:
1. Login no sistema
2. Vá em **Settings** (⚙️)
3. Seção **Language Configuration**
4. Configure:
   - **I speak**: `Português`
   - **I want to hear**: `English`
5. Clique em **Save**

### Entrar na Reunião:
1. Vá em **Home**
2. Clique em **Create Room** ou cole link de sala
3. Permita acesso ao microfone
4. Aguarde outro usuário entrar
5. Comece a falar!

## 🎓 Entenda os Logs

| Emoji | Significado |
|-------|-------------|
| 🌐 | Configuração de idiomas carregada |
| 🎤 | Usuário falou (ASR completou) |
| 📢 | Processando para listener específico |
| 🌐 | Tradução completada |
| ✅ | Áudio enviado com sucesso |
| ⚠️ | Warning (normal se mesma língua) |
| ❌ | Erro (investigar) |

## 🔥 Teste Avançado - 3 Idiomas

### Setup:
```bash
# User A: Português
curl -X PUT http://localhost:8000/api/profile/languages \
  -H "Authorization: Bearer TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"speaks_languages":["pt"],"understands_languages":["pt"]}'

# User B: Inglês
curl -X PUT http://localhost:8000/api/profile/languages \
  -H "Authorization: Bearer TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"speaks_languages":["en"],"understands_languages":["en"]}'

# User C: Espanhol
curl -X PUT http://localhost:8000/api/profile/languages \
  -H "Authorization: Bearer TOKEN_C" \
  -H "Content-Type: application/json" \
  -d '{"speaks_languages":["es"],"understands_languages":["es"]}'
```

### Resultado:
- User A fala PT → User B ouve EN, User C ouve ES
- User B fala EN → User A ouve PT, User C ouve ES
- User C fala ES → User A ouve PT, User B ouve EN

**3 usuários, 3 idiomas, todos se entendendo! 🌍**

## 📊 Performance Checklist

- [ ] Latência < 500ms
- [ ] Áudio traduzido chegando
- [ ] Voz clonada funcionando (se configurada)
- [ ] Sem erros nos logs
- [ ] Cache de traduções ativo (mesma frase = rápido)

## 🎉 Sucesso!

Se você vê estes logs, está funcionando perfeitamente:
```
✅ User XXX audio processed in 250.5ms | Sent to N listener(s)
```

Aproveite a tradução em tempo real! 🚀
