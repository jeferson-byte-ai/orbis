# 🔍 GUIA DE DIAGNÓSTICO - VOZ CLONADA

## 🎯 **PROBLEMA ATUAL**
"Tradução e voz clonada não estão funcionando"

---

## ✅ **CORREÇÕES APLICADAS**

### **1. Endpoint /api/voices/preload CORRIGIDO**
📁 `backend/api/voices.py` - Linha 199

**O que foi corrigido:**
- ❌ **ANTES:** Apenas carregava TTS, mas **NÃO criava o arquivo JSON** do perfil de voz
- ✅ **AGORA:** Chama `coqui_service.clone_voice()` para criar o JSON com metadata

**Arquivos criados:**
- `data/voices/{user_id}.wav` ← Áudio original (já existia)
- `data/voices/{user_id}.json` ← **NOVO!** Metadata do Coqui (speaker_wav reference)

---

## 🧪 **COMO TESTAR AGORA**

### **PASSO 1: Verificar arquivos no servidor**

```bash
# No diretório do projeto
cd c:\Users\Jeferson\Documents\orbis

# Listar arquivos de vozes
dir data\voices
```

**Esperado:**
```
📁 data/voices/
  ├─ {user_id}.wav   ← Áudio original
  └─ {user_id}.json  ← Metadata Coqui (DEVE EXISTIR!)
```

---

### **PASSO 2: Testar endpoint de preload**

```bash
# Abrir outro terminal
curl -X POST http://localhost:8000/api/voices/preload \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Content-Type: application/json"
```

**Resposta esperada:**
```json
{
  "success": true,
  "message": "Voice preloaded successfully",
  "voice_profile_id": "uuid-aqui",
  "voice_name": "Seu Nome (Cloned)",
  "language": "en",
  "ready": true,
  "file_size": 123456,
  "tts_loaded": true,
  "voice_wav": "data/voices/{user_id}.wav",
  "voice_json": "data/voices/{user_id}.json",
  "json_exists": true  ← DEVE SER TRUE!
}
```

---

### **PASSO 3: Verificar LOGS do backend**

Procure no terminal do backend por:

```
✅ Mensagens esperadas:
🎤 Preloading voice for user {user_id}
📁 Voice WAV: data/voices/{user_id}.wav
📁 Voice JSON: data/voices/{user_id}.json
🔄 Loading Coqui TTS model...
✅ Coqui TTS model loaded
🎨 Creating Coqui voice profile...
✅ Voice cloned successfully: data/voices/{user_id}.json
📊 Voice WAV file: X bytes
📊 Voice profile metadata: Coqui XTTS v2 voice profile...
✅ Speaker WAV verified: data/voices/{user_id}.wav
✅ Voice preloaded and cached for user {user_id}

❌ Erros possíveis:
⚠️ Speaker WAV not found
❌ Failed to clone voice
❌ TTS model not loaded
```

---

### **PASSO 4: Verificar conteúdo do JSON**

```bash
# Ver conteúdo do JSON criado
type data\voices\{user_id}.json
```

**Deve conter:**
```json
{
  "created_at": 1234567890.123,
  "sample_count": 1,
  "samples": [
    "C:\\Users\\...\\data\\voices\\{user_id}.wav"
  ],
  "model": "tts_models/multilingual/multi-dataset/xtts_v2",
  "device": "cuda",
  "speaker_wav": "C:\\Users\\...\\data\\voices\\{user_id}.wav",
  "notes": "Coqui XTTS v2 voice profile - works with short audio samples (5+ seconds)"
}
```

**IMPORTANTE:** O campo `speaker_wav` DEVE apontar para o arquivo WAV!

---

## 🔧 **SE NÃO FUNCIONAR**

### **Diagnóstico 1: Arquivo JSON não foi criado**

```bash
# Verificar se JSON existe
dir data\voices\*.json
```

Se **NÃO existir:**
- Backend teve erro ao clonar voz
- Verifique logs do backend
- TTS Coqui pode não estar instalado: `pip install TTS`

---

### **Diagnóstico 2: JSON existe mas tradução não funciona**

**Verifique no código:**
📁 `backend/services/audio_pipeline/stream_processor.py` - Linha 515

```python
def _get_speaker_reference(self, user_id: UUID) -> Optional[str]:
    # Deve buscar o JSON e ler o campo "speaker_wav"
    ...
```

**Logs esperados durante reunião:**
```
🎤 User {id} spoke in en: 'Hello'
🌐 Translated to pt: 'Olá'
✅ Using cloned voice for user {id}: data/voices/{id}.wav
```

---

### **Diagnóstico 3: Coqui TTS não está carregando**

```python
# Ver se TTS foi carregado
# No terminal do backend, procure por:
✅ Coqui TTS model loaded successfully
```

Se **NÃO aparecer:**
```bash
# Instalar TTS
pip install TTS

# Verificar instalação
python -c "from TTS.api import TTS; print('OK')"
```

---

## 📋 **CHECKLIST DE VERIFICAÇÃO**

Antes de entrar na reunião, confirme:

- [ ] ✅ Arquivo WAV existe: `data/voices/{user_id}.wav`
- [ ] ✅ Arquivo JSON existe: `data/voices/{user_id}.json`
- [ ] ✅ JSON tem campo `speaker_wav` apontando para WAV
- [ ] ✅ Endpoint `/api/voices/preload` retorna `"ready": true`
- [ ] ✅ Backend mostra: "✅ Coqui TTS model loaded"
- [ ] ✅ Backend mostra: "✅ Voice cloned successfully"
- [ ] ✅ Settings salvos: "I speak" e "Want to hear"

---

## 🎬 **TESTE COMPLETO EM REUNIÃO**

### **Setup:**
1. **User A:** Faz upload de voz em inglês
2. **User A:** Settings → I speak: English, Want to hear: Portuguese
3. **User A:** Create Meeting → Ver loading "Setting Up Voice"
4. **User B:** Faz upload de voz em português
5. **User B:** Settings → I speak: Portuguese, Want to hear: English  
6. **User B:** Join Meeting → Ver loading "Setting Up Voice"

### **Teste:**
```
User A fala: "Hello, how are you?"
  ↓
Logs do backend (PROCURE POR):
  🎤 User A spoke in en: 'Hello, how are you?'
  🌐 Translated to pt: 'Olá, como você está?'
  ✅ Using cloned voice for user A: data/voices/A.wav
  ✅ Synthesized speech: 'Olá, como você está?' in pt
  ↓
User B DEVE OUVIR: 
  "Olá, como você está?" 
  COM A VOZ DE USER A! ✅
```

---

## 🚨 **ERROS COMUNS**

### **Erro 1: "Voice profile not found"**
```
❌ Solução: Fazer upload de voz novamente no Settings
```

### **Erro 2: "Failed to clone voice"**
```
❌ Possíveis causas:
- TTS não instalado: pip install TTS
- Áudio muito curto (mínimo 5 segundos)
- Arquivo WAV corrompido
```

### **Erro 3: "TTS model not loaded"**
```
❌ Solução:
pip install TTS
# Ou verificar CUDA se estiver usando GPU
```

### **Erro 4: "No listeners in room"**
```
✅ Normal se você está sozinho na sala
   Convide alguém para testar!
```

---

## 📊 **LOGS PARA COMPARTILHAR**

Se continuar com problema, compartilhe:

```bash
# 1. Ver arquivos de voz
dir data\voices

# 2. Ver conteúdo do JSON
type data\voices\{seu_user_id}.json

# 3. Logs do backend (últimas 50 linhas)
# Copie do terminal onde está rodando:
# python start.py
```

---

## ✅ **CONFIRMAÇÃO DE SUCESSO**

Você saberá que está funcionando quando:

1. ✅ Tela de loading "Setting Up Voice" aparece
2. ✅ Backend mostra: "✅ Voice cloned successfully"
3. ✅ Arquivo JSON existe em `data/voices/`
4. ✅ Na reunião, backend mostra: "✅ Using cloned voice for user X"
5. ✅ Você ouve o outro participante com a voz **dele** no **seu idioma**

**ISSO É A VERDADEIRA DUBLAGEM!** 🎬🎤

---

**Última atualização:** 2025-12-05 12:35  
**Status:** Backend corrigido, pronto para testar!
