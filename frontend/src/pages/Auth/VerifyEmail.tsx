/**
 * Email Verification Page
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [resending, setResending] = useState(false);

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token');

      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link. No token provided.');
        return;
      }

      try {
        const response = await fetch('http://localhost:8000/api/auth/verify-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Verification failed');
        }

        await response.json(); // Verify response is valid JSON
        setStatus('success');
        setMessage('Email verified successfully! Redirecting to login...');

        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } catch (error: any) {
        setStatus('error');
        setMessage(error.message || 'Failed to verify email. The link may be expired or invalid.');
      }
    };

    verifyEmail();
  }, [searchParams, navigate]);

  const handleResendVerification = async () => {
    if (!email) {
      setMessage('Please enter your email address');
      return;
    }

    setResending(true);
    try {
      const response = await fetch('http://localhost:8000/api/auth/resend-verification', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to resend verification email');
      }

      setMessage('Verification email sent! Please check your inbox (and spam folder).');
    } catch (error: any) {
      setMessage(error.message || 'Failed to resend verification email. Please try again.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <div className="max-w-md w-full mx-4">
        <div className="bg-gray-800/50 backdrop-blur-xl rounded-2xl shadow-2xl p-8 border border-gray-700">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl mx-auto mb-4 flex items-center justify-center">
              <span className="text-3xl">🌍</span>
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">
              {status === 'verifying' && 'Verifying Email...'}
              {status === 'success' && 'Email Verified!'}
              {status === 'error' && 'Verification Failed'}
            </h1>
          </div>

          {/* Status Icon */}
          <div className="text-center mb-6">
            {status === 'verifying' && (
              <div className="inline-block w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
            )}
            {status === 'success' && (
              <div className="inline-block w-16 h-16 bg-green-500 rounded-full flex items-center justify-center">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
            {status === 'error' && (
              <div className="inline-block w-16 h-16 bg-red-500 rounded-full flex items-center justify-center">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
            )}
          </div>

          {/* Message */}
          <p className={`text-center mb-6 ${status === 'success' ? 'text-green-400' :
              status === 'error' ? 'text-red-400' :
                'text-gray-300'
            }`}>
            {message}
          </p>

          {/* Actions */}
          {status === 'error' && (
            <div className="space-y-3">
              {/* Resend Verification */}
              <div className="bg-gray-700/50 rounded-lg p-4 mb-4">
                <p className="text-gray-300 text-sm mb-3">
                  Didn't receive the email or link expired? Enter your email to receive a new verification link:
                </p>
                <input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-gray-900/50 border border-gray-600 text-white px-4 py-2 rounded-lg mb-3 focus:outline-none focus:border-purple-500 transition-colors"
                />
                <button
                  onClick={handleResendVerification}
                  disabled={resending}
                  className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-3 px-4 rounded-lg font-medium hover:from-green-700 hover:to-emerald-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {resending ? 'Sending...' : 'Resend Verification Email'}
                </button>
              </div>

              <button
                onClick={() => navigate('/login')}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 px-4 rounded-lg font-medium hover:from-purple-700 hover:to-pink-700 transition-all duration-200"
              >
                Go to Login
              </button>
              <button
                onClick={() => navigate('/signup')}
                className="w-full bg-gray-700 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-600 transition-all duration-200"
              >
                Create New Account
              </button>
            </div>
          )}

          {status === 'verifying' && (
            <p className="text-center text-gray-400 text-sm">
              Please wait while we verify your email address...
            </p>
          )}

          {status === 'success' && (
            <div className="text-center">
              <p className="text-gray-400 text-sm mb-4">
                You will be redirected automatically...
              </p>
              <button
                onClick={() => navigate('/login')}
                className="text-purple-400 hover:text-purple-300 text-sm font-medium"
              >
                Click here if not redirected
              </button>
            </div>
          )}
        </div>

        {/* Back to Home */}
        <div className="text-center mt-6">
          <button
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;
