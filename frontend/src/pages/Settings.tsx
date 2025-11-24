/**
 * User Settings Page - Comprehensive user configuration
 */
import React, { useState, useEffect } from 'react';
import {
  User, Mail, Lock, Bell, Globe, Palette, Shield, Key,
  Mic, Video, Volume2, Trash2, Download, Upload, Settings as SettingsIcon,
  Check, X, AlertCircle, Loader, Eye, EyeOff, LogOut, CreditCard, Save
} from 'lucide-react';
import { useLanguageContext } from '../contexts/LanguageContext';
import { Language } from '../i18n/translations';

interface SettingsProps {
  user: {
    id: string;
    email: string;
    username: string;
    fullName?: string;
    avatarUrl?: string;
    bio?: string;
    company?: string;
    jobTitle?: string;
    preferences?: any;
    isOauthUser?: boolean;  // True if user logged in via OAuth
  };
  onUpdateProfile: (data: any) => Promise<void>;
  onChangePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  onDeleteAccount: (password: string, confirmation: string) => Promise<void>;
  onUpdatePreferences: (preferences: any) => Promise<void>;
  onLogout: () => void;
}

const Settings: React.FC<SettingsProps> = ({
  user,
  onUpdateProfile,
  onChangePassword,
  onDeleteAccount,
  onUpdatePreferences,
  onLogout
}) => {
  // Initialize language hook
  const { currentLanguage, changeLanguage, t } = useLanguageContext();

  const [activeTab, setActiveTab] = useState('account');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [isOauthUser, setIsOauthUser] = useState(user?.isOauthUser || false);

  // Load updated user data on mount
  React.useEffect(() => {
    const loadUserData = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) return;

        const response = await fetch('http://localhost:8000/api/users/me', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const updatedUser = await response.json();
          console.log('✅ Loaded updated user data:', {
            email: updatedUser.email,
            is_oauth_user: updatedUser.is_oauth_user,
            password_hash_exists: updatedUser.password_hash !== null
          });

          // Update local state immediately
          setIsOauthUser(updatedUser.is_oauth_user);

          // Update localStorage
          const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
          currentUser.isOauthUser = updatedUser.is_oauth_user;
          localStorage.setItem('user', JSON.stringify(currentUser));

          console.log('✅ Updated isOauthUser state:', updatedUser.is_oauth_user);
        }
      } catch (error) {
        console.error('Failed to load user data:', error);
      }
    };

    loadUserData();
  }, []);

  // Debug effect
  React.useEffect(() => {
    console.log('Settings component mounted/updated', {
      activeTab,
      showDeleteModal,
      hasUser: !!user,
      userEmail: user?.email,
      isOauthUser: isOauthUser,
      userObject: user
    });
  }, [activeTab, showDeleteModal, user, isOauthUser]);

  // Password fields
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Preferences
  const [language] = useState(currentLanguage); // Read-only, auto-detected from browser
  const [autoDetectInput, setAutoDetectInput] = useState(user.preferences?.auto_detect_input ?? true);
  const [autoDetectOutput, setAutoDetectOutput] = useState(user.preferences?.auto_detect_output ?? true);

  // Notifications
  const [emailNotifications, setEmailNotifications] = useState(user.preferences?.email_notifications ?? true);
  const [pushNotifications, setPushNotifications] = useState(user.preferences?.push_notifications ?? true);
  const [meetingReminders, setMeetingReminders] = useState(user.preferences?.meeting_reminders ?? true);
  const [newFeatures, setNewFeatures] = useState(user.preferences?.feature_updates ?? true);

  // Audio settings
  const [micVolume, setMicVolume] = useState(user.preferences?.microphone_volume || 80);
  const [speakerVolume, setSpeakerVolume] = useState(user.preferences?.speaker_volume || 80);
  const [echoCancellation, setEchoCancellation] = useState(user.preferences?.echo_cancellation ?? true);
  const [noiseSuppression, setNoiseSuppression] = useState(user.preferences?.noise_suppression ?? true);

  // Voice profile state
  const [voiceProfile, setVoiceProfile] = useState<any>(null);
  const [loadingVoiceProfile, setLoadingVoiceProfile] = useState(false);
  const [uploadingVoice, setUploadingVoice] = useState(false);
  const [deletingVoice, setDeletingVoice] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const tabs = [
    { id: 'account', label: t('account_tab'), icon: Mail },
    { id: 'security', label: t('security_tab'), icon: Shield },
    { id: 'preferences', label: t('preferences_tab'), icon: Palette },
    { id: 'notifications', label: t('notifications_tab'), icon: Bell },
    { id: 'audio', label: t('audio_tab'), icon: Mic },
    { id: 'danger', label: t('danger_tab'), icon: AlertCircle }
  ];

  // Load voice profile when audio tab is active
  useEffect(() => {
    if (activeTab === 'audio') {
      loadVoiceProfile();
    }
  }, [activeTab]);

  const loadVoiceProfile = async () => {
    setLoadingVoiceProfile(true);
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('http://localhost:8000/api/voices/profile', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setVoiceProfile(data);

        // Load audio file with authentication and create blob URL
        const audioResponse = await fetch('http://localhost:8000/api/voices/profile/audio', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (audioResponse.ok) {
          const blob = await audioResponse.blob();
          const url = URL.createObjectURL(blob);

          // Revoke old URL if exists to free memory
          if (audioUrl) {
            URL.revokeObjectURL(audioUrl);
          }

          setAudioUrl(url);
        }
      } else if (response.status === 404) {
        setVoiceProfile(null);
        setAudioUrl(null);
      }
    } catch (err) {
      console.error('Error loading voice profile:', err);
    } finally {
      setLoadingVoiceProfile(false);
    }
  };

  const handleVoiceUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('audio/')) {
      setError('Please select a valid audio file');
      return;
    }

    setUploadingVoice(true);
    setError('');

    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        throw new Error('You need to be logged in to upload');
      }

      console.log('🎤 Uploading voice profile with token:', token.substring(0, 20) + '...');

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/api/voices/upload-profile-voice', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      console.log('📤 Upload response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('❌ Upload error:', errorData);

        // Check if token expired
        if (response.status === 401) {
          setError('Your session expired. Logout and login again.');
          setTimeout(() => {
            if (confirm('Your session expired. Do you want to logout now?')) {
              onLogout();
            }
          }, 1000);
          return;
        }

        throw new Error(errorData.detail || 'Failed to upload voice profile');
      }

      setSuccess('Voice profile saved! Will be used in next meetings.');
      await loadVoiceProfile();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      console.error('❌ Voice upload error:', err);
      setError(err.message || 'Error uploading voice profile');
    } finally {
      setUploadingVoice(false);
      event.target.value = '';
    }
  };

  const handleDeleteVoiceProfile = async () => {
    if (!confirm('Are you sure you want to delete your voice profile? This action cannot be undone.')) {
      return;
    }

    setDeletingVoice(true);
    setError('');

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('http://localhost:8000/api/voices/profile', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to delete voice profile');
      }

      setSuccess('Voice profile deleted successfully');
      setVoiceProfile(null);

      // Revoke audio URL to free memory
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }

      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Error deleting voice profile');
    } finally {
      setDeletingVoice(false);
    }
  };

  const handleSavePreferences = async () => {
    console.log('💾 Saving preferences:', { autoDetectInput, autoDetectOutput });
    console.log('ℹ️ Language is auto-detected from browser:', language);
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Only save to backend if user is logged in
      if (user && user.id) {
        try {
          const preferences = {
            primary_language: language, // Save auto-detected language
            auto_detect_input: autoDetectInput,
            auto_detect_output: autoDetectOutput
          };
          console.log('📤 Sending preferences to server:', preferences);
          await onUpdatePreferences(preferences);
        } catch (backendError: any) {
          console.error('❌ Backend error:', backendError);
          // If 401, just save locally
          if (backendError.message?.includes('401') || backendError.message?.includes('Unauthorized')) {
            console.log('💾 Saving to localStorage due to auth error');
            localStorage.setItem('orbis_preferences', JSON.stringify({
              primary_language: language,
              auto_detect_input: autoDetectInput,
              auto_detect_output: autoDetectOutput
            }));
          } else {
            throw backendError; // Re-throw non-auth errors
          }
        }
      } else {
        // Save to localStorage only
        console.log('💾 Saving preferences to localStorage (not logged in)');
        localStorage.setItem('orbis_preferences', JSON.stringify({
          primary_language: language,
          auto_detect_input: autoDetectInput,
          auto_detect_output: autoDetectOutput
        }));
      }

      console.log('✅ Preferences saved successfully!');
      setSuccess(t('preferences_saved'));
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      console.error('❌ Failed to save preferences:', err);
      setError(err.message || 'Failed to save preferences');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNotifications = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await onUpdatePreferences({
        email_notifications: emailNotifications,
        push_notifications: pushNotifications,
        meeting_reminders: meetingReminders,
        feature_updates: newFeatures
      });
      setSuccess('Notification settings saved!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save notification settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAudio = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await onUpdatePreferences({
        microphone_volume: micVolume,
        speaker_volume: speakerVolume,
        echo_cancellation: echoCancellation,
        noise_suppression: noiseSuppression
      });
      setSuccess('Audio settings saved!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save audio settings');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      setLoading(false);
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      setLoading(false);
      return;
    }

    try {
      await onChangePassword(currentPassword, newPassword);
      setSuccess('Password changed successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err.message || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    console.log('handleDeleteAccount called', { deletePassword: !!deletePassword, deleteConfirmation, isOauthUser: isOauthUser });
    setLoading(true);
    setError('');

    try {
      // OAuth users don't need password, send empty string
      const passwordToSend = isOauthUser ? '' : deletePassword;
      await onDeleteAccount(passwordToSend, deleteConfirmation);
      console.log('Account deleted successfully');
      // Account deleted, user will be logged out
    } catch (err: any) {
      console.error('Delete account error:', err);
      setError(err.message || 'Failed to delete account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-950 to-zinc-950 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.03),transparent_50%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem]" />
      {/* Header */}
      <header className="bg-black/40 backdrop-blur-xl border-b border-white/10 relative z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a href="/" className="flex items-center gap-3">
              <img src="/logo.png" alt="Orbis" className="w-10 h-10 rounded-2xl" />
              <h1 className="text-white text-2xl font-bold">Orbis</h1>
            </a>
            <span className="text-gray-400">/</span>
            <h2 className="text-white text-xl">{t('settings_title')}</h2>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-2 px-4 py-2 bg-black/60 border border-white/10 hover:bg-white/10 hover:border-white/20 rounded-lg text-white transition-all"
          >
            <LogOut size={16} />
            {t('logout')}
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="md:col-span-1">
            <div className="bg-black/30 backdrop-blur-xl rounded-2xl p-4 border border-white/10">
              <nav className="space-y-1">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === tab.id
                        ? 'bg-gradient-to-r from-red-500 to-red-600 text-white'
                        : 'text-gray-300 hover:bg-white/5'
                        }`}
                    >
                      <Icon size={20} />
                      <span className="font-medium">{tab.label}</span>
                    </button>
                  );
                })}
              </nav>
            </div>
          </div>

          {/* Content */}
          <div className="md:col-span-3">
            <div className="bg-black/40 backdrop-blur-xl rounded-2xl p-6 border border-white/10 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] via-transparent to-transparent pointer-events-none" />
              {/* Success/Error messages */}
              {success && (
                <div className="mb-6 p-4 bg-green-500/20 border border-green-500/50 rounded-xl flex items-center gap-3 text-green-300">
                  <Check size={20} />
                  <span>{success}</span>
                </div>
              )}
              {error && (
                <div className="mb-6 p-4 bg-white/5 border border-white/20 rounded-xl flex items-center gap-3 text-gray-300">
                  <AlertCircle size={20} />
                  <span>{error}</span>
                </div>
              )}

              {/* Account Tab */}
              {activeTab === 'account' && (
                <div className="space-y-6">
                  <h3 className="text-2xl font-bold text-white mb-6">Account Information</h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={user.email}
                      disabled
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-gray-400 cursor-not-allowed"
                    />
                    <p className="text-sm text-gray-500 mt-2">
                      Email cannot be changed. Contact support if needed.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={user.username}
                      disabled
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-gray-400 cursor-not-allowed"
                    />
                    <p className="text-sm text-gray-500 mt-2">
                      Username cannot be changed.
                    </p>
                  </div>

                  <div className="pt-6 border-t border-white/10">
                    <h4 className="text-lg font-semibold text-white mb-4">Account Status</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                        <div className="flex items-center gap-2 text-green-400 mb-1">
                          <Check size={20} />
                          <span className="font-semibold">Email Verified</span>
                        </div>
                        <p className="text-sm text-gray-400">Your email is verified</p>
                      </div>
                      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                        <div className="flex items-center gap-2 text-blue-400 mb-1">
                          <CreditCard size={20} />
                          <span className="font-semibold">Free Plan</span>
                        </div>
                        <p className="text-sm text-gray-400">Basic features included</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Security Tab */}
              {activeTab === 'security' && (
                <div className="space-y-6">
                  <h3 className="text-2xl font-bold text-white mb-6">Security Settings</h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Current Password
                    </label>
                    <div className="relative">
                      <input
                        type={showCurrentPassword ? 'text' : 'password'}
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="w-full px-4 py-3 bg-black/60 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 hover:border-white/20 transition-all"
                        placeholder="Enter current password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                      >
                        {showCurrentPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      New Password
                    </label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="w-full px-4 py-3 bg-black/60 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 hover:border-white/20 transition-all"
                        placeholder="Enter new password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                      >
                        {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full px-4 py-3 bg-black/60 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 hover:border-white/20 transition-all"
                      placeholder="Confirm new password"
                    />
                  </div>

                  <button
                    onClick={handleChangePassword}
                    disabled={loading || !currentPassword || !newPassword || !confirmPassword}
                    className="w-full py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-800 disabled:to-gray-900 text-white rounded-xl font-medium transition-all shadow-[0_0_40px_rgba(220,38,38,0.3)] hover:shadow-[0_0_60px_rgba(220,38,38,0.5)] border border-red-500/20 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader className="animate-spin" size={20} />
                        Changing...
                      </>
                    ) : (
                      <>
                        <Lock size={20} />
                        Change Password
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Preferences Tab */}
              {activeTab === 'preferences' ? (
                <div className="space-y-6">
                  <h3 className="text-2xl font-bold text-white mb-6">{t('preferences_title')}</h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      {t('language_label')} <span className="text-xs text-gray-500">(Auto-detected from browser)</span>
                    </label>
                    <select
                      value={language}
                      disabled
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-gray-400 cursor-not-allowed"
                    >
                      <option value="en">🇺🇸 English</option>
                      <option value="pt">🇧🇷 Português</option>
                      <option value="es">🇪🇸 Español</option>
                      <option value="fr">🇫🇷 Français</option>
                      <option value="de">🇩🇪 Deutsch</option>
                      <option value="it">🇮🇹 Italiano</option>
                      <option value="ja">🇯🇵 日本語</option>
                      <option value="ko">🇰🇷 한국어</option>
                      <option value="zh">🇨🇳 中文 (简体)</option>
                      <option value="ar">🇸🇦 العربية</option>
                      <option value="ru">🇷🇺 Русский</option>
                      <option value="hi">🇮🇳 हिन्दी</option>
                      <option value="nl">🇳🇱 Nederlands</option>
                      <option value="pl">🇵🇱 Polski</option>
                      <option value="tr">🇹🇷 Türkçe</option>
                      <option value="sv">🇸🇪 Svenska</option>
                      <option value="no">🇳🇴 Norsk</option>
                      <option value="da">🇩🇰 Dansk</option>
                      <option value="fi">🇫🇮 Suomi</option>
                      <option value="cs">🇨🇿 Čeština</option>
                      <option value="el">🇬🇷 Ελληνικά</option>
                      <option value="he">🇮🇱 עברית</option>
                      <option value="id">🇮🇩 Bahasa Indonesia</option>
                      <option value="th">🇹🇭 ภาษาไทย</option>
                      <option value="vi">🇻🇳 Tiếng Việt</option>
                    </select>
                  </div>

                  <div className="space-y-4 pt-4">
                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <span className="text-white font-medium">{t('auto_detect_input')}</span>
                      <input
                        type="checkbox"
                        checked={autoDetectInput}
                        onChange={(e) => setAutoDetectInput(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>

                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <span className="text-white font-medium">{t('auto_detect_output')}</span>
                      <input
                        type="checkbox"
                        checked={autoDetectOutput}
                        onChange={(e) => setAutoDetectOutput(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>
                  </div>

                  <button
                    onClick={handleSavePreferences}
                    disabled={loading}
                    className="w-full py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-800 disabled:to-gray-900 text-white rounded-xl font-medium transition-all shadow-[0_0_40px_rgba(220,38,38,0.3)] hover:shadow-[0_0_60px_rgba(220,38,38,0.5)] border border-red-500/20 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader className="animate-spin" size={20} />
                        {t('loading')}
                      </>
                    ) : (
                      <>
                        <Save size={20} />
                        {t('save_preferences')}
                      </>
                    )}
                  </button>
                </div>
              ) : null}

              {/* Notifications Tab */}
              {activeTab === 'notifications' ? (
                <div className="space-y-6">
                  <h3 className="text-2xl font-bold text-white mb-6">Notification Settings</h3>

                  <div className="space-y-4">
                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <div>
                        <div className="text-white font-medium">Email Notifications</div>
                        <div className="text-sm text-gray-400">Receive notifications via email</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={emailNotifications}
                        onChange={(e) => setEmailNotifications(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>

                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <div>
                        <div className="text-white font-medium">Push Notifications</div>
                        <div className="text-sm text-gray-400">Get notified in your browser</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={pushNotifications}
                        onChange={(e) => setPushNotifications(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>

                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <div>
                        <div className="text-white font-medium">Meeting Reminders</div>
                        <div className="text-sm text-gray-400">Remind me before meetings start</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={meetingReminders}
                        onChange={(e) => setMeetingReminders(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>

                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <div>
                        <div className="text-white font-medium">New Features</div>
                        <div className="text-sm text-gray-400">Learn about new features and updates</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={newFeatures}
                        onChange={(e) => setNewFeatures(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>
                  </div>

                  <button
                    onClick={handleSaveNotifications}
                    disabled={loading}
                    className="w-full py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-800 disabled:to-gray-900 text-white rounded-xl font-medium transition-all shadow-[0_0_40px_rgba(220,38,38,0.3)] hover:shadow-[0_0_60px_rgba(220,38,38,0.5)] border border-red-500/20 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader className="animate-spin" size={20} />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save size={20} />
                        Save Notification Settings
                      </>
                    )}
                  </button>
                </div>
              ) : null}

              {/* Audio Tab */}
              {activeTab === 'audio' ? (
                <div className="space-y-6">
                  <h3 className="text-2xl font-bold text-white mb-6">Audio & Video Settings</h3>

                  {/* Voice Profile Section */}
                  <div className="relative overflow-hidden p-6 bg-gradient-to-br from-black via-gray-950 to-black border-2 border-white/20 rounded-2xl hover-lift">
                    {/* Animated background effect */}
                    <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] via-transparent to-transparent opacity-50" />
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

                    <div className="relative z-10">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-3 rounded-xl shadow-lg shadow-white/10">
                          <Mic className="text-white" size={24} />
                        </div>
                        <div>
                          <h4 className="text-xl font-bold text-white flex items-center gap-2">
                            Perfil de Voz
                            <span className="bg-gray-800 text-white text-xs px-2 py-0.5 rounded-full font-semibold">AI</span>
                          </h4>
                          <p className="text-sm text-gray-400">Clonagem de voz com IA</p>
                        </div>
                      </div>

                      <p className="text-gray-300 text-sm mb-6 leading-relaxed">
                        Upload an audio of your voice to create a profile. It will be used automatically in next meetings for translation with <span className="text-gray-300 font-semibold">your cloned voice</span>.
                      </p>

                      {loadingVoiceProfile ? (
                        <div className="flex flex-col items-center justify-center py-12 glass-dark rounded-2xl border border-white/10">
                          <Loader className="animate-spin text-gray-400 mb-4" size={40} />
                          <p className="text-gray-400">Carregando perfil de voz...</p>
                        </div>
                      ) : voiceProfile ? (
                        <div className="space-y-4">
                          {/* Current Voice Profile Card */}
                          <div className="glass-dark rounded-2xl p-5 border border-green-500/30 shadow-xl space-y-4 animate-fade-in">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="relative">
                                  <div className="absolute inset-0 bg-green-500 rounded-xl blur-md opacity-50 animate-pulse" />
                                  <div className="relative bg-gradient-to-br from-green-500 to-emerald-600 p-2.5 rounded-xl">
                                    <Check className="text-white" size={20} />
                                  </div>
                                </div>
                                <div>
                                  <p className="text-white font-bold flex items-center gap-2">
                                    Perfil Ativo
                                    <span className="bg-green-500/20 text-green-400 text-xs px-2 py-0.5 rounded-full">✓ Verificado</span>
                                  </p>
                                  <p className="text-sm text-gray-400">
                                    Criado em {new Date(voiceProfile.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })}
                                  </p>
                                </div>
                              </div>
                              <button
                                onClick={handleDeleteVoiceProfile}
                                disabled={deletingVoice}
                                className="group px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/20 hover:border-white/30 text-gray-300 hover:text-white rounded-xl transition-all disabled:opacity-50 flex items-center gap-2 font-medium"
                              >
                                {deletingVoice ? (
                                  <>
                                    <Loader className="animate-spin" size={16} />
                                    Excluindo...
                                  </>
                                ) : (
                                  <>
                                    <Trash2 size={16} className="group-hover:scale-110 transition-transform" />
                                    Delete
                                  </>
                                )}
                              </button>
                            </div>

                            {/* Audio Player */}
                            <div className="bg-black/40 rounded-xl p-4 border border-white/5">
                              <div className="flex items-center gap-2 mb-3">
                                <Volume2 size={16} className="text-gray-400" />
                                <label className="text-sm text-gray-300 font-medium">Sample da sua voz:</label>
                              </div>
                              {audioUrl ? (
                                <audio
                                  controls
                                  className="w-full h-10 rounded-lg"
                                  style={{ filter: 'hue-rotate(0deg) saturate(1.2)' }}
                                  src={audioUrl}
                                  key={audioUrl}
                                >
                                  Seu navegador não suporta o elemento de áudio.
                                </audio>
                              ) : (
                                <div className="text-sm text-gray-400 py-2">
                                  Carregando áudio...
                                </div>
                              )}
                            </div>

                            {/* File Info */}
                            <div className="flex items-center justify-between text-xs">
                              <div className="flex items-center gap-4 text-gray-500">
                                <span>📦 Tamanho: {(voiceProfile.file_size / 1024).toFixed(2)} KB</span>
                                <span>🎵 Formato: WAV</span>
                              </div>
                            </div>
                          </div>

                          {/* Replace Voice Profile */}
                          <div className="pt-2">
                            <label className="block group">
                              <div className="cursor-pointer glass hover:bg-white/5 border-2 border-dashed border-white/20 hover:border-white/40 rounded-xl p-6 transition-all text-center relative overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                <input
                                  type="file"
                                  accept="audio/*"
                                  onChange={handleVoiceUpload}
                                  disabled={uploadingVoice}
                                  className="hidden"
                                />
                                {uploadingVoice ? (
                                  <div className="flex items-center justify-center gap-3 text-gray-400">
                                    <div className="relative">
                                      <Loader className="animate-spin" size={24} />
                                      <div className="absolute inset-0 bg-white rounded-full blur-lg opacity-30 animate-pulse" />
                                    </div>
                                    <span className="font-medium">Processando novo áudio...</span>
                                  </div>
                                ) : (
                                  <div className="relative z-10">
                                    <div className="flex items-center justify-center gap-2 mb-2">
                                      <Upload className="text-gray-400 group-hover:scale-110 transition-transform" size={24} />
                                      <span className="text-white font-semibold">Substituir Áudio</span>
                                    </div>
                                    <p className="text-sm text-gray-400">
                                      Clique para selecionar um novo arquivo
                                    </p>
                                  </div>
                                )}
                              </div>
                            </label>
                          </div>
                        </div>
                      ) : (
                        /* No Voice Profile - Upload New */
                        <div>
                          <label className="block group">
                            <div className="cursor-pointer glass-dark hover:bg-white/5 border-2 border-dashed border-white/20 hover:border-white/40 rounded-2xl p-12 transition-all text-center relative overflow-hidden">
                              {/* Animated background */}
                              <div className="absolute inset-0 bg-gradient-to-br from-white/[0.05] via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-white/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />

                              <input
                                type="file"
                                accept="audio/*"
                                onChange={handleVoiceUpload}
                                disabled={uploadingVoice}
                                className="hidden"
                              />

                              {uploadingVoice ? (
                                <div className="flex flex-col items-center gap-4 relative z-10">
                                  <div className="relative">
                                    <Loader className="animate-spin text-gray-400" size={56} />
                                    <div className="absolute inset-0 bg-white rounded-full blur-2xl opacity-30 animate-pulse" />
                                  </div>
                                  <div>
                                    <p className="text-xl text-white font-bold mb-2">Processando áudio...</p>
                                    <p className="text-sm text-gray-400">Aguarde enquanto analisamos sua voz</p>
                                  </div>
                                  <div className="flex gap-1 mt-2">
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                  </div>
                                </div>
                              ) : (
                                <div className="relative z-10">
                                  <div className="relative inline-block mb-4">
                                    <div className="absolute inset-0 bg-white rounded-2xl blur-xl opacity-20 group-hover:opacity-30 transition-opacity" />
                                    <div className="relative bg-gradient-to-br from-gray-800 to-gray-900 p-6 rounded-2xl group-hover:scale-110 transition-transform shadow-2xl">
                                      <Upload className="text-white" size={48} />
                                    </div>
                                  </div>

                                  <p className="text-2xl text-white font-bold mb-3">No voice profile found</p>
                                  <p className="text-gray-300 mb-6 max-w-md mx-auto leading-relaxed">
                                    Upload an audio with <span className="text-gray-300 font-semibold">minimum 6 seconds</span> of your voice to create your cloning profile
                                  </p>

                                  <div className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-gray-800 to-gray-900 hover:from-gray-700 hover:to-gray-800 text-white rounded-xl font-bold shadow-xl shadow-white/10 group-hover:shadow-white/15 transition-all group-hover:scale-105">
                                    <Mic size={20} />
                                    Selecionar Arquivo de Áudio
                                    <Upload size={18} />
                                  </div>

                                  <div className="flex items-center justify-center gap-6 mt-6 text-xs text-gray-500">
                                    <span className="flex items-center gap-1">
                                      ✓ WAV
                                    </span>
                                    <span className="flex items-center gap-1">
                                      ✓ MP3
                                    </span>
                                    <span className="flex items-center gap-1">
                                      ✓ OGG
                                    </span>
                                    <span className="flex items-center gap-1">
                                      ✓ M4A
                                    </span>
                                  </div>
                                </div>
                              )}
                            </div>
                          </label>
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Microphone Volume: {micVolume}%
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={micVolume}
                      onChange={(e) => setMicVolume(parseInt(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Speaker Volume: {speakerVolume}%
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={speakerVolume}
                      onChange={(e) => setSpeakerVolume(parseInt(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-4 pt-4">
                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <div>
                        <div className="text-white font-medium">Echo Cancellation</div>
                        <div className="text-sm text-gray-400">Reduce echo in calls</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={echoCancellation}
                        onChange={(e) => setEchoCancellation(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>

                    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl cursor-pointer hover:bg-white/10 transition-colors">
                      <div>
                        <div className="text-white font-medium">Noise Suppression</div>
                        <div className="text-sm text-gray-400">Filter background noise</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={noiseSuppression}
                        onChange={(e) => setNoiseSuppression(e.target.checked)}
                        className="w-5 h-5 rounded"
                      />
                    </label>
                  </div>

                  <button
                    onClick={handleSaveAudio}
                    disabled={loading}
                    className="w-full py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-800 disabled:to-gray-900 text-white rounded-xl font-medium transition-all shadow-[0_0_40px_rgba(220,38,38,0.3)] hover:shadow-[0_0_60px_rgba(220,38,38,0.5)] border border-red-500/20 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader className="animate-spin" size={20} />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save size={20} />
                        Save Audio Settings
                      </>
                    )}
                  </button>
                </div>
              ) : null}

              {/* Danger Zone Tab */}
              {activeTab === 'danger' && (
                <div className="space-y-6">
                  <h3 className="text-2xl font-bold text-white mb-6">Danger Zone</h3>

                  <div className="p-6 bg-white/5 border-2 border-white/20 rounded-xl">
                    <h4 className="text-xl font-bold text-gray-300 mb-3 flex items-center gap-2">
                      <AlertCircle size={24} />
                      Delete Account
                    </h4>
                    <p className="text-gray-300 mb-4">
                      Once you delete your account, there is no going back. Please be certain.
                      This will permanently delete:
                    </p>
                    <ul className="text-gray-400 space-y-2 mb-6">
                      <li>• Your profile and account information</li>
                      <li>• All your meetings and recordings</li>
                      <li>• Your voice profiles</li>
                      <li>• All associated data</li>
                    </ul>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        console.log('Delete button clicked - setting modal to true');
                        setShowDeleteModal(true);
                      }}
                      className="px-6 py-3 bg-gray-800 hover:bg-gray-700 active:bg-gray-900 text-white rounded-xl font-medium transition-colors flex items-center gap-2 cursor-pointer"
                    >
                      <Trash2 size={20} />
                      Delete My Account
                    </button>
                    {showDeleteModal && (
                      <p className="mt-3 text-green-400 text-sm">✓ Modal should be visible now</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete Account Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-gradient-to-br from-gray-900 to-red-900/20 rounded-2xl p-8 max-w-md w-full border-2 border-red-500/50 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 bg-white/10 rounded-xl">
                <AlertCircle size={32} className="text-gray-300" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-white">Delete Account</h3>
                <p className="text-gray-400 text-sm">This action cannot be undone</p>
              </div>
            </div>

            <div className="space-y-4 mb-6">
              <div className="p-4 bg-white/5 border border-white/20 rounded-xl">
                <p className="text-gray-300 font-semibold mb-2">⚠️ Warning:</p>
                <p className="text-gray-300 text-sm">
                  This will <span className="font-bold text-white">permanently and irreversibly</span> delete:
                </p>
                <ul className="text-gray-400 text-sm mt-2 space-y-1">
                  <li>✗ Your account and profile</li>
                  <li>✗ All meetings and recordings</li>
                  <li>✗ All voice profiles</li>
                  <li>✗ All preferences and settings</li>
                </ul>
              </div>

              {!isOauthUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Enter your password to continue
                  </label>
                  <input
                    type="password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    className="w-full px-4 py-3 bg-black/60 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/30"
                    placeholder="Your password"
                    autoFocus
                  />
                </div>
              )}

              {isOauthUser && (
                <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                  <p className="text-blue-300 text-sm">
                    ℹ️ You signed in with OAuth (Google/GitHub). Password not required.
                  </p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Type <span className="font-bold text-gray-300">DELETE</span> to confirm
                </label>
                <input
                  type="text"
                  value={deleteConfirmation}
                  onChange={(e) => setDeleteConfirmation(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Type DELETE in capital letters"
                />
              </div>

              {error && (
                <div className="p-3 bg-white/5 border border-white/20 rounded-xl flex items-center gap-2 text-gray-300 text-sm">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeletePassword('');
                  setDeleteConfirmation('');
                  setError('');
                }}
                disabled={loading}
                className="flex-1 px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={
                  loading ||
                  deleteConfirmation.toUpperCase() !== 'DELETE' ||
                  (!isOauthUser && !deletePassword)  // Only require password for non-OAuth users
                }
                className="flex-1 px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin" size={20} />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 size={20} />
                    Delete Forever
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
