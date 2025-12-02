/**
 * Home Page - Premium Landing
 * Landing page with meeting join/create options
 */
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Video, Globe, Mic2, Zap, Sparkles, Shield, ArrowRight, Settings } from 'lucide-react';
import { useLanguageContext } from '../contexts/LanguageContext';
import VoiceSetupModal from '../components/VoiceSetupModal';
import { authenticatedFetch, apiFetch } from '../utils/api';

interface HomeProps {
  onJoinMeeting: (roomId: string, token: string, participants?: string[], language?: string) => void;
  userPreferences?: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    notifications: boolean;
    analytics: boolean;
  };
  onUpdatePreferences?: (preferences: any) => void;
  user?: { username: string; email: string } | null;
  onLogout?: () => void;
}

const ROOM_ID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PENDING_ROOM_STORAGE_KEY = 'orbis_pending_room';

const extractRoomIdFromUrl = (value: string): string => {
  try {
    const parsed = new URL(value);
    const param = parsed.searchParams.get('room');
    if (param && ROOM_ID_REGEX.test(param)) {
      return param;
    }
    const segments = parsed.pathname.split('/').filter(Boolean);
    const candidate = segments[segments.length - 1];
    if (candidate && ROOM_ID_REGEX.test(candidate)) {
      return candidate;
    }
  } catch {
    // Not a URL, ignore
  }
  return '';
};

const normalizeRoomCode = (rawValue: string): string => {
  if (!rawValue) {
    return '';
  }

  const trimmed = rawValue.trim();
  if (!trimmed) {
    return '';
  }

  const fromUrl = extractRoomIdFromUrl(trimmed);
  if (fromUrl) {
    return fromUrl;
  }

  const inlineMatch = trimmed.match(/room=([0-9a-fA-F-]{36})/);
  if (inlineMatch && inlineMatch[1] && ROOM_ID_REGEX.test(inlineMatch[1])) {
    return inlineMatch[1];
  }

  return ROOM_ID_REGEX.test(trimmed) ? trimmed : '';
};

const showRoomDetectedNotification = (message: string) => {
  if (typeof document === 'undefined') {
    return;
  }

  const notification = document.createElement('div');
  notification.className = 'fixed top-4 right-4 z-50 bg-red-500/10 border border-red-500/20 text-red-400 px-6 py-3 rounded-xl shadow-lg animate-slide-down';
  notification.innerHTML = `
    <div class="flex items-center gap-2">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <span>${message}</span>
    </div>
  `;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 5000);
};

const Home: React.FC<HomeProps> = ({ onJoinMeeting, user, onLogout }) => {
  const { t } = useLanguageContext();
  const [roomId, setRoomId] = useState('');
  const [loading, setLoading] = useState(false);
  const [showVoiceSetup, setShowVoiceSetup] = useState(false);
  const [pendingMeetingCreation, setPendingMeetingCreation] = useState(false);
  const [pendingRoomId, setPendingRoomId] = useState<string | null>(null);

  // Auto-detect room ID from URL parameter (?room=)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const roomParam = urlParams.get('room');

    if (roomParam) {
      const normalizedRoom = normalizeRoomCode(roomParam);
      if (normalizedRoom) {
        console.log('🔗 Room ID detected from URL:', normalizedRoom);
        setRoomId(normalizedRoom);

        // Clean URL without reloading page
        window.history.replaceState({}, '', window.location.pathname);

        showRoomDetectedNotification('Room link detected! Click "Join" to enter the meeting.');
      }
    }
  }, []);

  useEffect(() => {
    if (roomId) {
      return;
    }

    if (typeof window === 'undefined') {
      return;
    }

    const storedRoom = sessionStorage.getItem(PENDING_ROOM_STORAGE_KEY);
    if (storedRoom) {
      const normalizedRoom = normalizeRoomCode(storedRoom);
      if (normalizedRoom) {
        setRoomId(normalizedRoom);
        showRoomDetectedNotification('Room link restored after login. Click "Join" to enter the meeting.');
      }
      sessionStorage.removeItem(PENDING_ROOM_STORAGE_KEY);
    }
  }, [roomId]);

  const ensureVoiceProfileExists = async (): Promise<boolean> => {
    try {
      const response = await authenticatedFetch('/api/voices/profile', { method: 'GET' });

      if (response.ok) {
        localStorage.setItem('hasVoiceProfile', 'true');
        return true;
      }

      if (response.status === 404) {
        localStorage.setItem('hasVoiceProfile', 'false');
        return false;
      }

      console.warn('Unexpected status when checking voice profile:', response.status);
      return true;
    } catch (error) {
      console.error('Error checking voice profile:', error);
      return true;
    }
  };

  const joinRoomOnServer = async (targetRoomId: string, token: string) => {
    const response = await apiFetch(`/api/rooms/${targetRoomId}/join`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        input_language: 'auto',
        output_language: 'auto'
      })
    });

    if (!response.ok) {
      let detail = 'Failed to join room';
      try {
        const errorData = await response.json();
        detail = errorData.detail || detail;
      } catch {
        // Ignore parse errors
      }
      throw new Error(detail);
    }
  };

  const checkVoiceProfileAndCreateMeeting = async () => {
    setLoading(true);

    // Get real token from localStorage
    const token = localStorage.getItem('auth_token');

    if (!token) {
      alert('Você precisa fazer login primeiro!\n\nPor favor, acesse /login para autenticar.');
      window.location.href = '/login';
      setLoading(false);
      return;
    }

    try {
      const hasVoiceProfile = await ensureVoiceProfileExists();

      if (!hasVoiceProfile) {
        setLoading(false);
        setShowVoiceSetup(true);
        setPendingMeetingCreation(true);
        return;
      }

      await createMeetingRoom(token);
    } catch (error) {
      console.error('Error checking voice profile:', error);
      // On error, still allow meeting creation
      await createMeetingRoom(token);
    }
  };

  const createMeetingRoom = async (token: string) => {
    setLoading(true);

    // Create real room via API
    try {
      const response = await authenticatedFetch('/api/rooms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: 'Quick Meeting',
          description: 'Meeting created from home',
          max_participants: 10,
          is_public: false
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create room');
      }

      const data = await response.json();
      localStorage.setItem('hasVoiceProfile', 'true');
      await joinRoomOnServer(data.id, token);
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(PENDING_ROOM_STORAGE_KEY);
      }
      setPendingRoomId(null);
      onJoinMeeting(data.id, token);
    } catch (error) {
      console.error('Error creating meeting:', error);
      alert('Error creating room. Check if you are authenticated.');
      window.location.href = '/login';
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMeeting = () => {
    checkVoiceProfileAndCreateMeeting();
  };

  const handleVoiceSetupComplete = () => {
    setShowVoiceSetup(false);
    localStorage.setItem('hasVoiceProfile', 'true');
    if (pendingMeetingCreation) {
      setPendingMeetingCreation(false);
      const token = localStorage.getItem('auth_token');
      if (token) {
        createMeetingRoom(token);
      }
    } else {
      void resumePendingRoomJoin();
    }
  };

  const handleVoiceSetupClose = () => {
    setShowVoiceSetup(false);
    if (pendingMeetingCreation) {
      // User skipped voice setup but still wants to create meeting
      setPendingMeetingCreation(false);
      const token = localStorage.getItem('auth_token');
      if (token) {
        createMeetingRoom(token);
      }
    } else if (pendingRoomId || roomId.trim()) {
      void resumePendingRoomJoin();
    }
  };

  const checkVoiceProfileAndJoinMeeting = async (targetRoomId: string) => {
    if (!targetRoomId) {
      return;
    }

    setLoading(true);

    const token = localStorage.getItem('auth_token');

    if (!token) {
      alert('Você precisa fazer login primeiro!\n\nPor favor, acesse /login para autenticar.');
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(PENDING_ROOM_STORAGE_KEY, targetRoomId);
      }
      window.location.href = '/login';
      setLoading(false);
      return;
    }

    try {
      const hasVoiceProfile = await ensureVoiceProfileExists();

      if (!hasVoiceProfile) {
        setLoading(false);
        setShowVoiceSetup(true);
        setPendingMeetingCreation(false);
        setPendingRoomId(targetRoomId);
        if (typeof window !== 'undefined') {
          sessionStorage.setItem(PENDING_ROOM_STORAGE_KEY, targetRoomId);
        }
        return;
      }

      await joinRoomOnServer(targetRoomId, token);
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(PENDING_ROOM_STORAGE_KEY);
      }
      setPendingRoomId(null);
      onJoinMeeting(targetRoomId, token);
    } catch (error) {
      console.error('Error checking voice profile:', error);
      const message = error instanceof Error
        ? error.message
        : 'Erro ao entrar na sala. Verifique o link e tente novamente.';
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  const resumePendingRoomJoin = async () => {
    const targetRoomId = pendingRoomId || normalizeRoomCode(roomId);
    if (!targetRoomId) {
      alert('Insira um link ou código de reunião válido para continuar.');
      return;
    }

    const token = localStorage.getItem('auth_token');
    if (!token) {
      alert('Você precisa fazer login primeiro!\n\nPor favor, acesse /login para autenticar.');
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(PENDING_ROOM_STORAGE_KEY, targetRoomId);
      }
      window.location.href = '/login';
      return;
    }

    setLoading(true);
    try {
      await joinRoomOnServer(targetRoomId, token);
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(PENDING_ROOM_STORAGE_KEY);
      }
      setPendingRoomId(null);
      onJoinMeeting(targetRoomId, token);
    } catch (error) {
      console.error('Error joining room after voice setup:', error);
      const message = error instanceof Error
        ? error.message
        : 'Não foi possível entrar na sala. Tente novamente.';
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  const handleJoinMeeting = () => {
    const normalizedRoom = normalizeRoomCode(roomId);
    if (!normalizedRoom) {
      alert('Insira um link ou código de reunião válido.');
      return;
    }

    if (normalizedRoom !== roomId) {
      setRoomId(normalizedRoom);
    }

    void checkVoiceProfileAndJoinMeeting(normalizedRoom);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-950 to-zinc-950 flex flex-col relative overflow-hidden">
      {/* Animated background elements - Sutil glow effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.03),transparent_50%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem]" />

        {/* Subtle glowing orbs */}
        <div className="absolute top-20 right-20 w-96 h-96 bg-white/5 rounded-full filter blur-3xl animate-float" />
        <div className="absolute bottom-20 left-20 w-96 h-96 bg-white/5 rounded-full filter blur-3xl animate-float" style={{ animationDelay: '2s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-radial from-white/[0.02] to-transparent rounded-full" />
      </div>
      {/* Header */}
      <header className="px-6 py-6 relative z-10 animate-slide-down">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <img src="/logo.png" alt="Orbis" className="w-10 h-10 rounded-3xl" />
            </div>
            <h1 className="text-white text-3xl font-bold tracking-tight">Orbis</h1>
            <span className="bg-gradient-to-r from-red-500 to-red-600 text-white text-xs px-2 py-1 rounded-full font-semibold">FREE</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Description Button */}
            <a
              href="/description"
              className="bg-white/5 backdrop-blur-xl border border-white/10 text-white px-4 py-2.5 rounded-xl transition-all hover:bg-white/10 hover:border-white/20 hover:shadow-[0_0_20px_rgba(255,255,255,0.1)] font-medium flex items-center gap-2 group"
              title="View Platform Description"
            >
              <Sparkles size={18} className="text-red-400" />
              <span className="hidden md:inline">Description</span>
            </a>

            {user ? (
              <>
                <span className="text-gray-300 text-sm hidden md:block">
                  {t('welcome')}, <span className="font-semibold text-white">{user.username}</span>
                </span>
                <a
                  href="/settings"
                  className="bg-white/5 backdrop-blur-xl border border-white/10 text-white p-2.5 rounded-xl transition-all hover:bg-white/10 hover:border-white/20 hover:shadow-[0_0_20px_rgba(255,255,255,0.1)]"
                  title={t('settings')}
                >
                  <Settings size={20} />
                </a>
                <button
                  onClick={onLogout}
                  className="bg-white/5 backdrop-blur-xl border border-white/10 text-white px-6 py-2.5 rounded-xl transition-all hover:bg-red-500/10 hover:border-red-500/30 hover:shadow-[0_0_20px_rgba(239,68,68,0.2)] font-medium flex items-center gap-2 group"
                >
                  {t('sign_out')}
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </button>
              </>
            ) : (
              <a href="/login" className="bg-white/5 backdrop-blur-xl border border-white/10 text-white px-6 py-2.5 rounded-xl transition-all hover:bg-white/10 hover:border-white/20 hover:shadow-[0_0_20px_rgba(255,255,255,0.1)] font-medium flex items-center gap-2 group">
                {t('sign_in')}
                <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex items-center justify-center px-6 py-12 relative z-10">
        <div className="max-w-5xl w-full">
          <div className="text-center mb-16 animate-fade-in">
            <div className="inline-flex items-center gap-2 bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-full text-sm font-medium mb-6 hover-lift">
              <Sparkles size={16} />
              {t('powered_by_ai')}
            </div>
            <h2 className="text-6xl md:text-7xl font-black text-white mb-6 leading-tight relative z-20">
              {t('hero_title_1')}<br />
              <span className="text-white">{t('hero_title_2')}</span>
            </h2>
            <p className="text-xl md:text-2xl text-gray-300 mb-4 max-w-3xl mx-auto leading-relaxed">
              {t('hero_description')}
            </p>
            <p className="text-gray-400 flex items-center justify-center gap-2">
              <Zap size={16} className="text-yellow-400" />
              <span className="font-semibold text-white">170ms</span> {t('end_to_end_latency')}
            </p>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-4 gap-4 mb-16 animate-slide-up">
            <Feature
              icon={Mic2}
              title={t('voice_cloning')}
              description={t('voice_cloning_desc')}
              gradient="from-gray-800 to-gray-900"
            />
            <Feature
              icon={Zap}
              title={t('ultra_fast')}
              description={t('ultra_fast_desc')}
              gradient="from-yellow-500 to-orange-500"
            />
            <Feature
              icon={Video}
              title={t('hd_video')}
              description={t('hd_video_desc')}
              gradient="from-gray-800 to-gray-900"
            />
            <Feature
              icon={Shield}
              title={t('secure')}
              description={t('secure_desc')}
              gradient="from-green-500 to-emerald-500"
            />
          </div>

          {/* Meeting Controls */}
          <div className="bg-black/40 backdrop-blur-xl rounded-3xl p-8 shadow-[0_8px_32px_rgba(0,0,0,0.4)] border border-white/10 animate-scale-in hover-lift relative overflow-hidden">
            {/* Subtle inner glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] via-transparent to-transparent pointer-events-none" />

            <div className="space-y-6 relative z-10">
              {/* Create Meeting */}
              <div>
                <button
                  onClick={handleCreateMeeting}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-800 disabled:to-gray-900 text-white py-5 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-3 shadow-[0_0_40px_rgba(220,38,38,0.3)] hover:shadow-[0_0_60px_rgba(220,38,38,0.5)] hover:scale-[1.02] active:scale-[0.98] group border border-red-500/20"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                      <span>{t('creating')}</span>
                    </>
                  ) : (
                    <>
                      <Video size={24} className="group-hover:scale-110 transition-transform" />
                      {t('create_instant_meeting')}
                      <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>
              </div>

              {/* Divider */}
              <div className="flex items-center gap-4">
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                <span className="text-gray-500 text-sm font-medium">{t('or')}</span>
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
              </div>

              {/* Join Meeting */}
              <div className="flex gap-3">
                <input
                  type="text"
                  value={roomId}
                  onChange={(e) => setRoomId(e.target.value)}
                  placeholder={t('enter_room_code')}
                  className="flex-1 bg-black/60 backdrop-blur-xl border border-white/10 text-white px-5 py-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 placeholder-gray-500 transition-all hover:border-white/20"
                  onKeyPress={(e) => e.key === 'Enter' && handleJoinMeeting()}
                />
                <button
                  onClick={handleJoinMeeting}
                  disabled={loading || !roomId.trim()}
                  className="bg-white/5 backdrop-blur-xl border border-white/10 hover:bg-white/10 hover:border-white/20 hover:shadow-[0_0_20px_rgba(255,255,255,0.1)] disabled:opacity-50 disabled:hover:bg-white/5 disabled:hover:shadow-none text-white px-10 py-4 rounded-xl font-semibold transition-all hover:scale-105 active:scale-95"
                >
                  {t('join')}
                </button>
              </div>
            </div>
          </div>

          {/* Info */}
          <div className="mt-12 text-center space-y-4">
            <p className="text-gray-400 flex items-center justify-center gap-4 flex-wrap">
              <span className="flex items-center gap-2">
                <Globe size={16} />
                {t('works_in_browser')}
              </span>
              <span className="text-gray-600">•</span>
              <span className="flex items-center gap-2">
                <Sparkles size={16} />
                {t('free_to_use')}
              </span>
            </p>
            <p className="text-sm text-gray-500">
              {t('join_thousands')}
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-8 text-center text-gray-500 relative z-10 border-t border-white/5">
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex items-center justify-center gap-6 text-sm">
            <Link to="/terms" className="hover:text-white transition-colors">
              Terms of Service
            </Link>
            <span>•</span>
            <Link to="/privacy" className="hover:text-white transition-colors">
              Privacy Policy
            </Link>
            <span>•</span>
            <a href="mailto:orbis.ai.app@gmail.com" className="hover:text-white transition-colors">
              Contact
            </a>
          </div>
          <p className="text-sm">{t('footer_text')}</p>
        </div>
      </footer>

      {/* Voice Setup Modal */}
      <VoiceSetupModal
        isOpen={showVoiceSetup}
        onClose={handleVoiceSetupClose}
        onComplete={handleVoiceSetupComplete}
      />
    </div>
  );
};

interface FeatureProps {
  icon: React.ElementType;
  title: string;
  description: string;
  gradient: string;
}

const Feature: React.FC<FeatureProps> = ({ icon: Icon, title, description, gradient }) => {
  return (
    <div className="bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl p-6 text-center hover-lift cursor-default group transition-all hover:bg-black/40 hover:border-white/20 hover:shadow-[0_8px_32px_rgba(0,0,0,0.3)]">
      <div className={`bg-gradient-to-br ${gradient} rounded-2xl w-14 h-14 flex items-center justify-center mx-auto mb-4 shadow-[0_0_20px_rgba(0,0,0,0.5)] group-hover:scale-110 group-hover:shadow-[0_0_30px_rgba(0,0,0,0.7)] transition-all`}>
        <Icon size={26} className="text-white" />
      </div>
      <h3 className="text-white font-bold mb-2">{title}</h3>
      <p className="text-gray-500 text-sm leading-relaxed">{description}</p>
    </div>
  );
};

export default Home;