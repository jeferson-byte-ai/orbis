/**
 * useWebRTC Hook
 * Manages WebRTC connections for video/audio streaming
 */
import { useState, useEffect, useRef, useCallback } from 'react';

interface Participant {
  id: string;
  stream: MediaStream | null;
  isMuted: boolean;
  isVideoOff: boolean;
  language: string;
}

interface UseWebRTCReturn {
  localStream: MediaStream | null;
  participants: Map<string, Participant>;
  isConnected: boolean;
  isMuted: boolean;
  isVideoOff: boolean;
  error: string | null;
  toggleMute: () => Promise<void>;
  toggleVideo: () => Promise<void>;
  startCall: (roomId: string) => Promise<void>;
  endCall: () => void;
}

export const useWebRTC = (): UseWebRTCReturn => {
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [participants, setParticipants] = useState<Map<string, Participant>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const peerConnections = useRef<Map<string, RTCPeerConnection>>(new Map());
  
  // Get user media (camera + microphone)
  const getUserMedia = async (): Promise<MediaStream> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          frameRate: { ideal: 30 }
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000
        }
      });
      
      setLocalStream(stream);
      return stream;
    } catch (err) {
      const errorMsg = `Failed to access camera/microphone: ${err}`;
      setError(errorMsg);
      throw new Error(errorMsg);
    }
  };
  
  // Toggle mute/unmute
  const toggleMute = useCallback(async () => {
    if (localStream) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack && audioTrack.readyState === 'live') {
        // Track is alive, just toggle enabled
        audioTrack.enabled = !audioTrack.enabled;
        setIsMuted(!audioTrack.enabled);
        console.log('🎤 Audio toggled:', audioTrack.enabled ? 'unmuted' : 'muted');
      } else {
        // Track is dead or missing, request new audio
        console.log('🔄 Audio track dead, requesting new audio...');
        try {
          const newAudioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
              sampleRate: 48000
            }
          });
          
          // Replace audio track in existing stream
          const oldAudioTrack = localStream.getAudioTracks()[0];
          if (oldAudioTrack) {
            localStream.removeTrack(oldAudioTrack);
            oldAudioTrack.stop();
          }
          
          const newAudioTrack = newAudioStream.getAudioTracks()[0];
          localStream.addTrack(newAudioTrack);
          setIsMuted(false);
          console.log('✅ New audio track added');
        } catch (err) {
          console.error('❌ Failed to get audio:', err);
          setError('Failed to access microphone');
        }
      }
    }
  }, [localStream]);
  
  // Toggle video on/off
  const toggleVideo = useCallback(async () => {
    if (localStream) {
      const videoTrack = localStream.getVideoTracks()[0];
      if (videoTrack && videoTrack.readyState === 'live') {
        // Track is alive, just toggle enabled
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoOff(!videoTrack.enabled);
        console.log('📹 Video toggled:', videoTrack.enabled ? 'on' : 'off');
      } else {
        // Track is dead or missing, request new video
        console.log('🔄 Video track dead, requesting new video...');
        try {
          const newVideoStream = await navigator.mediaDevices.getUserMedia({
            video: {
              width: { ideal: 1920 },
              height: { ideal: 1080 },
              frameRate: { ideal: 30 }
            }
          });
          
          // Replace video track in existing stream
          const oldVideoTrack = localStream.getVideoTracks()[0];
          if (oldVideoTrack) {
            localStream.removeTrack(oldVideoTrack);
            oldVideoTrack.stop();
          }
          
          const newVideoTrack = newVideoStream.getVideoTracks()[0];
          localStream.addTrack(newVideoTrack);
          setIsVideoOff(false);
          
          // Force re-render by updating state
          setLocalStream(new MediaStream(localStream.getTracks()));
          console.log('✅ New video track added');
        } catch (err) {
          console.error('❌ Failed to get video:', err);
          setError('Failed to access camera');
        }
      }
    }
  }, [localStream]);
  
  // Start WebRTC call
  const startCall = useCallback(async (roomId: string) => {
    try {
      await getUserMedia();
      setIsConnected(true);
      setError(null);
      
      // In production, this would:
      // 1. Connect to signaling server
      // 2. Exchange SDP offers/answers
      // 3. Establish peer connections
      console.log(`Starting call in room: ${roomId}`);
      
    } catch (err) {
      setError(`Failed to start call: ${err}`);
      console.error('Call start error:', err);
    }
  }, []);
  
  // End WebRTC call
  const endCall = useCallback(() => {
    // Stop all tracks
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      setLocalStream(null);
    }
    
    // Close all peer connections
    peerConnections.current.forEach(pc => pc.close());
    peerConnections.current.clear();
    
    setParticipants(new Map());
    setIsConnected(false);
    setIsMuted(false);
    setIsVideoOff(false);
  }, [localStream]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      endCall();
    };
  }, [endCall]);
  
  return {
    localStream,
    participants,
    isConnected,
    isMuted,
    isVideoOff,
    error,
    toggleMute,
    toggleVideo,
    startCall,
    endCall
  };
};