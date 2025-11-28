/**
 * Voice Setup Modal - Inline voice cloning during meeting creation
 * Shows when user tries to create meeting without voice configured
 */
import React, { useState, useRef } from 'react';
import { Upload, FileAudio, X, AlertCircle, Loader, Check, Sparkles, Volume2 } from 'lucide-react';
import { authenticatedFetch } from '../utils/api';

interface VoiceSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

const VoiceSetupModal: React.FC<VoiceSetupModalProps> = ({ isOpen, onClose, onComplete }) => {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadComplete, setUploadComplete] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

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

    setUploadedFile(file);
    setUploadError('');
  };

  const handleUpload = async () => {
    if (!uploadedFile) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadError('');

    const formData = new FormData();
    formData.append('file', uploadedFile, uploadedFile.name);

    const token = localStorage.getItem('auth_token');

    if (!token) {
      setUploadError('You need to be logged in. Please login again.');
      setUploading(false);
      return;
    }

    try {
      // Simulate progress
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress = Math.min(progress + 5, 90);
        setUploadProgress(progress);
      }, 200);

      const response = await authenticatedFetch('/api/voices/upload-profile-voice', {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);

      if (response.status === 401) {
        setUploadError('Session expired. Please login again.');
        localStorage.removeItem('auth_token');
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
        return;
      }

      if (response.ok) {
        setUploadProgress(100);
        setUploadComplete(true);
        setTimeout(() => {
          onComplete();
        }, 1500);
      } else {
        const errorData = await response.json();
        setUploadError(errorData.detail || 'Failed to upload voice profile');
      }
    } catch (error: any) {
      console.error('Network error during voice profile upload:', error);
      setUploadError('Network error. Please check your connection and try again.');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-6 z-50 animate-fade-in">
      <div className="glass-dark rounded-3xl max-w-2xl w-full p-8 shadow-2xl border border-white/20 animate-scale-in relative">
        {/* Close button */}
        {!uploading && !uploadComplete && (
          <button
            onClick={onClose}
            className="absolute top-6 right-6 text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        )}

        {uploadComplete ? (
          // Success state
          <div className="text-center py-8">
            <div className="relative inline-block mb-6">
              <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-scale-in">
                <Check size={56} className="text-white" strokeWidth={3} />
              </div>
              <div className="absolute inset-0 bg-gradient-to-br from-green-500 to-emerald-600 rounded-3xl blur-2xl opacity-50" />
            </div>
            
            <h2 className="text-4xl font-black text-white mb-4">
              Voice Configured!
            </h2>
            
            <div className="flex items-center justify-center gap-2 mb-6">
              <Sparkles size={20} className="text-yellow-400 animate-pulse" />
              <p className="text-green-400 font-bold text-xl">Voice profile created successfully</p>
              <Sparkles size={20} className="text-yellow-400 animate-pulse" />
            </div>
            
            <p className="text-gray-300 text-lg">
              Creating your meeting...
            </p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="text-center mb-8">
              <div className="relative inline-block mb-4">
                <div className="bg-gradient-to-br from-red-500 to-red-700 rounded-3xl w-20 h-20 flex items-center justify-center shadow-2xl animate-float">
                  <FileAudio size={40} className="text-white" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-red-500 to-red-700 rounded-3xl blur-2xl opacity-50" />
              </div>
              
              <h2 className="text-3xl font-black text-white mb-2">
                Configure Your Voice
              </h2>
              <p className="text-gray-300 text-lg">
                For more natural translations, upload an audio with your voice
              </p>
            </div>

            {uploading ? (
              // Uploading state
              <div className="text-center py-8">
                <div className="relative inline-block mb-6">
                  <div className="bg-gradient-to-br from-red-600 to-red-800 rounded-3xl w-20 h-20 flex items-center justify-center shadow-2xl">
                    <Loader size={40} className="text-white animate-spin" />
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-br from-red-600 to-red-800 rounded-3xl blur-2xl opacity-50 animate-pulse" />
                </div>
                
                <h3 className="text-2xl font-bold text-white mb-4">
                  Processing Your Voice Profile
                </h3>
                
                <p className="text-gray-300 mb-8">
                  Please wait while we process your audio with <span className="text-red-400 font-bold">AI</span>...
                </p>
                
                <div className="glass rounded-full h-4 mb-4 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-red-500 via-red-600 to-red-700 h-4 rounded-full transition-all shadow-lg relative"
                    style={{ width: `${uploadProgress}%` }}
                  >
                    <div className="absolute inset-0 bg-white/30 shimmer" />
                  </div>
                </div>
                
                <p className="text-white text-2xl font-bold">{uploadProgress}%</p>
              </div>
            ) : (
              <>
                {/* Upload Area */}
                <div className="mb-6">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  
                  {!uploadedFile ? (
                    <div
                      onClick={() => fileInputRef.current?.click()}
                      className="glass hover:bg-white/10 border-2 border-dashed border-white/30 hover:border-red-500/50 rounded-2xl p-12 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                      <Upload size={64} className="text-red-400 mx-auto mb-4" />
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
                            setUploadedFile(null);
                            setUploadError('');
                          }}
                          className="text-red-400 hover:text-red-300 transition-colors"
                        >
                          <X size={24} />
                        </button>
                      </div>
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
                    <Volume2 size={20} className="text-red-400" />
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

                {/* Action buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={onClose}
                    className="flex-1 glass hover:bg-white/10 text-white py-4 rounded-xl font-bold transition-all hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Skip for Now
                  </button>
                  <button
                    onClick={handleUpload}
                    disabled={!uploadedFile}
                    className={`flex-1 py-4 rounded-xl font-bold transition-all flex items-center justify-center gap-2 ${
                      uploadedFile
                        ? 'bg-gradient-to-r from-red-500 to-red-700 hover:from-red-600 hover:to-red-800 text-white shadow-xl hover:scale-[1.02] active:scale-[0.98]'
                        : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    <Upload size={20} />
                    Upload and Continue
                  </button>
                </div>

                {/* Info note */}
                <div className="mt-6 text-center">
                  <p className="text-gray-400 text-sm">
                    💡 <span className="text-white font-semibold">Tip:</span> You can configure your voice later in Settings
                  </p>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default VoiceSetupModal;
