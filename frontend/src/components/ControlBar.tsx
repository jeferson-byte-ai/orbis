/**
 * ControlBar Component - Premium Design
 * Meeting controls (mute, video, leave, etc.)
 */
import React, { useState } from 'react';
import { Mic, MicOff, Video, VideoOff, PhoneOff, Monitor, MonitorOff, Users, Maximize, Minimize, MessageSquare, Subtitles, Waves } from 'lucide-react';

interface ControlBarProps {
  isMuted: boolean;
  isVideoOff: boolean;
  onToggleMute: () => void;
  onToggleVideo: () => void;
  onLeave: () => void;
  onEndMeeting?: () => void;
  isHost?: boolean;
  onToggleScreenShare?: () => void;
  isScreenSharing?: boolean;
  participantCount?: number;
  onToggleFullscreen?: () => void;
  isFullscreen?: boolean;
  onToggleChat?: () => void;
  isChatVisible?: boolean;
  onToggleCaptions?: () => void;
  showCaptions?: boolean;
  // Debug toggle to send raw microphone over WebRTC
  rawMicEnabled?: boolean;
  onToggleRawMic?: () => void;
}

const ControlBar: React.FC<ControlBarProps> = ({
  isMuted,
  isVideoOff,
  onToggleMute,
  onToggleVideo,
  onLeave,
  onEndMeeting,
  isHost = false,
  onToggleScreenShare,
  isScreenSharing = false,
  participantCount = 1,
  onToggleFullscreen,
  isFullscreen = false,
  onToggleChat,
  isChatVisible = true,
  onToggleCaptions,
  showCaptions = true
}) => {
  const [showEndMeetingConfirm, setShowEndMeetingConfirm] = useState(false);

  const handleEndMeeting = () => {
    if (onEndMeeting) {
      onEndMeeting();
      setShowEndMeetingConfirm(false);
    }
  };

  return (
    <>
      <div className="glass-dark px-6 py-5 border-t border-white/10">
        <div className="flex items-center justify-center gap-3">
          {/* Microphone toggle */}
          <ControlButton
            icon={isMuted ? MicOff : Mic}
            label={isMuted ? 'Unmute' : 'Mute'}
            onClick={onToggleMute}
            isActive={!isMuted}
            isDanger={isMuted}
          />

          {/* Video toggle */}
          <ControlButton
            icon={isVideoOff ? VideoOff : Video}
            label={isVideoOff ? 'Start Video' : 'Stop Video'}
            onClick={onToggleVideo}
            isActive={!isVideoOff}
            isDanger={isVideoOff}
          />

          {/* Screen share */}
          {onToggleScreenShare && (
            <ControlButton
              icon={isScreenSharing ? MonitorOff : Monitor}
              label={isScreenSharing ? 'Stop Sharing' : 'Share Screen'}
              onClick={onToggleScreenShare}
              isActive={isScreenSharing}
            />
          )}

          {/* Fullscreen */}
          {onToggleFullscreen && (
            <ControlButton
              icon={isFullscreen ? Minimize : Maximize}
              label={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
              onClick={onToggleFullscreen}
              isActive={isFullscreen}
            />
          )}

          {/* Captions toggle */}
          {onToggleCaptions && (
            <ControlButton
              icon={Subtitles}
              label={showCaptions ? 'Hide Captions' : 'Show Captions'}
              onClick={onToggleCaptions}
              isActive={showCaptions}
            />
          )}

          {/* Raw mic debug toggle */}
          {onToggleRawMic && (
            <ControlButton
              icon={Waves}
              label={rawMicEnabled ? 'Raw Mic ON' : 'Raw Mic OFF'}
              onClick={onToggleRawMic}
              isActive={!!rawMicEnabled}
            />
          )}

          {/* Chat toggle - Enhanced with visible label */}
          {(onToggleChat && (
            <div className="relative">
              <button
                onClick={onToggleChat}
                className={`rounded-full p-4 transition-all hover:scale-110 active:scale-95 relative group ${isChatVisible
                    ? 'bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-lg shadow-red-600/50'
                    : 'glass hover:bg-white/10 text-white animate-pulse'
                  }`}
                title={isChatVisible ? 'Hide Chat' : 'Show Chat'}
              >
                <MessageSquare size={24} />
                {/* Badge when chat is hidden */}
                {!isChatVisible && (
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                )}
              </button>
              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                {isChatVisible ? 'Hide Chat' : 'Show Chat'}
              </div>
              {/* Visible label when hidden */}
              {!isChatVisible && (
                <div className="absolute top-full mt-1 left-1/2 transform -translate-x-1/2 bg-red-600 text-white text-xs px-2 py-1 rounded-full whitespace-nowrap font-medium animate-bounce">
                  Show Chat
                </div>
              )}
            </div>
          ))}

          {/* Participant count */}
          <div className="glass px-4 py-3 rounded-full flex items-center gap-2">
            <Users size={20} className="text-red-400" />
            <span className="text-white font-semibold">{participantCount}</span>
          </div>

          {/* Spacer */}
          <div className="w-8" />

          {/* Leave or End Meeting button */}
          {isHost && onEndMeeting ? (
            <button
              onClick={() => setShowEndMeetingConfirm(true)}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-full px-6 py-4 transition-all shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 group font-semibold"
              title="End Meeting for All"
            >
              End Meeting
            </button>
          ) : (
            <button
              onClick={onLeave}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-full p-4 transition-all shadow-lg hover:shadow-xl hover:scale-110 active:scale-95 group"
              title="Leave Meeting"
            >
              <PhoneOff size={24} className="group-hover:rotate-12 transition-transform" />
            </button>
          )}
        </div>
      </div>

      {/* End Meeting Confirmation Modal */}
      {showEndMeetingConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowEndMeetingConfirm(false)} />
          <div className="relative bg-gradient-to-br from-gray-900 to-black border border-red-500/30 rounded-2xl p-8 max-w-md shadow-[0_0_60px_rgba(220,38,38,0.4)] animate-scale-in">
            <h3 className="text-2xl font-bold text-white mb-4">End Meeting?</h3>
            <p className="text-gray-300 mb-6">
              This will end the meeting for all participants. Everyone will be disconnected.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowEndMeetingConfirm(false)}
                className="flex-1 bg-white/10 hover:bg-white/20 text-white px-6 py-3 rounded-xl font-semibold transition-all border border-white/20"
              >
                Cancel
              </button>
              <button
                onClick={handleEndMeeting}
                className="flex-1 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white px-6 py-3 rounded-xl font-semibold transition-all shadow-[0_0_40px_rgba(220,38,38,0.3)]"
              >
                End Meeting
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

interface ControlButtonProps {
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  isActive?: boolean;
  isDanger?: boolean;
}

const ControlButton: React.FC<ControlButtonProps> = ({
  icon: Icon,
  label,
  onClick,
  isActive = false,
  isDanger = false
}) => {
  const baseClasses = "rounded-full p-4 transition-all hover:scale-110 active:scale-95 relative group";
  const colorClasses = isDanger
    ? "bg-red-600/80 hover:bg-red-600 text-white shadow-lg shadow-red-600/50"
    : isActive
      ? "bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-lg shadow-red-600/50"
      : "glass hover:bg-white/10 text-white";

  return (
    <div className="relative">
      <button
        onClick={onClick}
        className={`${baseClasses} ${colorClasses}`}
        title={label}
      >
        <Icon size={24} />
      </button>
      {/* Tooltip */}
      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
        {label}
      </div>
    </div>
  );
};

export default ControlBar;