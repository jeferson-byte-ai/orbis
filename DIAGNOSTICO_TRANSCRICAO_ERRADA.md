# 🚨 DIAGNÓSTICO: Transcrição Completamente Errada

## 🔴 Problema Reportado

**Você disse:**
> "Eu falei cerca de 30 segundos e não transcreveu NADA que eu falei, ou transcreveu outra coisa completamente diferente"

## 🔍 Possíveis Causas (em ordem de probabilidade)

### 1. **🎤 Problema de Captura de Áudio do Microfone**

**Sintomas:**
- Whisper recebe áudio, mas o áudio está corrompido/vazio
- Transcrição aleatória ou vazia
- Funciona em alguns ambientes mas não em outros

**Causas Comuns:**
- ❌ Microfone errado selecionado no navegador
- ❌ Volume do microfone muito baixo
- ❌ Microfone com ruído excessivo
- ❌ Permissões de microfone bloqueadas
- ❌ Driver de áudio com problema

**Como Verificar:**
```
1. Abra o Console do navegador (F12)
2. Procure por: "[AudioDebug] chunk"
3. Você deve ver logs como:
   [AudioDebug] chunk 50 downsampledSamples=3333 pcmBytes=6666
   
4. Se não aparecer NENHUM log de audio, o microfone NÃO está capturando
```

**Solução:**
```powershell
# No Windows, verifique:
1. Settings → System → Sound → Input
2. Fale no microfone e veja se a barra se mexe
3. Ajuste o volume para 80-100%
4. Teste: gravador de voz do Windows
```

---

### 2. **🌐 Problema de Idioma / Detecção de Idioma**

**Sintomas:**
- Whisper transcreve, mas em idioma errado
- Palavras aleatórias que não fazem sentido
- Mistura de idiomas

**Causa:**
- Você configurou "I speak: Portuguese" mas Whisper está detectando outro idioma
- Audio muito curto para detectar idioma corretamente
- VAD cortando início/fim da fala

**Logs Esperados (Correto):**
```
🎤 User xxx spoke in pt: 'Olá, como vai?'
```

**Logs Problema (Errado):**
```
🎤 User xxx spoke in en: 'All como vai?'  ← Detectou inglês!
🎤 User xxx spoke in es: 'Hola como vai?'  ← Detectou espanhol!
```

**Solução Temporária:**
Forçar o idioma no código (testar se resolve):

```python
# Em ml/asr/whisper_service.py, linha 142
segments, info = self.model.transcribe(
    audio,
    language="pt",  # ✅ FORÇAR português (era: language=language)
    ...
)
```

---

### 3. **⚙️ Modelo Whisper Errado ou Corrompido**

**Sintomas:**
- Transcrição sempre errada, independente do que falar
- Palavras sem sentido
- Sempre o mesmo tipo de erro

**Causa:**
- Modelo Whisper "base" pode ser ruim para português
- Modelo não baixou corretamente
- Cache corrompido

**Solução:**
```python
# Em backend/main.py ou config
whisper_service.model_size = "medium"  # Usar modelo maior
```

**Limpar cache:**
```powershell
Remove-Item -Recurse -Force ./data/models/whisper/*
# Reiniciar servidor para re-baixar
```

---

### 4. **🔊 Problema de Sample Rate / Formato de Áudio**

**Sintomas:**
- Áudio soa "acelerado" ou "lento" para Whisper
- Transcrição parece correta mas de outro idioma
- Palavras distorcidas

**Causa:**
- Frontend envia 16kHz mas backend espera outra coisa
- Conversão PCM16 com bug

**Verificação:**
No código, temos:
- Frontend: downsamples para 16kHz ✅
- Backend: espera 16kHz ✅
- Whisper: requer 16kHz ✅

**Mas..** se o AudioContext do navegador está em 44.1kHz ou 48kHz e o downsample tem bug, o áudio fica distorcido.

**Teste:**
```javascript
// No console do navegador (F12):
const context = new AudioContext();
console.log('Sample rate:', context.sampleRate);
// Deve mostrar: 48000 ou 44100
```

---

### 5. **🎛️ VAD Muito Agressivo (Corta a Fala)**

**Sintomas:**
- Só transcreve palavras soltas
- Frases cortadas no meio
- Transcrição incompleta

**Causa:**
- VAD corta início/fim da fala
- Chunks muito pequenos

**Já Corrigimos:**
- ✅ Aumentamos intervalo para 500ms
- ✅ Reduzimos threshold VAD (0.6 → 0.4)
- ✅ Filtramos chunks < 300ms

**Se ainda persistir, desabilitar VAD completamente:**

```python
# Em stream_processor.py, linha 160
transcribed_text, detected_lang, _ = await whisper_service.transcribe(
    audio_array,
    language=input_lang if input_lang != 'auto' else None,
    sample_rate=self.input_sample_rate,
    vad_filter=False  # ✅ DESABILITAR VAD para testar
)
```

---

## 🧪 TESTE DEFINITIVO

Vamos criar um teste para identificar exatamente o problema:

### **Teste 1: Verificar se Whisper funciona isoladamente**

```python
# tmp_rovodev_test_whisper_real.py
import numpy as np
import asyncio
from ml.asr.whisper_service import whisper_service

# Carregar modelo
whisper_service.load()

# Criar áudio de teste (tom puro 440Hz, 1 segundo)
sample_rate = 16000
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)

# Transcrever
result = asyncio.run(whisper_service.transcribe(audio, language="pt", sample_rate=16000))
print(f"Resultado: '{result[0]}'")
print(f"Idioma detectado: {result[1]}")

# Deve retornar vazio ou ruído (pois é só um tom)
# Se retornar texto real, Whisper está alucinando!
```

### **Teste 2: Verificar áudio do navegador**

```javascript
// No console do navegador (F12), cole isso:
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (e) => {
      const data = e.inputBuffer.getChannelData(0);
      const max = Math.max(...data);
      const min = Math.min(...data);
      console.log(`Audio level: ${min.toFixed(3)} to ${max.toFixed(3)}`);
    };
    
    source.connect(processor);
    processor.connect(context.destination);
    
    console.log('✅ Monitoring audio... speak now!');
    console.log('Sample rate:', context.sampleRate);
  })
  .catch(err => console.error('❌ Microphone error:', err));

// FALE NO MICROFONE
// Você deve ver logs como:
// Audio level: -0.523 to 0.612  ← ISSO É BOM (áudio detectado)
//
// Se ver:
// Audio level: -0.001 to 0.001  ← RUIM (sem áudio)
```

---

## 💡 SOLUÇÃO RÁPIDA PARA TESTAR AGORA

Vou criar uma versão que **DESABILITA TODAS as otimizações** e usa configuração mais permissiva:

### **Fix Temporário - Teste de Diagnóstico**

```python
# Em ml/asr/whisper_service.py, linha 142
segments, info = self.model.transcribe(
    audio,
    language="pt",  # ✅ FORÇAR português
    vad_filter=False,  # ✅ DESABILITAR VAD
    beam_size=5,  # ✅ Aumentar qualidade (era 1)
    best_of=5,  # ✅ Aumentar qualidade (era 1)
    temperature=0.0,
    compression_ratio_threshold=2.4,
    log_prob_threshold=-1.0,
    no_speech_threshold=0.8,  # ✅ Mais estrito (era 0.4)
    condition_on_previous_text=True,  # ✅ Ativar contexto
)
```

**E em stream_processor.py, linha 94:**

```python
await asyncio.sleep(1.0)  # ✅ Processar a cada 1 SEGUNDO (era 0.5)
```

**E em stream_processor.py, linha 111:**

```python
if len(combined_chunk) < 32000:  # ✅ Mínimo 1 SEGUNDO (era 0.3s)
    logger.debug(f"⏭️ Skipping short audio chunk: {len(combined_chunk)} bytes")
    continue
```

Isso força:
- ✅ Idioma português fixo
- ✅ VAD desabilitado
- ✅ Chunks de 1 segundo completo
- ✅ Maior qualidade de transcrição

---

## 📊 O que você deve ver nos logs:

**ANTES (Bugado):**
```
⏭️ Skipping short audio chunk: 4800 bytes
⏭️ Skipping short audio chunk: 3200 bytes
⏭️ Skipping empty/noise transcription
⏭️ Skipping empty/noise transcription
🎤 User xxx spoke in en: 'random gibberish'  ← ERRADO!
```

**DEPOIS (Correto):**
```
🎤 User xxx spoke in pt: 'Olá, tudo bem com você?'  ← CORRETO!
🌐 Translated to en: 'Hello, how are you?'
✅ Using cloned voice for user xxx
✅ User xxx audio processed in 450ms
```

---

## 🎯 Próximos Passos

1. **Reinicie o servidor** com as mudanças
2. **Abra o Console do navegador** (F12)
3. **Entre na sala e fale por 5-10 segundos**
4. **Observe os logs do backend**
5. **Me envie:**
   - Logs do console do navegador
   - Logs do terminal do backend
   - O que você falou vs o que foi transcrito

Isso vai me dar informação exata para corrigir!

---

## 🔧 Se Nada Funcionar

Última alternativa: usar outro motor ASR (Google Speech-to-Text, Azure, etc) temporariamente para verificar se é problema do Whisper ou do pipeline de áudio.

Ou usar Whisper via API externa:
```python
# Teste com OpenAI Whisper API
import openai
openai.api_key = "YOUR_KEY"
result = openai.Audio.transcribe("whisper-1", audio_file)
```

Se funcionar com API externa, o problema é:
- ❌ Whisper local mal configurado
- ❌ Modelo corrompido
- ❌ Driver de áudio do Windows

Se NÃO funcionar nem com API externa, o problema é:
- ❌ Captura de áudio do navegador
- ❌ Microfone físico
- ❌ Formato de áudio enviado

**Me avise os resultados e vamos resolver juntos!** 🚀
