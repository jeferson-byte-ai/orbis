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
}

interface UseTranslationReturn {
  isConnected: boolean;
  inputLanguage: string;
  outputLanguage: string;
  lastTranslation: string | null;
  latency: number;
  error: string | null;
  participants: string[];
  connect: (roomId: string, token: string) => void;
  disconnect: () => void;
  sendAudioChunk: (audioData: ArrayBuffer) => Promise<void>;
  updateLanguages: (input: string, output: string) => void;
  mute: () => void;
  unmute: () => void;
}

export const useTranslation = (): UseTranslationReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [inputLanguage, setInputLanguage] = useState('auto');
  const [outputLanguage, setOutputLanguage] = useState('en');
  const [lastTranslation, setLastTranslation] = useState<string | null>(null);
  const [latency, setLatency] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);

  const ws = useRef<WebSocket | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const processingQueue = useRef<ArrayBuffer[]>([]);
  const isProcessing = useRef(false);
  const voiceProfileExists = useRef(false); // New ref to store voice profile status

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
  const connect = useCallback((roomId: string, token: string, initialInputLang: string = 'auto', initialOutputLang: string = 'en') => {
    try {
      // Close existing connection if any
      if (ws.current) {
        console.log('🔄 Closing existing WebSocket connection before creating new one');
        ws.current.close();
        ws.current = null;
      }

      setInputLanguage(initialInputLang);
      setOutputLanguage(initialOutputLang);

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
          input_language: initialInputLang,
          output_language: initialOutputLang,
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

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (data: TranslationMessage) => {
    const startTime = data.timestamp || Date.now();
    const currentLatency = Date.now() - startTime;

    switch (data.type) {
      case 'connected':
        console.log('Translation service connected');
        break;

      case 'translated_audio': {
        // Received translated audio from another participant
        if (data.text) {
          setLastTranslation(data.text);
          setLatency(currentLatency);
        }

        const audioPayload: TranslationAudioPayload | undefined = data.audio || (data.audio_data ? {
          data: data.audio_data,
          encoding: 'pcm_s16le',
          sample_rate: 22050
        } : undefined);
        if (audioPayload?.data) {
          // Play translated audio
          void playAudio(audioPayload.data, audioPayload.sample_rate ?? 22050, audioPayload.encoding ?? 'pcm_s16le');
        }
        break;
      }

      case 'participant_joined':
        console.log('👋 Participant joined:', data.user_id);
        // @ts-ignore - data.participants exists in backend response
        if (data.participants) {
          // @ts-ignore
          setParticipants(data.participants);
        }
        break;

      case 'participant_left':
        console.log('👋 Participant left:', data.user_id);
        // @ts-ignore
        if (data.participants) {
          // @ts-ignore
          setParticipants(data.participants);
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
    if (!chunk || !audioContext.current || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
      return;
    }

    isProcessing.current = true;
    try {
      const pcm16 = await convertToPCM16(chunk, audioContext.current, 16000);
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

  const sendAudioChunk = useCallback(async (audioData: ArrayBuffer) => {
    // Skip audio processing if translation is disabled
    if (!ENABLE_TRANSLATION) {
      return;
    }

    processingQueue.current.push(audioData);
    await processNextChunk();
  }, [processNextChunk]);

  // Update language preferences
  const updateLanguages = useCallback((input: string, output: string) => {
    console.log('🌐 Updating languages:', { from: inputLanguage, to: input }, { from: outputLanguage, to: output });
    setInputLanguage(input);
    setOutputLanguage(output);

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'language_update',
        input_language: input,
        output_language: output
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
  const playAudio = async (audioData: string, sampleRate: number, encoding: string) => {
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

      const source = audioContext.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.current.destination);
      source.start();

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
    latency,
    error,
    participants,
    connect,
    disconnect,
    sendAudioChunk,
    updateLanguages,
    mute,
    unmute
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
  // Create a DataView to read bytes from the Int16Array's buffer
  const dataView = new DataView(data.buffer);
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
