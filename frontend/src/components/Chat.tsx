/**
 * Chat Component - Modern Premium Interface
 * Real-time chat with translation features
 */
import React, { useState, useEffect, useRef } from 'react';
import { Send, Languages, X, Loader2, Check, Sparkles, Zap } from 'lucide-react';
import { apiFetch } from '../utils/api';
import { buildBackendWebSocketUrl } from '../utils/websocket';

interface ChatMessage {
  id: string;
  room_id: string;
  user_id: string;
  user_name: string;
  user_avatar: string | null;
  content: string;
  language: string | null;
  created_at: string;
  translated?: string;
  translating?: boolean;
}

interface ChatProps {
  roomId: string;
  token: string;
  userName: string;
  currentUserId: string;
  targetLanguage: string; // User's preferred language for translation
  onClose?: () => void;
  isVisible?: boolean;
  isFullscreen?: boolean;
}

const normalizeLanguageCode = (code?: string | null): string | null => {
  if (!code) return null;
  const cleaned = code.toLowerCase().replace('_', '-');
  if (cleaned === 'auto') return null;
  return cleaned.split('-')[0];
};

const detectProbableLanguage = (text: string): string | null => {
  const lower = text.toLowerCase();
  if (/[ãõâêôáéíóúç]/.test(lower) || lower.includes(' você') || lower.includes(' que ')) {
    return 'pt';
  }
  if (/[ñáéíóú¡¿]/.test(lower)) {
    return 'es';
  }
  return null;
};

const Chat: React.FC<ChatProps> = ({
  roomId,
  token,
  userName,
  currentUserId,
  targetLanguage,
  onClose,
  isVisible = true,
  isFullscreen = false
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [ws, setWs] = useState<WebSocket | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageBoxRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load initial messages
  useEffect(() => {
    const loadMessages = async () => {
      try {
        const response = await apiFetch(
          `/api/chat/messages/${roomId}?limit=100`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );

        if (response.ok) {
          const data = await response.json();
          setMessages(data);
        }
      } catch (error) {
        console.error('Error loading messages:', error);
      } finally {
        setLoading(false);
      }
    };

    loadMessages();
  }, [roomId, token]);

  // Connect to WebSocket for real-time messages
  useEffect(() => {
    const wsUrl = buildBackendWebSocketUrl(`/api/chat/ws/${roomId}`);

    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('Chat WebSocket connected');
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'new_message') {
        setMessages(prev => [...prev, data.message]);
      }
    };

    websocket.onerror = (error) => {
      console.error('Chat WebSocket error:', error);
    };

    websocket.onclose = () => {
      console.log('Chat WebSocket disconnected');
    };

    setWs(websocket);

    // Ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      websocket.close();
    };
  }, [roomId]);

  // Send message
  const handleSendMessage = async () => {
    if (!newMessage.trim() || sending) return;

    setSending(true);
    const messageContent = newMessage.trim();
    const tempId = `temp-${Date.now()}`;

    // Add message optimistically (immediate feedback)
    const optimisticMessage: ChatMessage = {
      id: tempId,
      room_id: roomId,
      user_id: currentUserId,
      user_name: userName,
      user_avatar: null,
      content: messageContent,
      language: null,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, optimisticMessage]);
    setNewMessage('');

    try {
      const response = await apiFetch('/api/chat/messages', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          room_id: roomId,
          content: messageContent,
          language: null // Auto-detect
        })
      });

      if (response.ok) {
        const data = await response.json();
        // Replace temp message with real one from server
        setMessages(prev => prev.map(msg =>
          msg.id === tempId ? data : msg
        ));
      } else {
        console.error('Error sending message');
        // Remove optimistic message on error
        setMessages(prev => prev.filter(msg => msg.id !== tempId));
        setNewMessage(messageContent); // Restore message
      }
    } catch (error) {
      console.error('Error sending message:', error);
      // Remove optimistic message on error
      setMessages(prev => prev.filter(msg => msg.id !== tempId));
      setNewMessage(messageContent); // Restore message
    } finally {
      setSending(false);
    }
  };

  // Translate a single message
  const translateMessage = async (message: ChatMessage) => {
    const rawTarget = targetLanguage?.toLowerCase();
    const normalizedTarget = normalizeLanguageCode(targetLanguage) || (rawTarget && rawTarget !== 'auto' ? rawTarget : 'en');
    const sourceCandidate = normalizeLanguageCode(message.language) || detectProbableLanguage(message.content) || (normalizedTarget === 'en' ? 'pt' : 'en');

    if (sourceCandidate === normalizedTarget) {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === message.id
            ? { ...msg, translated: message.content, translating: false }
            : msg
        )
      );
      return;
    }

    // Mark message as translating
    setMessages(prev =>
      prev.map(msg =>
        msg.id === message.id ? { ...msg, translating: true } : msg
      )
    );

    try {
      const response = await apiFetch('/api/chat/translate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: message.content,
          source_language: sourceCandidate,
          target_language: normalizedTarget
        })
      });

      if (!response.ok) {
        throw new Error(`Translation failed with status ${response.status}`);
      }

      const data = await response.json();
      const translatedText = data.translated_text || data.data?.translated_text;
      const resolvedSource = data.source_language || sourceCandidate;

      setMessages(prev =>
        prev.map(msg =>
          msg.id === message.id
            ? {
              ...msg,
              translating: false,
              translated: translatedText || message.content,
              language: msg.language ?? resolvedSource
            }
            : msg
        )
      );
    } catch (error) {
      console.error('Error translating message:', error);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === message.id ? { ...msg, translating: false } : msg
        )
      );
    }
  };


  // Handle Enter key
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isVisible) return null;

  return (
    <div data-chat-panel className={`h-full bg-gradient-to-b from-gray-950 via-black to-gray-950 border-l border-white/10 flex flex-col shadow-2xl relative overflow-hidden rounded-l-3xl ${isFullscreen ? 'pb-24' : ''
      }`}>
      {/* Animated background effects */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
        <div className="absolute top-0 right-0 w-64 h-64 bg-red-500 rounded-full mix-blend-screen filter blur-3xl animate-pulse" style={{ animationDuration: '4s' }} />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500 rounded-full mix-blend-screen filter blur-3xl animate-pulse" style={{ animationDuration: '6s', animationDelay: '2s' }} />
      </div>

      {/* Header */}
      <div className="relative z-10 bg-gradient-to-r from-red-950/30 via-black/50 to-purple-950/30 backdrop-blur-xl px-4 py-4 border-b border-white/10 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="absolute inset-0 bg-red-500 rounded-full blur-md animate-pulse" />
              <div className="relative w-10 h-10 bg-gradient-to-br from-red-600 to-red-800 rounded-xl flex items-center justify-center shadow-lg">
                <Sparkles size={20} className="text-white" />
              </div>
            </div>
            <div>
              <h3 className="text-white font-bold text-lg flex items-center gap-2">
                Live Chat
                <span className="px-2 py-0.5 bg-red-500/20 border border-red-500/30 rounded-full text-xs font-medium text-red-400">
                  {messages.length}
                </span>
              </h3>
              <p className="text-gray-400 text-xs flex items-center gap-1">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                Connected
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Close Button */}
            {onClose && (
              <button
                onClick={onClose}
                className="group relative p-2.5 hover:bg-white/10 rounded-2xl transition-all hover:scale-110 active:scale-95"
                title="Hide chat"
              >
                <X size={18} className="text-gray-400 group-hover:text-white transition-colors" />
                <div className="absolute inset-0 bg-white/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity blur-sm" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div
        ref={messageBoxRef}
        className="relative z-10 flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-red-500/50 scrollbar-track-transparent hover:scrollbar-thumb-red-500/70"
      >
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-red-500 blur-xl animate-pulse" />
              <Loader2 size={48} className="relative text-red-400 animate-spin" />
            </div>
            <p className="text-gray-400 font-medium">Loading messages...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-red-500 rounded-full blur-2xl opacity-30" />
              <div className="relative w-20 h-20 bg-gradient-to-br from-red-600/20 to-purple-600/20 rounded-2xl flex items-center justify-center border border-white/10">
                <Sparkles size={32} className="text-red-400" />
              </div>
            </div>
            <div className="text-center">
              <p className="text-gray-400 font-medium mb-1">No messages yet</p>
              <p className="text-gray-600 text-sm">Be the first to say something!</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => {
            const isCurrentUser = message.user_id === currentUserId;
            const isNewMessage = index === messages.length - 1;

            return (
              <div
                key={message.id}
                className={`flex ${isCurrentUser ? 'justify-end' : 'justify-start'} animate-slide-up`}
                style={{ animationDelay: isNewMessage ? '0ms' : `${index * 50}ms` }}
              >
                <div className={`max-w-[80%] ${isCurrentUser ? 'items-end' : 'items-start'} flex flex-col gap-1.5 group`}>
                  {/* User name with avatar */}
                  <div className={`flex items-center gap-2 px-2 ${isCurrentUser ? 'flex-row-reverse' : 'flex-row'}`}>
                    {!isCurrentUser && (
                      <div className="w-6 h-6 bg-gradient-to-br from-purple-600 to-purple-800 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg">
                        {message.user_name.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <span className={`text-xs font-medium ${isCurrentUser ? 'text-red-400' : 'text-purple-400'}`}>
                      {message.user_name}
                    </span>
                  </div>

                  {/* Message bubble */}
                  <div className="relative">
                    {/* Glow effect */}
                    <div className={`absolute inset-0 ${isCurrentUser ? 'bg-red-500' : 'bg-purple-500'} rounded-2xl blur-lg opacity-0 group-hover:opacity-30 transition-opacity`} />

                    <div
                      className={`relative px-5 py-3 rounded-3xl backdrop-blur-sm border transition-all group-hover:scale-[1.02] ${isCurrentUser
                        ? 'bg-gradient-to-br from-red-600 to-red-700 text-white rounded-br-lg border-red-500/30 shadow-lg shadow-red-500/20'
                        : 'bg-gradient-to-br from-gray-800 to-gray-900 text-white rounded-bl-lg border-white/10 shadow-lg'
                        }`}
                    >
                      <p className="text-sm leading-relaxed break-words whitespace-pre-wrap">
                        {message.content}
                      </p>
                    </div>
                  </div>

                  {/* Translated text */}
                  {message.translated && (
                    <div className="relative px-4 py-3 bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-3xl rounded-tl-lg border border-blue-500/30 backdrop-blur-sm">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Zap size={12} className="text-blue-400" />
                        <p className="text-xs text-blue-300 font-medium">AI Translated</p>
                      </div>
                      <p className="text-sm text-white leading-relaxed break-words whitespace-pre-wrap">
                        {message.translated}
                      </p>
                    </div>
                  )}

                  {/* Translate button (only for other users' messages) */}
                  {!isCurrentUser && !message.translated && (
                    <button
                      onClick={() => translateMessage(message)}
                      disabled={message.translating}
                      className="group/btn relative text-xs px-3 py-1.5 rounded-full bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30 hover:border-purple-400/50 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-1.5"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-full opacity-0 group-hover/btn:opacity-100 transition-opacity blur-sm" />
                      {message.translating ? (
                        <>
                          <Loader2 size={12} className="animate-spin text-purple-400" />
                          <span className="text-purple-300 font-medium">Translating...</span>
                        </>
                      ) : (
                        <>
                          <Languages size={12} className="text-purple-400 group-hover/btn:text-purple-300 transition-colors" />
                          <span className="text-purple-400 group-hover/btn:text-purple-300 font-medium transition-colors">Translate</span>
                        </>
                      )}
                    </button>
                  )}

                  {/* Timestamp */}
                  <div className={`flex items-center gap-1.5 px-2 ${isCurrentUser ? 'flex-row-reverse' : 'flex-row'}`}>
                    <span className="text-xs text-gray-500">
                      {new Date(message.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                    {isCurrentUser && (
                      <Check size={12} className="text-red-400" />
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className={`relative z-10 bg-gradient-to-r from-gray-900/50 via-black/50 to-gray-900/50 backdrop-blur-xl border-t border-white/10 p-4 ${isFullscreen ? 'rounded-bl-3xl' : ''
        }`}>
        <div className="flex gap-3">
          <div className="flex-1 relative group">
            {/* Glow effect */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-purple-500 rounded-3xl opacity-0 group-focus-within:opacity-30 blur transition-opacity" />

            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="relative w-full bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm border border-white/20 text-white px-5 py-3 rounded-3xl focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 resize-none placeholder-gray-500 transition-all"
              rows={1}
              disabled={sending}
            />
          </div>

          <button
            onClick={handleSendMessage}
            disabled={!newMessage.trim() || sending}
            className="group relative bg-gradient-to-br from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-700 disabled:to-gray-800 disabled:opacity-50 text-white p-4 rounded-3xl transition-all hover:scale-110 active:scale-95 disabled:hover:scale-100 shadow-lg disabled:shadow-none"
          >
            {/* Glow effect */}
            <div className="absolute inset-0 bg-red-500 rounded-3xl opacity-0 group-hover:opacity-50 blur-xl transition-opacity" />

            {sending ? (
              <Loader2 size={22} className="relative animate-spin" />
            ) : (
              <Send size={22} className="relative group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            )}
          </button>
        </div>

        {/* Typing indicator placeholder */}
        <div className="mt-2 h-4 flex items-center px-2">
          {sending && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="font-medium">Sending...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Chat;
