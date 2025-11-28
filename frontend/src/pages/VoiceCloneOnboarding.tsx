/**
 * VoiceCloneOnboarding Component - Premium Design
 * Guides user through voice cloning setup with file upload
 */
import React, { useState, useRef } from 'react';
import { Check, Loader, Sparkles, Volume2, Wand2, Upload, FileAudio, AlertCircle, X, User } from 'lucide-react';
import { authenticatedFetch } from '../utils/api';

interface VoiceCloneOnboardingProps {
  onComplete: () => void;
  onSkip: () => void;
  userPreferences?: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    notifications: boolean;
    analytics: boolean;
  };
}

const VoiceCloneOnboarding: React.FC<VoiceCloneOnboardingProps> = ({
  onComplete,
  onSkip
}) => {
  const [step, setStep] = useState<'intro' | 'upload' | 'processing' | 'complete'>('intro');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string>('');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  
  const uploadIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check authentication on mount
  React.useEffect(() => {
    const token = localStorage.getItem('auth_token');
    setIsAuthenticated(!!token);
  }, []);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('audio/')) {
      setUploadError('Please select a valid audio file');
      return;
    }

    // Validate file size (max 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      setUploadError('File too large. Maximum size: 50MB');
      return;
    }

    // Validate duration (we'll do this after processing, but set file first)
    setUploadedFile(file);
    setUploadError('');
  };

  const handleUploadFile = async () => {
    if (!uploadedFile) return;

    const audioBlob = new Blob([uploadedFile], { type: uploadedFile.type });
    await uploadVoiceProfile(audioBlob, uploadedFile.name);
  };

  const uploadVoiceProfile = async (audioBlob: Blob, filename: string = 'voice_profile.webm') => {
    setStep('processing');
    setProcessingProgress(0);

    const formData = new FormData();
    formData.append('file', audioBlob, filename);

    // Get auth token
    const token = localStorage.getItem('auth_token');

    if (!token) {
      alert('You need to be logged in to upload voice. Please login again.');
      setStep('upload');
      return;
    }

    try {
      // Simulate progress for upload
      let progress = 0;
      uploadIntervalRef.current = setInterval(() => {
        progress = Math.min(progress + 5, 90);
        setProcessingProgress(progress);
      }, 200);

      const response = await authenticatedFetch('/api/voices/upload-profile-voice', {
        method: 'POST',
        body: formData
      });

      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
      }

      if (response.status === 401) {
        alert('Session expired. Please login again.');
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
        return;
      }

      if (response.ok) {
        const data = await response.json();
        console.log('Voice profile uploaded successfully:', data);
        setProcessingProgress(100);
        setStep('complete');
      } else {
        const errorData = await response.json();
        console.error('Failed to upload voice profile:', errorData);
        alert(`Failed to upload voice profile: ${errorData.detail || response.statusText}`);
        setStep('upload');
      }
    } catch (error) {
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
      }
      console.error('Network error during voice profile upload:', error);
      alert('Network error. Please check your connection and try again.');
      setStep('upload');
    }
  };

  const handleComplete = () => {
    onComplete();
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center px-6 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-20 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float" />
        <div className="absolute bottom-20 right-20 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float" style={{ animationDelay: '2s' }} />
      </div>
      
      <div className="max-w-3xl w-full glass-dark rounded-3xl p-10 shadow-2xl border border-white/20 relative z-10 animate-scale-in">
        {!isAuthenticated ? (
          <LoginRequiredStep onSkip={onSkip} />
        ) : (
          <>
            {step === 'intro' && (
              <IntroStep
                onStart={() => setStep('upload')}
                onSkip={onSkip}
              />
            )}
        
        {/* Steps choice e tts removidos - apenas clonagem de voz */}
        
        {step === 'upload' && (
          <UploadStep
            uploadedFile={uploadedFile}
            uploadError={uploadError}
            fileInputRef={fileInputRef}
            onFileSelect={handleFileSelect}
            onUpload={handleUploadFile}
            onBack={() => setStep('intro')}
            onSkip={onSkip}
          />
        )}
        
        {step === 'processing' && (
          <ProcessingStep progress={processingProgress} />
        )}
        
        {step === 'complete' && (
          <CompleteStep onContinue={handleComplete} />
        )}
          </>
        )}
      </div>
    </div>
  );
};

// Login Required Step
const LoginRequiredStep: React.FC<{ onSkip: () => void }> = ({ onSkip }) => (
  <div className="text-center">
    <div className="relative inline-block mb-6">
      <div className="bg-gradient-to-br from-yellow-600 to-orange-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-float">
        <AlertCircle size={48} className="text-white" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-yellow-600 to-orange-600 rounded-3xl blur-2xl opacity-50" />
    </div>
    
    <h2 className="text-4xl font-black text-white mb-3">
      Login Required
    </h2>
    <p className="text-gray-300 text-lg mb-10 leading-relaxed">
      To configure your voice and save your preferences, you need to be logged into your Orbis account.
    </p>
    
    <div className="glass rounded-2xl p-6 mb-10">
      <div className="flex items-start gap-3 text-left mb-4">
        <span className="text-blue-400 text-2xl">🔐</span>
        <div>
          <h3 className="text-white font-bold mb-1">Why do I need to login?</h3>
          <p className="text-gray-400 text-sm">
            Your voice settings are saved to your profile so you can use them on any device.
          </p>
        </div>
      </div>
      <div className="flex items-start gap-3 text-left">
        <span className="text-green-400 text-2xl">✨</span>
        <div>
          <h3 className="text-white font-bold mb-1">Benefits of having an account</h3>
          <ul className="text-gray-400 text-sm space-y-1">
            <li>• Access your voices from anywhere</li>
            <li>• Meeting history and transcriptions</li>
            <li>• Synchronized settings</li>
          </ul>
        </div>
      </div>
    </div>
    
    <div className="flex gap-4">
      <button
        onClick={onSkip}
        className="flex-1 glass hover:bg-white/10 text-white py-4 rounded-xl font-bold transition-all hover:scale-105 active:scale-95"
      >
        Use Without Login
      </button>
      <a
        href="/login"
        className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-4 rounded-xl font-bold transition-all shadow-xl hover:shadow-2xl hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
      >
        <User size={20} />
        Login
      </a>
    </div>
  </div>
);

// Intro Step
const IntroStep: React.FC<{ onStart: () => void; onSkip: () => void }> = ({ onStart, onSkip }) => (
  <div className="text-center">
    <div className="relative inline-block mb-6">
      <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-float">
        <Wand2 size={48} className="text-white" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl blur-2xl opacity-50" />
    </div>
    
    <h2 className="text-4xl font-black text-white mb-3">
      Clone Your Voice
    </h2>
    <div className="flex items-center justify-center gap-2 mb-6">
      <Sparkles size={18} className="text-yellow-400" />
      <p className="text-blue-400 font-semibold">AI Voice Synthesis</p>
      <Sparkles size={18} className="text-yellow-400" />
    </div>
    
    <p className="text-gray-300 text-lg mb-10 leading-relaxed">
      To provide natural-sounding translations, we'll create a voice profile from your audio file. 
      This takes just a few <span className="text-white font-bold">seconds</span>.
    </p>
    
    <div className="glass rounded-2xl p-8 mb-10">
      <h3 className="text-white font-bold text-xl mb-5 flex items-center gap-2">
        <Volume2 size={24} className="text-blue-400" />
        What you need:
      </h3>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="glass p-4 rounded-xl">
          <span className="text-2xl mb-2 block">🎵</span>
          <p className="text-white font-semibold">Audio file</p>
        </div>
        <div className="glass p-4 rounded-xl">
          <span className="text-2xl mb-2 block">⏱️</span>
          <p className="text-white font-semibold">At least 6 seconds</p>
        </div>
        <div className="glass p-4 rounded-xl">
          <span className="text-2xl mb-2 block">🔇</span>
          <p className="text-white font-semibold">Quiet environment</p>
        </div>
        <div className="glass p-4 rounded-xl">
          <span className="text-2xl mb-2 block">✨</span>
          <p className="text-white font-semibold">High quality</p>
        </div>
      </div>
    </div>
    
    <div className="flex gap-4">
      <button
        onClick={onSkip}
        className="flex-1 glass hover:bg-white/10 text-white py-4 rounded-xl font-bold transition-all hover:scale-105 active:scale-95"
      >
        Skip for Now
      </button>
      <button
        onClick={onStart}
        className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-4 rounded-xl font-bold transition-all shadow-xl hover:shadow-2xl hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
      >
        <Sparkles size={20} />
        Let's Start
      </button>
    </div>
  </div>
);

// Processing Step
const ProcessingStep: React.FC<{ progress: number }> = ({ progress }) => (
  <div className="text-center">
    <div className="relative inline-block mb-8">
      <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl">
        <Loader size={48} className="text-white animate-spin" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl blur-2xl opacity-50 animate-pulse" />
    </div>
    
    <h2 className="text-4xl font-black text-white mb-4">
      Creating Your Voice Profile
    </h2>
    
    <p className="text-gray-300 text-lg mb-10">
      Please wait while we process your voice recordings with <span className="text-blue-400 font-bold">AI magic</span>...
    </p>
    
    <div className="glass rounded-full h-4 mb-4 overflow-hidden">
      <div
        className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 h-4 rounded-full transition-all shadow-lg relative"
        style={{ width: `${progress}%` }}
      >
        <div className="absolute inset-0 bg-white/30 shimmer" />
      </div>
    </div>
    
    <p className="text-white text-2xl font-bold">{progress}%</p>
  </div>
);

// Upload Step
interface UploadStepProps {
  uploadedFile: File | null;
  uploadError: string;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onFileSelect: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onUpload: () => void;
  onBack: () => void;
  onSkip: () => void;
}

const UploadStep: React.FC<UploadStepProps> = ({
  uploadedFile,
  uploadError,
  fileInputRef,
  onFileSelect,
  onUpload,
  onBack,
  onSkip
}) => {
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="text-center">
      <div className="relative inline-block mb-6">
        <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-float">
          <FileAudio size={48} className="text-white" />
        </div>
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl blur-2xl opacity-50" />
      </div>
      
      <h2 className="text-4xl font-black text-white mb-3">
        Upload Audio File
      </h2>
      <p className="text-gray-300 text-lg mb-8">
        Select an audio file with your voice
      </p>

      {/* Upload Area */}
      <div className="mb-8">
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={onFileSelect}
          className="hidden"
        />
        
        {!uploadedFile ? (
          <div
            onClick={() => fileInputRef.current?.click()}
            className="glass hover:bg-white/10 border-2 border-dashed border-white/30 hover:border-blue-500/50 rounded-2xl p-12 cursor-pointer transition-all hover:scale-105 active:scale-95"
          >
            <Upload size={64} className="text-blue-400 mx-auto mb-4" />
            <p className="text-white font-bold text-xl mb-2">
              Click to select file
            </p>
            <p className="text-gray-400 text-sm mb-4">
              or drag and drop here
            </p>
            <div className="text-gray-500 text-xs">
              Formats: MP3, WAV, OGG, M4A, FLAC, WebM<br />
              Maximum size: 50MB
            </div>
          </div>
        ) : (
          <div className="glass rounded-2xl p-6 border-2 border-green-500/50">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-green-500/20 rounded-lg p-3">
                  <FileAudio size={32} className="text-green-400" />
                </div>
                <div className="text-left">
                  <p className="text-white font-bold">{uploadedFile.name}</p>
                  <p className="text-gray-400 text-sm">
                    {formatFileSize(uploadedFile.size)} • {uploadedFile.type}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  if (fileInputRef.current) {
                    fileInputRef.current.value = '';
                  }
                  onFileSelect({ target: { files: null } } as any);
                }}
                className="text-red-400 hover:text-red-300 transition-colors"
              >
                <X size={24} />
              </button>
            </div>
            <button
              onClick={onUpload}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-3 rounded-xl font-bold transition-all shadow-xl hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
            >
              <Upload size={20} />
              Upload and Process
            </button>
          </div>
        )}

        {uploadError && (
          <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded-xl flex items-center gap-3 text-red-300">
            <AlertCircle size={20} />
            <span>{uploadError}</span>
          </div>
        )}
      </div>

      {/* Requirements */}
      <div className="glass rounded-xl p-6 mb-6">
        <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <Volume2 size={20} className="text-blue-400" />
          File Requirements:
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm text-left">
          <div className="flex items-start gap-2">
            <span className="text-green-400 mt-0.5">✓</span>
            <span className="text-gray-300">Duration: at least 6 seconds</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-green-400 mt-0.5">✓</span>
            <span className="text-gray-300">Quality: High</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-green-400 mt-0.5">✓</span>
            <span className="text-gray-300">Environment: Quiet</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-green-400 mt-0.5">✓</span>
            <span className="text-gray-300">Only your voice</span>
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 glass hover:bg-white/10 text-white py-3 rounded-xl font-semibold transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={onSkip}
          className="flex-1 text-gray-400 hover:text-white py-3 transition-colors"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
};

// ChoiceStep e TTSSelectionStep REMOVIDOS
// Orbis agora usa apenas clonagem de voz

/* REMOVIDO - ChoiceStep
const ChoiceStep_OLD: React.FC<ChoiceStepProps> = ({ onChooseCloned, onChooseTTS, onBack }) => (
  <div className="text-center">
    <div className="relative inline-block mb-6">
      <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-float">
        <Wand2 size={48} className="text-white" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl blur-2xl opacity-50" />
    </div>
    
    <h2 className="text-4xl font-black text-white mb-3">
      Escolha seu Tipo de Voz
    </h2>
    <p className="text-gray-300 text-lg mb-10">
      Como você quer que sua voz seja representada nas traduções?
    </p>
    
    <div className="grid md:grid-cols-2 gap-6 mb-8">
      
      <button
        onClick={onChooseCloned}
        className="group glass hover:bg-white/10 p-8 rounded-2xl transition-all hover:scale-105 active:scale-95 border-2 border-white/10 hover:border-purple-500/50"
      >
        <div className="bg-gradient-to-br from-purple-600 to-pink-600 rounded-2xl w-20 h-20 flex items-center justify-center mx-auto mb-4 shadow-xl group-hover:scale-110 transition-transform">
          <Wand2 size={40} className="text-white" />
        </div>
        <h3 className="text-white font-bold text-xl mb-2">Voz Clonada</h3>
        <p className="text-gray-400 text-sm mb-4">
          Clone sua voz real para traduções ultra-realistas
        </p>
        <div className="flex flex-col gap-2 text-sm text-left">
          <div className="flex items-center gap-2 text-green-400">
            <span>✓</span>
            <span>Sua voz única</span>
          </div>
          <div className="flex items-center gap-2 text-green-400">
            <span>✓</span>
            <span>100% personalizado</span>
          </div>
          <div className="flex items-center gap-2 text-green-400">
            <span>✓</span>
            <span>Ultra-realista</span>
          </div>
        </div>
      </button>

      
      <button
        onClick={onChooseTTS}
        className="group glass hover:bg-white/10 p-8 rounded-2xl transition-all hover:scale-105 active:scale-95 border-2 border-white/10 hover:border-blue-500/50 relative"
      >
        <div className="absolute top-4 right-4 bg-green-500 text-white text-xs px-3 py-1 rounded-full font-bold">
          GRÁTIS
        </div>
        <div className="bg-gradient-to-br from-blue-600 to-cyan-600 rounded-2xl w-20 h-20 flex items-center justify-center mx-auto mb-4 shadow-xl group-hover:scale-110 transition-transform">
          <Volume2 size={40} className="text-white" />
        </div>
        <h3 className="text-white font-bold text-xl mb-2">Voz TTS</h3>
        <p className="text-gray-400 text-sm mb-4">
          Use vozes naturais masculinas ou femininas
        </p>
        <div className="flex flex-col gap-2 text-sm text-left">
          <div className="flex items-center gap-2 text-green-400">
            <span>✓</span>
            <span>Instantâneo</span>
          </div>
          <div className="flex items-center gap-2 text-green-400">
            <span>✓</span>
            <span>Vozes naturais</span>
          </div>
          <div className="flex items-center gap-2 text-green-400">
            <span>✓</span>
            <span>100% gratuito</span>
          </div>
        </div>
      </button>
    </div>

    <div className="glass rounded-xl p-4 mb-6">
      <p className="text-gray-400 text-sm">
        💡 <span className="text-white font-semibold">Tip:</span> You can change this setting later in settings.
      </p>
    </div>
    
    <button
      onClick={onBack}
      className="text-gray-400 hover:text-white transition-colors text-sm underline"
    >
      ← Voltar
    </button>
  </div>
);

/* REMOVIDO - TTSSelectionStep
const TTSSelectionStep_OLD: React.FC<TTSSelectionStepProps> = ({ 
  selectedTTS, 
  onSelectTTS, 
  onContinue, 
  onBack 
}) => (
  <div className="text-center">
    <div className="relative inline-block mb-6">
      <div className="bg-gradient-to-br from-blue-600 to-cyan-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-float">
        <Volume2 size={48} className="text-white" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-3xl blur-2xl opacity-50" />
    </div>
    
    <h2 className="text-4xl font-black text-white mb-3">
      Escolha uma Voz TTS
    </h2>
    <p className="text-gray-300 text-lg mb-10">
      Selecione entre voz masculina ou feminina
    </p>
    
    <div className="grid md:grid-cols-2 gap-6 mb-8">
      
      <button
        onClick={() => onSelectTTS('male')}
        className={`group glass p-8 rounded-2xl transition-all hover:scale-105 active:scale-95 border-2 ${
          selectedTTS === 'male' 
            ? 'border-blue-500 bg-blue-500/10' 
            : 'border-white/10 hover:border-blue-500/50'
        }`}
      >
        <div className={`bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl w-20 h-20 flex items-center justify-center mx-auto mb-4 shadow-xl transition-transform ${
          selectedTTS === 'male' ? 'scale-110' : 'group-hover:scale-110'
        }`}>
          <User size={40} className="text-white" />
        </div>
        <h3 className="text-white font-bold text-xl mb-2">Voz Masculina</h3>
        <p className="text-gray-400 text-sm mb-4">
          Voz natural e profissional masculina
        </p>
        {selectedTTS === 'male' && (
          <div className="flex items-center justify-center gap-2 text-blue-400 font-semibold">
            <Check size={20} />
            <span>Selecionado</span>
          </div>
        )}
      </button>

      
      <button
        onClick={() => onSelectTTS('female')}
        className={`group glass p-8 rounded-2xl transition-all hover:scale-105 active:scale-95 border-2 ${
          selectedTTS === 'female' 
            ? 'border-pink-500 bg-pink-500/10' 
            : 'border-white/10 hover:border-pink-500/50'
        }`}
      >
        <div className={`bg-gradient-to-br from-pink-600 to-purple-600 rounded-2xl w-20 h-20 flex items-center justify-center mx-auto mb-4 shadow-xl transition-transform ${
          selectedTTS === 'female' ? 'scale-110' : 'group-hover:scale-110'
        }`}>
          <Users size={40} className="text-white" />
        </div>
        <h3 className="text-white font-bold text-xl mb-2">Voz Feminina</h3>
        <p className="text-gray-400 text-sm mb-4">
          Voz natural e profissional feminina
        </p>
        {selectedTTS === 'female' && (
          <div className="flex items-center justify-center gap-2 text-pink-400 font-semibold">
            <Check size={20} />
            <span>Selecionado</span>
          </div>
        )}
      </button>
    </div>

    <div className="glass rounded-xl p-4 mb-8">
      <p className="text-gray-400 text-sm">
        🎵 <span className="text-white font-semibold">Preview:</span> TTS voices are optimized for clarity and naturalness in multiple languages.
      </p>
    </div>
    
    <div className="flex gap-3">
      <button
        onClick={onBack}
        className="flex-1 glass hover:bg-white/10 text-white py-3 rounded-xl font-semibold transition-colors"
      >
        ← Voltar
      </button>
      <button
        onClick={onContinue}
        disabled={!selectedTTS}
        className={`flex-1 py-3 rounded-xl font-bold transition-all ${
          selectedTTS
            ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-xl hover:scale-105 active:scale-95'
            : 'bg-gray-600 text-gray-400 cursor-not-allowed'
        }`}
      >
        Continuar
      </button>
    </div>
  </div>
);
*/
// FIM DOS COMPONENTES REMOVIDOS (ChoiceStep e TTSSelectionStep)

// Complete Step
const CompleteStep: React.FC<{ onContinue: () => void }> = ({ onContinue }) => (
  <div className="text-center">
    <div className="relative inline-block mb-8">
      <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-scale-in">
        <Check size={56} className="text-white" strokeWidth={3} />
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-green-500 to-emerald-600 rounded-3xl blur-2xl opacity-50" />
    </div>
    
    <h2 className="text-4xl font-black text-white mb-4">
      Voice Profile Created!
    </h2>
    
    <div className="flex items-center justify-center gap-2 mb-8">
      <Sparkles size={20} className="text-yellow-400 animate-pulse" />
      <p className="text-green-400 font-bold text-xl">Successfully cloned your voice</p>
      <Sparkles size={20} className="text-yellow-400 animate-pulse" />
    </div>
    
    <p className="text-gray-300 text-lg mb-10 leading-relaxed">
      Your voice has been successfully cloned. You can now participate in meetings with natural-sounding translations 
      in <span className="text-white font-bold">20+ languages</span>.
    </p>
    
    <button
      onClick={onContinue}
      className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-12 py-4 rounded-xl font-bold text-lg transition-all shadow-2xl hover:scale-110 active:scale-95"
    >
      Continue to Meeting 🚀
    </button>
  </div>
);

export default VoiceCloneOnboarding;
