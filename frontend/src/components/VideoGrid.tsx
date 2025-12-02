/**
 * VideoGrid Component - Premium Design
 * Displays video streams in a responsive grid layout
 */
import React, { useEffect, useRef, useState } from 'react';
import { User, MicOff, VideoOff, Volume2, Maximize2 } from 'lucide-react';

interface Participant {
  id: string;
  stream: MediaStream | null;
  isMuted: boolean;
  isVideoOff: boolean;
  language: string;
  userName?: string;
}

interface VideoGridProps {
  localStream: MediaStream | null;
  participants: Map<string, Participant>;
  isMuted: boolean;
  isVideoOff: boolean;
  userName?: string;
}

const VideoGrid: React.FC<VideoGridProps> = ({ localStream, participants, isMuted, isVideoOff, userName }) => {
  const localVideoRef = useRef<HTMLVideoElement>(null);
  
  // Ensure the local video element always has the correct stream attached
  useEffect(() => {
    const videoElement = localVideoRef.current;
    if (!videoElement) return;

    if (!localStream) {
      videoElement.srcObject = null;
      return;
    }

    if (videoElement.srcObject !== localStream) {
      videoElement.srcObject = localStream;
    }

    if (!isVideoOff) {
      videoElement.play().catch(err => {
        console.warn('Video autoplay warning:', err);
      });
    }
  }, [localStream, isVideoOff]);
  
  const participantCount = participants.size + 1; // +1 for local user
  
  // Calculate grid layout based on participant count
  const getGridClass = () => {
    if (participantCount === 1) return 'grid-cols-1 grid-rows-1';
    if (participantCount === 2) return 'grid-cols-2 grid-rows-1';
    if (participantCount <= 4) return 'grid-cols-2 grid-rows-2';
    if (participantCount <= 6) return 'grid-cols-3 grid-rows-2';
    return 'grid-cols-3 grid-rows-3';
  };
  
  return (
    <div className={`h-full w-full grid ${getGridClass()} gap-4 p-6 overflow-auto`}>
      {/* Local video */}
      <VideoTile
        videoRef={localVideoRef}
        isLocal
        isMuted={isMuted}
        isVideoOff={isVideoOff}
        label="You"
        userName={userName}
      />
      
      {/* Remote participants */}
      {Array.from(participants.values()).map((participant) => (
        <ParticipantVideo
          key={participant.id}
          participant={participant}
        />
      ))}
    </div>
  );
};

interface VideoTileProps {
  videoRef?: React.RefObject<HTMLVideoElement>;
  isLocal?: boolean;
  isMuted: boolean;
  isVideoOff: boolean;
  label: string;
  userName?: string;
}

const VideoTile: React.FC<VideoTileProps> = ({ 
  videoRef, 
  isLocal = false, 
  isMuted, 
  isVideoOff, 
  label,
  userName
}) => {
  const [isHovered, setIsHovered] = useState(false);
  
  // Get initial from userName or label
  const getInitial = () => {
    const name = userName || label;
    return name.charAt(0).toUpperCase();
  };
  
  return (
    <div 
      className="relative bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl overflow-hidden h-full w-full shadow-xl border border-white/10 hover:border-white/20 transition-all group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Video element */}
      {!isVideoOff ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={isLocal}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center relative">
          {/* Gradient background */}
          <div className="absolute inset-0 bg-gradient-to-br from-gray-900 to-black" />
          <div className="bg-gradient-to-br from-red-600 to-red-700 rounded-full w-32 h-32 flex items-center justify-center shadow-2xl relative z-10 border-4 border-red-500/30">
            <span className="text-white text-5xl font-bold">{getInitial()}</span>
          </div>
        </div>
      )}
      
      {/* Top controls - shown on hover */}
      {isHovered && !isLocal && (
        <div className="absolute top-3 right-3 flex gap-2 animate-fade-in">
          <button className="glass p-2 rounded-lg hover:bg-white/20 transition-colors">
            <Maximize2 size={16} className="text-white" />
          </button>
        </div>
      )}
      
      {/* Overlay with participant info */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-4 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-white font-semibold text-lg">{label}</span>
            {isLocal && (
              <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full font-medium">You</span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {!isMuted && !isLocal && (
              <div className="glass p-1.5 rounded-lg animate-pulse">
                <Volume2 size={16} className="text-red-400" />
              </div>
            )}
            {isMuted && (
              <div className="bg-red-500/90 backdrop-blur-sm rounded-lg p-1.5 shadow-lg">
                <MicOff size={16} className="text-white" />
              </div>
            )}
            {isVideoOff && (
              <div className="bg-red-500/90 backdrop-blur-sm rounded-lg p-1.5 shadow-lg">
                <VideoOff size={16} className="text-white" />
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Border glow effect when speaking (could be tied to audio level) */}
      {!isMuted && (
        <div className="absolute inset-0 border-2 border-red-400/50 rounded-2xl animate-pulse pointer-events-none" />
      )}
    </div>
  );
};

interface ParticipantVideoProps {
  participant: Participant;
}

const ParticipantVideo: React.FC<ParticipantVideoProps> = ({ participant }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  useEffect(() => {
    if (videoRef.current && participant.stream) {
      videoRef.current.srcObject = participant.stream;
    }
  }, [participant.stream]);
  
  return (
    <VideoTile
      videoRef={videoRef}
      isMuted={participant.isMuted}
      isVideoOff={participant.isVideoOff}
      label={participant.userName || `Participant ${participant.id.substring(0, 6)}`}
      userName={participant.userName}
    />
  );
};

export default VideoGrid;