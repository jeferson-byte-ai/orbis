/**
 * Main App Component with Authentication
 */
import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Meeting from './components/Meeting';
import Home from './pages/Home';
import Login from './pages/Auth/Login';
import Signup from './pages/Auth/Signup';
import GoogleCallback from './pages/Auth/GoogleCallback';
import ForgotPassword from './pages/Auth/ForgotPassword';
import ResetPassword from './pages/Auth/ResetPassword';
import VerifyEmail from './pages/Auth/VerifyEmail';
import Settings from './pages/Settings';
import VoiceCloneOnboarding from './pages/VoiceCloneOnboarding';
import TranslationDemo from './pages/TranslationDemo';
import Terms from './pages/Terms';
import Privacy from './pages/Privacy';
import ParticleBackground from './components/ParticleBackground';
import LoadingScreen from './components/LoadingScreen';
import NotificationSystem from './components/NotificationSystem';
import AnalyticsTracker from './components/AnalyticsTracker';
import AuthExpirationHandler from './components/AuthExpirationHandler';
import { LanguageProvider } from './contexts/LanguageContext';

type AppState = 'loading' | 'home' | 'onboarding' | 'meeting';

interface MeetingData {
  roomId: string;
  token: string;
  participants?: string[];
  language?: string;
}

interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  notifications: boolean;
  analytics: boolean;
}

interface User {
  id: string;
  email: string;
  username: string;
  fullName?: string;
  isOauthUser?: boolean;  // True if user logged in via OAuth
}

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>('loading');
  const [meetingData, setMeetingData] = useState<MeetingData | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [userPreferences, setUserPreferences] = useState<UserPreferences>({
    theme: 'auto',
    language: 'en',
    notifications: true,
    analytics: true
  });
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // Initialize app
  useEffect(() => {
    initializeApp();
    setupEventListeners();
  }, []);

  const initializeApp = async () => {
    try {
      // Load user preferences
      const savedPreferences = localStorage.getItem('orbis_preferences');
      if (savedPreferences) {
        setUserPreferences(JSON.parse(savedPreferences));
      }

      // Check for saved auth
      const savedToken = localStorage.getItem('auth_token');
      const savedUser = localStorage.getItem('user');

      if (savedToken && savedUser) {
        setAuthToken(savedToken);
        setUser(JSON.parse(savedUser));
      }

      // Simulate loading time for better UX
      await new Promise(resolve => setTimeout(resolve, 1500));

      setAppState('home');
    } catch (error) {
      console.error('Failed to initialize app:', error);
      setAppState('home');
    }
  };

  const setupEventListeners = () => {
    // Online/offline detection
    window.addEventListener('online', () => setIsOnline(true));
    window.addEventListener('offline', () => setIsOnline(false));

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
  };

  const handleKeyboardShortcuts = (event: KeyboardEvent) => {
    // Ctrl/Cmd + K for quick meeting join
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
      event.preventDefault();
      const joinInput = document.querySelector('[data-join-meeting]') as HTMLInputElement;
      if (joinInput) {
        joinInput.focus();
      }
    }

    // Escape to leave meeting
    if (event.key === 'Escape' && appState === 'meeting') {
      handleLeaveMeeting();
    }
  };

  const handleLogin = async (email: string, password: string) => {
    try {
      // Use apiFetch to automatically add ngrok headers
      const { apiFetch } = await import('./utils/api');

      const response = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Invalid credentials');
      }

      const data = await response.json();

      // Save auth data
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      setAuthToken(data.access_token);
      setUser(data.user);

      // Track analytics
      if (userPreferences.analytics) {
        AnalyticsTracker.getInstance().track('user_login', {
          userId: data.user.id,
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const handleSignup = async (email: string, username: string, password: string, fullName?: string) => {
    try {
      // Use apiFetch to automatically add ngrok headers
      const { apiFetch } = await import('./utils/api');

      // Call signup endpoint
      const response = await apiFetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password, full_name: fullName })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Signup failed');
      }

      // User created successfully, now login
      const loginResponse = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!loginResponse.ok) {
        throw new Error('Auto-login failed');
      }

      const data = await loginResponse.json();

      // Save auth data
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      setAuthToken(data.access_token);
      setUser(data.user);

      // Track analytics
      if (userPreferences.analytics) {
        AnalyticsTracker.getInstance().track('user_signup', {
          userId: data.user.id,
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error('Signup failed:', error);
      throw error;
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    setAuthToken(null);
    setUser(null);
    setAppState('home');
    setMeetingData(null);
  };

  const handleJoinMeeting = (roomId: string, token: string, participants?: string[], language?: string) => {
    setMeetingData({ roomId, token, participants, language });

    // Track analytics
    if (userPreferences.analytics) {
      AnalyticsTracker.getInstance().track('meeting_join_attempted', {
        roomId,
        hasVoiceProfile: localStorage.getItem('hasVoiceProfile') === 'true',
        timestamp: new Date().toISOString()
      });
    }

    const hasVoiceProfile = localStorage.getItem('hasVoiceProfile') === 'true';
    if (!hasVoiceProfile) {
      setAppState('onboarding');
    } else {
      setAppState('meeting');
    }
  };

  const handleOnboardingComplete = () => {
    localStorage.setItem('hasVoiceProfile', 'true');

    if (userPreferences.analytics) {
      AnalyticsTracker.getInstance().track('voice_profile_created', {
        timestamp: new Date().toISOString()
      });
    }

    setAppState('meeting');
  };

  const handleLeaveMeeting = () => {
    if (userPreferences.analytics && meetingData) {
      AnalyticsTracker.getInstance().track('meeting_left', {
        roomId: meetingData.roomId,
        timestamp: new Date().toISOString()
      });
    }

    setAppState('home');
    setMeetingData(null);
  };

  const updateUserPreferences = (newPreferences: Partial<UserPreferences>) => {
    const updated = { ...userPreferences, ...newPreferences };
    setUserPreferences(updated);
    localStorage.setItem('orbis_preferences', JSON.stringify(updated));
  };

  // Show loading screen
  if (appState === 'loading') {
    return <LoadingScreen />;
  }

  return (
    <LanguageProvider>
      <BrowserRouter>
        <div className="app" data-theme={userPreferences.theme}>
          {/* Auth Expiration Handler */}
          <AuthExpirationHandler />

          {/* Particle Background */}
          <ParticleBackground />

          {/* Connection Status Indicators */}
          {!isOnline && (
            <div className="fixed top-4 right-4 z-50 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                <span>Offline</span>
              </div>
            </div>
          )}

          {/* Notification System */}
          <NotificationSystem />

          {/* Routes */}
          <div className="relative z-10">
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={
                user ? <Navigate to="/" /> : <Login onLogin={handleLogin} />
              } />
              <Route path="/signup" element={
                user ? <Navigate to="/" /> : <Signup onSignup={handleSignup} />
              } />

              {/* OAuth Callback Routes */}
              <Route path="/auth/google/callback" element={<GoogleCallback />} />

              {/* Email Verification Route */}
              <Route path="/verify-email" element={<VerifyEmail />} />

              {/* Translation Demo Route */}
              <Route path="/description" element={<TranslationDemo />} />

              {/* Password Reset Routes */}
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />

              {/* Legal Pages */}
              <Route path="/terms" element={<Terms />} />
              <Route path="/privacy" element={<Privacy />} />

              {/* Settings Route (Protected) */}
              <Route path="/settings" element={
                user ? (
                  <Settings
                    user={user}
                    onUpdateProfile={async (data) => {
                      const { apiFetch } = await import('./utils/api');
                      const response = await apiFetch('/api/users/me/profile', {
                        method: 'PUT',
                        headers: {
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify(data)
                      });
                      if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to update profile');
                      }
                      const updatedUser = await response.json();
                      setUser(updatedUser);
                      localStorage.setItem('user', JSON.stringify(updatedUser));
                    }}
                    onChangePassword={async (current, newPass) => {
                      const { apiFetch } = await import('./utils/api');
                      const response = await apiFetch('/api/users/me/change-password', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify({
                          current_password: current,
                          new_password: newPass
                        })
                      });
                      if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to change password');
                      }
                    }}
                    onDeleteAccount={async (password: string, confirmation: string) => {
                      console.log('🔑 Token in delete request:', authToken ? `${authToken.substring(0, 20)}...` : 'NULL');
                      console.log('📝 Delete request body:', { password: password ? '***' : 'empty', confirmation });

                      const { apiFetch } = await import('./utils/api');
                      const response = await apiFetch('/api/users/me', {
                        method: 'DELETE',
                        headers: {
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify({ password, confirmation })
                      });

                      console.log('📬 Response status:', response.status);

                      if (!response.ok) {
                        const error = await response.json();
                        console.error('❌ Delete error response:', error);

                        // Check if token expired
                        if (response.status === 401) {
                          // Auto logout if session expired
                          handleLogout();
                          throw new Error('Your session has expired. Please login again to delete your account.');
                        }

                        throw new Error(error.detail || 'Failed to delete account');
                      }
                      handleLogout();
                    }}
                    onUpdatePreferences={async (preferences: any) => {
                      const { apiFetch } = await import('./utils/api');
                      const response = await apiFetch('/api/users/me/preferences/all', {
                        method: 'PUT',
                        headers: {
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${authToken}`
                        },
                        body: JSON.stringify(preferences)
                      });
                      if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to update preferences');
                      }
                      const result = await response.json();
                      // Update user with new preferences
                      const updatedUser = { ...user, preferences: result.preferences };
                      setUser(updatedUser);
                      localStorage.setItem('user', JSON.stringify(updatedUser));
                    }}
                    onLogout={handleLogout}
                  />
                ) : (
                  <Navigate to="/login" />
                )
              } />

              {/* Protected Routes */}
              <Route path="/" element={
                appState === 'meeting' && meetingData ? (
                  <Meeting
                    roomId={meetingData.roomId}
                    token={meetingData.token}
                    participants={meetingData.participants}
                    language={meetingData.language}
                    onLeave={handleLeaveMeeting}
                    userPreferences={userPreferences}
                  />
                ) : appState === 'onboarding' && meetingData ? (
                  <VoiceCloneOnboarding
                    onComplete={handleOnboardingComplete}
                    onSkip={() => setAppState('meeting')}
                    userPreferences={userPreferences}
                  />
                ) : (
                  <Home
                    onJoinMeeting={handleJoinMeeting}
                    userPreferences={userPreferences}
                    onUpdatePreferences={updateUserPreferences}
                    user={user}
                    onLogout={handleLogout}
                  />
                )
              } />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </LanguageProvider>
  );
};

export default App;
