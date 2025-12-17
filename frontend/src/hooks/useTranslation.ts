/**
 * useTranslation Hook
 * Manages real-time audio translation via WebSocket
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { authenticatedFetch } from '../utils/api';
import { buildBackendWebSocketUrl } from '../utils/websocket';

// Feature flags - Set to true to enable advanced features
const ENABLE_VOICE_CLONING = true;
const ENABLE_TRANSLATION = true;

interface TranslationAudioPayload {
  data: string;
  encoding?: string;
  sample_rate?: number;
}

interface TranslationMessage {
  type: string;
  user_id?: string;
  audio_data?: string;
  audio?: TranslationAudioPayload;
  text?: string;
  timestamp?: number;
  voice_fallback?: boolean;
}

interface ParticipantInfo {
  id: string;
  username: string;
  full_name: string | null;
  name: string;
}

interface SendAudioOptions {
  isPCM16?: boolean;
}

interface UseTranslationReturn {
  isConnected: boolean;
  inputLanguage: string;
  outputLanguage: string;
  speaksLanguages: string[];
  understandsLanguages: string[];
  lastTranslation: string | null;
  lastOriginal: string | null;
  latency: number;
  error: string | null;
  participants: string[];
  participantsInfo: Map<string, ParticipantInfo>;
  connect: (
    roomId: string,
    token: string,
    initialInputLang?: string,
    initialOutputLang?: string,
    initialSpeaks?: string[],
    initialUnderstands?: string[]
  ) => void;
  disconnect: () => void;
  sendAudioChunk: (audioData: ArrayBuffer, options?: SendAudioOptions) => Promise<void>;
  updateLanguages: (input: string, output: string, speaks?: string[], understands?: string[]) => void;
  mute: () => void;
  unmute: () => void;
  websocket: WebSocket | null;
  setWebRTCMessageHandler: (handler: ((data: any) => void) | null) => void;
  voiceFallbackNotice: number | null;
}

export const useTranslation = (): UseTranslationReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [inputLanguage, setInputLanguage] = useState('auto');
  const [outputLanguage, setOutputLanguage] = useState('en');
  const [speaksLanguages, setSpeaksLanguages] = useState<string[]>(['en']);
  const [understandsLanguages, setUnderstandsLanguages] = useState<string[]>(['en']);
  const [lastTranslation, setLastTranslation] = useState<string | null>(null);
  const [lastOriginal, setLastOriginal] = useState<string | null>(null);
  const [latency, setLatency] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);
  const [participantsInfo, setParticipantsInfo] = useState<Map<string, ParticipantInfo>>(new Map());
  const [voiceFallbackNotice, setVoiceFallbackNotice] = useState<number | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  type PendingChunk = { buffer: ArrayBuffer; isPCM16?: boolean };
  const processingQueue = useRef<PendingChunk[]>([]);
  const isProcessing = useRef(false);
  const voiceProfileExists = useRef(false); // New ref to store voice profile status
  const webrtcMessageHandler = useRef<((data: any) => void) | null>(null);
  const pendingWebRTCMessages = useRef<TranslationMessage[]>([]);

  // Initialize audio context and check voice profile status
  useEffect(() => {
    audioContext.current = new AudioContext({ sampleRate: 48000 });

    const checkVoiceProfile = async () => {
      if (!ENABLE_VOICE_CLONING) {
        voiceProfileExists.current = false;
        return;
      }

      try {
        const response = await authenticatedFetch('/api/voices/profile', { method: 'GET' });

        if (response.ok) {
          voiceProfileExists.current = true;
          console.log('✅ Voice profile status: true');
        } else if (response.status === 404) {
          voiceProfileExists.current = false;
          console.log('ℹ️ No voice profile found (this is normal for new users)');
        } else {
          voiceProfileExists.current = true;
          console.warn('⚠️ Unexpected response when checking voice profile:', response.status);
        }
      } catch (err) {
        console.warn('⚠️ Could not check voice profile status:', err);
        voiceProfileExists.current = false;
      }
    };

    void checkVoiceProfile(); // Call immediately

    return () => {
      audioContext.current?.close();
    };
  }, []);

  // Connect to WebSocket
  const connect = useCallback((roomId: string, token: string, initialInputLang: string = 'en', initialOutputLang: string = 'en', initialSpeaks: string[] = [], initialUnderstands: string[] = []) => {
    try {
      // Close existing connection if any
      if (ws.current) {
        console.log('🔄 Closing existing WebSocket connection before creating new one');
        ws.current.close();
        ws.current = null;
      }

      const normIn = (initialInputLang || 'en').split('-')[0].toLowerCase();
      const normOut = (initialOutputLang || 'en').split('-')[0].toLowerCase();
      setInputLanguage(normIn);
      setOutputLanguage(normOut);
      if (initialSpeaks.length > 0) {
        setSpeaksLanguages(initialSpeaks);
      }
      if (initialUnderstands.length > 0) {
        setUnderstandsLanguages(initialUnderstands);
      }

      const wsUrl = buildBackendWebSocketUrl(`/api/ws/audio/${roomId}`, { token });
      const maskedUrl = wsUrl
        .replace(token, 'TOKEN_HIDDEN')
        .replace(encodeURIComponent(token), 'TOKEN_HIDDEN');
      console.log('🔌 Attempting WebSocket connection to:', maskedUrl);
      console.log('🎯 Room ID:', roomId);
      console.log('🔑 Token present:', !!token, 'Length:', token?.length);

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('✅ WebSocket connected successfully for translation');
        setIsConnected(true);
        setError(null);
        audioContext.current?.resume().catch(() => undefined);

        // Send initial language preferences and voice profile status
        ws.current?.send(JSON.stringify({
          type: 'init_settings',
          input_language: normIn,
          output_language: normOut,
          speaks_languages: initialSpeaks,
          understands_languages: initialUnderstands,
          voice_profile_exists: voiceProfileExists.current // Send voice profile status
        }));
      };

      ws.current.onmessage = (event) => {
        try {
          const data: TranslationMessage = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.current.onerror = (event) => {
        console.error('❌ WebSocket error:', event);
        console.error('WebSocket state:', ws.current?.readyState);
        console.error('WebSocket URL was:', wsUrl.replace(token, 'TOKEN_HIDDEN'));
        setError('WebSocket connection error');
      };

      ws.current.onclose = (event) => {
        console.log('🔴 WebSocket disconnected');
        console.log('Close code:', event.code);
        console.log('Close reason:', event.reason || 'No reason provided');
        console.log('Clean close:', event.wasClean);
        setIsConnected(false);
      };

    } catch (err) {
      setError(`Failed to connect: ${err}`);
      console.error('❌ WebSocket connection error:', err);
    }
  }, []);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    processingQueue.current = [];
    isProcessing.current = false;

    setIsConnected(false);
  }, []);

  // Set WebRTC message handler
  const setWebRTCMessageHandler = useCallback((handler: ((data: any) => void) | null) => {
    webrtcMessageHandler.current = handler;

    if (handler && pendingWebRTCMessages.current.length > 0) {
      pendingWebRTCMessages.current.forEach(message => {
        handler(message);
      });
      pendingWebRTCMessages.current = [];
    }
  }, []);

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (data: TranslationMessage) => {
    const startTime = data.timestamp || Date.now();
    const currentLatency = Date.now() - startTime;

    // Check if this is a WebRTC signaling message
    const webrtcMessageTypes = ['connected', 'webrtc_offer', 'webrtc_answer', 'ice_candidate', 'participant_joined', 'participant_left'];
    if (webrtcMessageTypes.includes(data.type)) {
      if (webrtcMessageHandler.current) {
        webrtcMessageHandler.current(data);
      } else {
        pendingWebRTCMessages.current.push(data);
      }

      if (data.type !== 'participant_joined' && data.type !== 'participant_left') {
        return;
      }
    }

    switch (data.type) {
      case 'connected':
        console.log('Translation service connected');
        break;

      case 'partial_transcript': {
        // Show immediate partial captions for the speaker
        setLastOriginal(data.text || '');
        setLatency(currentLatency);
        break;
      }

      case 'partial_translation': {
        // Show immediate translated partials to the listener
        setLastTranslation(data.text || '');
        setLatency(currentLatency);
        break;
      }

      case 'translated_audio': {
        // Received translated audio from another participant
        if (data.text) {
          // Prefer to show both translated text and the original for clarity
          const detectedLang = (data as any).detected_language ? String((data as any).detected_language).toUpperCase() : undefined;
          const original = (data as any).original_text as string | undefined;
          const show = original && detectedLang
            ? `${data.text}  |  [${detectedLang}] ${original}`
            : data.text;
          setLastTranslation(show);
          setLatency(currentLatency);
        }

        if (data.voice_fallback) {
          setVoiceFallbackNotice(Date.now());
        }

        const audioPayload: TranslationAudioPayload | undefined = data.audio || (data.audio_data ? {
          data: data.audio_data,
          encoding: 'pcm_s16le',
          sample_rate: 22050
        } : undefined);
        if (audioPayload?.data) {
          // Play translated audio (with sequence for jitter buffer ordering)
          const seq: number | undefined = (data as any).seq;
          void playAudio(audioPayload.data, audioPayload.sample_rate ?? 22050, audioPayload.encoding ?? 'pcm_s16le', seq);
        }
        break;
      }

      case 'participant_joined':
        console.log('👋 Participant joined:', data.user_id, (data as any).user_name);
        // @ts-expect-error - backend includes participants array for join events
        if (data.participants) {
          // @ts-expect-error - participants payload is injected dynamically by backend
          const participantsList = data.participants as ParticipantInfo[];
          setParticipants(participantsList.map(p => p.id));
          
          // Update participants info map
          const newParticipantsInfo = new Map<string, ParticipantInfo>();
          participantsList.forEach(p => {
            newParticipantsInfo.set(p.id, p);
          });
          setParticipantsInfo(newParticipantsInfo);
        }
        break;

      case 'participant_left':
        console.log('👋 Participant left:', data.user_id);
        // @ts-expect-error - backend includes participants array for leave events
        if (data.participants) {
          // @ts-expect-error - participants payload is injected dynamically by backend
          const participantsList = data.participants as ParticipantInfo[];
          setParticipants(participantsList.map(p => p.id));
          
          // Update participants info map
          const newParticipantsInfo = new Map<string, ParticipantInfo>();
          participantsList.forEach(p => {
            newParticipantsInfo.set(p.id, p);
          });
          setParticipantsInfo(newParticipantsInfo);
        }
        break;

      case 'error':
        console.error('Translation error:', data);
        setError(data.text || 'Unknown error');
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  };

  // Send audio chunk to server
  const processNextChunk = useCallback(async () => {
    if (isProcessing.current) return;
    const chunk = processingQueue.current.shift();
    if (!chunk || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
      return;
    }

    isProcessing.current = true;
    try {
      let pcm16: Int16Array | null = null;

      if (chunk.isPCM16) {
        pcm16 = new Int16Array(chunk.buffer.slice(0));
      } else {
        if (audioContext.current) {
          pcm16 = await convertToPCM16(chunk.buffer, audioContext.current as AudioContext, 16000);
        }

        if (!pcm16) {
          pcm16 = convertFloat32BufferToPCM16(chunk.buffer);
          if (!pcm16 && !convertFloat32BufferToPCM16.hasLoggedWarning) {
            console.warn('⚠️ Unable to decode audio chunk, dropping it. Ensure the client sends PCM16 data.');
            convertFloat32BufferToPCM16.hasLoggedWarning = true;
          }
        }
      }

      if (!pcm16 || pcm16.length === 0) {
        return;
      }

      const payload = int16ToBase64(pcm16);
      ws.current.send(JSON.stringify({
        type: 'audio_chunk',
        audio_data: payload,
        timestamp: Date.now()
      }));
    } catch (err) {
      console.error('Failed to process audio chunk', err);
    } finally {
      isProcessing.current = false;
      if (processingQueue.current.length > 0) {
        void processNextChunk();
      }
    }
  }, []);

  const sendAudioChunk = useCallback(async (audioData: ArrayBuffer, options?: SendAudioOptions) => {
    // Skip audio processing if translation is disabled
    if (!ENABLE_TRANSLATION) {
      return;
    }

    processingQueue.current.push({ buffer: audioData, isPCM16: options?.isPCM16 });
    await processNextChunk();
  }, [processNextChunk]);

  // Update language preferences
  const updateLanguages = useCallback((input: string, output: string, speaks?: string[], understands?: string[]) => {
    console.log('🌐 Updating languages:', { from: inputLanguage, to: input }, { from: outputLanguage, to: output });
    setInputLanguage(input);
    setOutputLanguage(output);
    if (speaks) {
      setSpeaksLanguages(speaks);
    }
    if (understands) {
      setUnderstandsLanguages(understands);
    }

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'language_update',
        input_language: input,
        output_language: output,
        speaks_languages: speaks,
        understands_languages: understands
      }));
      console.log('✅ Language update sent to server');
    } else {
      console.warn('⚠️ WebSocket not connected, languages updated locally only');
    }
  }, [inputLanguage, outputLanguage]);

  // Mute translation
  const mute = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'control',
        action: 'mute'
      }));
    }
  }, []);

  // Unmute translation
  const unmute = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'control',
        action: 'unmute'
      }));
    }
  }, []);

  // Play translated audio
  // Jitter buffer + simple crossfade for smoother streaming
  const playAudio = async (audioData: string, sampleRate: number, encoding: string, seq?: number) => {
    try {
      if (!audioContext.current) return;

      if (encoding !== 'pcm_s16le') {
        console.warn('Unsupported audio encoding:', encoding);
        return;
      }

      const buffer = base64ToArrayBuffer(audioData);
      if (!buffer) return;

      const pcm16 = new Int16Array(buffer);
      const floatData = int16ToFloat32(pcm16);

      const audioBuffer = audioContext.current.createBuffer(1, floatData.length, sampleRate);
      audioBuffer.copyToChannel(floatData, 0, 0);

      // Simple jitter queue per stream (single stream case)
      const now = audioContext.current.currentTime;
      const startAt = Math.max(now + 0.05, now); // 50ms buffer

      const source = audioContext.current.createBufferSource();
      source.buffer = audioBuffer;

      // Apply short fade-in/out (10ms) to avoid clicks between blocks
      const gainNode = audioContext.current.createGain();
      const fade = 0.01; // 10ms
      gainNode.gain.setValueAtTime(0.0, startAt);
      gainNode.gain.linearRampToValueAtTime(1.0, startAt + fade);
      gainNode.gain.setValueAtTime(1.0, startAt + (audioBuffer.duration - fade));
      gainNode.gain.linearRampToValueAtTime(0.0, startAt + audioBuffer.duration);

      source.connect(gainNode).connect(audioContext.current.destination);
      source.start(startAt);

    } catch (err) {
      console.error('Failed to play audio:', err);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    inputLanguage,
    outputLanguage,
    lastTranslation,
    lastOriginal,
    latency,
    error,
    participants,
    participantsInfo,
    connect,
    disconnect,
    sendAudioChunk,
    updateLanguages,
    speaksLanguages,
    understandsLanguages,
    mute,
    unmute,
    websocket: ws.current,
    setWebRTCMessageHandler,
    voiceFallbackNotice
  };
};

function base64ToArrayBuffer(base64: string): ArrayBuffer | null {
  try {
    const binary = atob(base64);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  } catch (err) {
    console.error('Failed to decode base64 audio', err);
    return null;
  }
}

async function convertToPCM16(buffer: ArrayBuffer, audioContext: AudioContext, targetSampleRate: number): Promise<Int16Array | null> {
  try {
    // Verify buffer has data
    if (!buffer || buffer.byteLength === 0) {
      return null;
    }

    const audioBuffer = await audioContext.decodeAudioData(buffer.slice(0));
    const channelCount = audioBuffer.numberOfChannels;
    const length = audioBuffer.length;

    const mono = new Float32Array(length);
    for (let channel = 0; channel < channelCount; channel++) {
      const channelData = audioBuffer.getChannelData(channel);
      for (let i = 0; i < length; i++) {
        mono[i] += channelData[i] / channelCount;
      }
    }

    let resampled: Float32Array;
    if (audioBuffer.sampleRate === targetSampleRate) {
      resampled = mono;
    } else {
      const offlineContext = new OfflineAudioContext(1, Math.ceil(audioBuffer.duration * targetSampleRate), targetSampleRate);
      const resampleBuffer = offlineContext.createBuffer(1, mono.length, audioBuffer.sampleRate);
      // Directly copy the Float32Array data
      resampleBuffer.copyToChannel(mono, 0, 0);
      const source = offlineContext.createBufferSource();
      source.buffer = resampleBuffer;
      source.connect(offlineContext.destination);
      source.start(0);
      const rendered = await offlineContext.startRendering();
      resampled = rendered.getChannelData(0);
    }

    const pcm16 = new Int16Array(resampled.length);
    for (let i = 0; i < resampled.length; i++) {
      let sample = resampled[i];
      sample = Math.max(-1, Math.min(1, sample));
      pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }

    return pcm16;
  } catch (err) {
    // Only log errors once to avoid console spam
    if (ENABLE_TRANSLATION && !convertToPCM16.hasLoggedError) {
      console.error('⚠️ Failed to convert audio chunk to PCM16:', err);
      console.log('ℹ️ This may be normal if audio format is not yet supported. Audio translation may not work.');
      convertToPCM16.hasLoggedError = true;
    }
    return null;
  }
}

// Add error tracking to function
(convertToPCM16 as any).hasLoggedError = false;

function int16ToBase64(data: Int16Array): string {
  let binary = '';
  // Iterate through the Int16Array, converting each 16-bit integer to two 8-bit bytes
  for (let i = 0; i < data.length; i++) {
    // Get the 16-bit integer
    const value = data[i];
    // Append the two bytes (little-endian)
    binary += String.fromCharCode(value & 0xFF);
    binary += String.fromCharCode((value >> 8) & 0xFF);
  }
  return btoa(binary);
}

function int16ToFloat32(data: Int16Array): Float32Array {
  const float32 = new Float32Array(data.length);
  for (let i = 0; i < data.length; i++) {
    float32[i] = data[i] / 0x7fff;
  }
  return float32;
}

function convertFloat32BufferToPCM16(buffer: ArrayBuffer): Int16Array | null {
  try {
    if (!buffer || buffer.byteLength % 4 !== 0) {
      return null;
    }

    const float32 = new Float32Array(buffer.slice(0));
    const pcm16 = new Int16Array(float32.length);

    for (let i = 0; i < float32.length; i++) {
      let sample = float32[i];
      sample = Math.max(-1, Math.min(1, sample));
      pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }

    return pcm16;
  } catch (error) {
    console.warn('Failed to fallback-convert Float32 buffer to PCM16:', error);
    return null;
  }
}

convertFloat32BufferToPCM16.hasLoggedWarning = false as boolean;
