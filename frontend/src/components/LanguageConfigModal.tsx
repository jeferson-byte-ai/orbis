/**
 * Language Configuration Modal
 * Allows users to configure languages they speak and understand during meetings
 */
import React, { useState, useEffect } from 'react';
import { X, Check, Globe, Mic, Ear, Search, Loader } from 'lucide-react';
import { apiFetch } from '../utils/api';

interface Language {
  code: string;
  name: string;
  native_name: string;
  flag: string;
}

interface LanguageConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSpeaksLanguages: string[];
  currentUnderstandsLanguages: string[];
  onSave: (speaks: string[], understands: string[]) => Promise<void>;
}

const LanguageConfigModal: React.FC<LanguageConfigModalProps> = ({
  isOpen,
  onClose,
  currentSpeaksLanguages,
  currentUnderstandsLanguages,
  onSave
}) => {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [speaksLanguages, setSpeaksLanguages] = useState<string[]>(currentSpeaksLanguages);
  const [understandsLanguages, setUnderstandsLanguages] = useState<string[]>(currentUnderstandsLanguages);

  useEffect(() => {
    if (isOpen) {
      loadLanguages();
      setSpeaksLanguages(currentSpeaksLanguages);
      setUnderstandsLanguages(currentUnderstandsLanguages);
    }
  }, [isOpen, currentSpeaksLanguages, currentUnderstandsLanguages]);

  const loadLanguages = async () => {
    setLoading(true);
    try {
      // Endpoint público - não precisa de autenticação
      const response = await apiFetch('/api/profile/languages/supported');

      if (!response.ok) {
        throw new Error(`Failed to load languages: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Languages loaded:', data.total, 'languages');
      
      if (data.languages && data.languages.length > 0) {
        setLanguages(data.languages);
      } else {
        console.error('❌ No languages returned from API');
      }
    } catch (error) {
      console.error('❌ Error loading languages:', error);
      // Fallback com idiomas básicos
      setLanguages([
        { code: 'en', name: 'English', native_name: 'English', flag: '🇬🇧' },
        { code: 'pt', name: 'Portuguese', native_name: 'Português', flag: '🇧🇷' },
        { code: 'es', name: 'Spanish', native_name: 'Español', flag: '🇪🇸' },
        { code: 'fr', name: 'French', native_name: 'Français', flag: '🇫🇷' },
        { code: 'de', name: 'German', native_name: 'Deutsch', flag: '🇩🇪' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSpeaks = (code: string) => {
    setSpeaksLanguages(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  const toggleUnderstands = (code: string) => {
    setUnderstandsLanguages(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  const handleSave = async () => {
    if (speaksLanguages.length === 0) {
      alert('Please select at least one language you speak');
      return;
    }
    if (understandsLanguages.length === 0) {
      alert('Please select at least one language you understand');
      return;
    }

    setSaving(true);
    try {
      await onSave(speaksLanguages, understandsLanguages);
      onClose();
    } catch (error) {
      console.error('Error saving languages:', error);
      alert('Failed to save language settings');
    } finally {
      setSaving(false);
    }
  };

  const filteredLanguages = languages.filter(lang =>
    lang.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lang.native_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lang.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-gradient-to-br from-black via-gray-950 to-red-950/30 border border-red-500/30 rounded-3xl shadow-[0_0_60px_rgba(220,38,38,0.4)] w-full max-w-4xl max-h-[90vh] overflow-hidden backdrop-blur-xl animate-scale-in">
        <style>{`
          @keyframes fade-in {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes scale-in {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
          }
          .animate-fade-in {
            animation: fade-in 0.2s ease-out;
          }
          .animate-scale-in {
            animation: scale-in 0.3s ease-out;
          }
        `}</style>
        {/* Header */}
        <div className="bg-gradient-to-r from-red-600/20 via-red-500/10 to-transparent p-6 border-b border-red-500/30 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative w-12 h-12 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-lg shadow-red-600/50">
                <div className="absolute inset-0 bg-red-500 rounded-2xl blur-lg opacity-50" />
                <Globe className="w-6 h-6 text-white relative z-10" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">Language Settings</h2>
                <p className="text-sm text-gray-400">Configure languages for real-time translation</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="group p-2 hover:bg-white/10 rounded-2xl transition-all hover:scale-110 active:scale-95"
            >
              <X className="w-6 h-6 text-gray-400 group-hover:text-white transition-colors" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader className="w-8 h-8 text-red-500 animate-spin" />
              <span className="ml-3 text-gray-400">Loading languages...</span>
            </div>
          ) : (
            <>
              {/* Search */}
              <div className="mb-6">
                <div className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-red-600 rounded-2xl opacity-0 group-focus-within:opacity-30 blur transition-opacity" />
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 z-10" />
                  <input
                    type="text"
                    placeholder="Search languages..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="relative w-full pl-12 pr-4 py-3 bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm border border-white/20 rounded-2xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 transition-all"
                  />
                </div>
              </div>

              {/* Instructions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="relative bg-gradient-to-br from-red-600/10 to-red-800/10 border border-red-500/30 rounded-2xl p-5 backdrop-blur-sm hover:border-red-500/50 transition-all group">
                  <div className="absolute inset-0 bg-red-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="relative z-10">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-8 h-8 rounded-xl bg-red-600/20 flex items-center justify-center">
                        <Ear className="w-5 h-5 text-red-400" />
                      </div>
                      <h3 className="text-lg font-semibold text-white">I Want to Understand</h3>
                    </div>
                    <p className="text-sm text-gray-300 mb-3">
                      What language do you want to UNDERSTAND? Everyone will be translated TO this language for you.
                    </p>
                    <div className="bg-red-900/20 border border-red-600/30 rounded-xl p-3 mb-3">
                      <p className="text-xs text-red-300">
                        💡 <strong>Example:</strong> Choose Portuguese → Everything others say will be translated to Portuguese for you
                      </p>
                    </div>
                    <div className="text-sm text-red-400 font-medium">
                      ✓ Selected: {understandsLanguages.length} language{understandsLanguages.length !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>

                <div className="relative bg-gradient-to-br from-purple-600/10 to-purple-800/10 border border-purple-500/30 rounded-2xl p-5 backdrop-blur-sm hover:border-purple-500/50 transition-all group">
                  <div className="absolute inset-0 bg-purple-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="relative z-10">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-8 h-8 rounded-xl bg-purple-600/20 flex items-center justify-center">
                        <Mic className="w-5 h-5 text-purple-400" />
                      </div>
                      <h3 className="text-lg font-semibold text-white">I Will Speak</h3>
                    </div>
                    <p className="text-sm text-gray-300 mb-3">
                      What language will you SPEAK? Your voice will be translated FROM this language to others.
                    </p>
                    <div className="bg-purple-900/20 border border-purple-600/30 rounded-xl p-3 mb-3">
                      <p className="text-xs text-purple-300">
                        💡 <strong>Example:</strong> Choose Portuguese → When you speak Portuguese, it will be translated to English (or what others chose)
                      </p>
                    </div>
                    <div className="text-sm text-purple-400 font-medium">
                      ✓ Selected: {speaksLanguages.length} language{speaksLanguages.length !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>
              </div>

              {/* Language Grid */}
              <div className="space-y-3">
                {filteredLanguages.map((lang) => (
                  <div
                    key={lang.code}
                    className="relative bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-white/10 rounded-2xl p-5 hover:border-white/20 transition-all backdrop-blur-sm group"
                  >
                    <div className="absolute inset-0 bg-red-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-3xl">{lang.flag}</span>
                        <div>
                          <div className="text-white font-semibold">{lang.name}</div>
                          <div className="text-sm text-gray-400">{lang.native_name}</div>
                        </div>
                      </div>

                      <div className="flex gap-3">
                        {/* Understands checkbox (Vermelho - ícone ouvido) */}
                        <button
                          onClick={() => toggleUnderstands(lang.code)}
                          className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all relative group ${
                            understandsLanguages.includes(lang.code)
                              ? 'bg-gradient-to-r from-red-600 to-red-500 text-white shadow-lg shadow-red-500/30 hover:from-red-700 hover:to-red-600'
                              : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/70 border border-white/10'
                          }`}
                          title="I want to UNDERSTAND this language"
                        >
                          <Ear className="w-4 h-4" />
                          {understandsLanguages.includes(lang.code) && <Check className="w-4 h-4" />}
                          {/* Tooltip */}
                          <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none border border-red-500/30">
                            Understand
                          </div>
                        </button>

                        {/* Speaks checkbox (Roxo - ícone microfone) */}
                        <button
                          onClick={() => toggleSpeaks(lang.code)}
                          className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all relative group ${
                            speaksLanguages.includes(lang.code)
                              ? 'bg-gradient-to-r from-purple-600 to-purple-500 text-white shadow-lg shadow-purple-500/30 hover:from-purple-700 hover:to-purple-600'
                              : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/70 border border-white/10'
                          }`}
                          title="I will SPEAK this language"
                        >
                          <Mic className="w-4 h-4" />
                          {speaksLanguages.includes(lang.code) && <Check className="w-4 h-4" />}
                          {/* Tooltip */}
                          <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none border border-purple-500/30">
                            Speak
                          </div>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {filteredLanguages.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                  No languages found matching "{searchTerm}"
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-900/50 border-t border-gray-800 p-6">
          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-6 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || speaksLanguages.length === 0 || understandsLanguages.length === 0}
              className="px-6 py-3 bg-gradient-to-r from-red-600 to-purple-600 text-white rounded-lg hover:from-red-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {saving ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-5 h-5" />
                  Save Settings
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LanguageConfigModal;
