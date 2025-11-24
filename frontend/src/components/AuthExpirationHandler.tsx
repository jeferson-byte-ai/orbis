/**
 * Auth Expiration Handler
 * Listens for token expiration events and shows notification
 */
import React, { useEffect, useState } from 'react';
import { AlertCircle } from 'lucide-react';

const AuthExpirationHandler: React.FC = () => {
  const [isExpired, setIsExpired] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const handleAuthExpired = (event: CustomEvent) => {
      setMessage(event.detail.message || 'Your session has expired. Please login again.');
      setIsExpired(true);
      
      // Hide notification after 2 seconds
      setTimeout(() => {
        setIsExpired(false);
      }, 2000);
    };

    window.addEventListener('auth:expired', handleAuthExpired as EventListener);

    return () => {
      window.removeEventListener('auth:expired', handleAuthExpired as EventListener);
    };
  }, []);

  if (!isExpired) return null;

  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-[9999] animate-slide-down">
      <div className="bg-gradient-to-r from-red-600 to-red-700 text-white px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 border border-red-500/50">
        <AlertCircle size={24} className="flex-shrink-0" />
        <div>
          <p className="font-bold text-lg">Session Expired</p>
          <p className="text-sm text-red-100">{message}</p>
        </div>
      </div>
    </div>
  );
};

export default AuthExpirationHandler;
