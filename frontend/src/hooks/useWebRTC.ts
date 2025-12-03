/**
 * useWebRTC Hook
 * Manages WebRTC connections for video/audio streaming with signaling
 */
import { useState, useEffect, useRef, useCallback } from 'react';

interface Participant {
  id: string;
  stream: MediaStream | null;
  isMuted: boolean;
  isVideoOff: boolean;
  language: string;
  userName?: string;
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
  startCall: (roomId: string, signalingWs: WebSocket) => Promise<void>;
  endCall: () => void;
  signalingConnected: boolean;
  handleSignalingMessage: (data: any) => Promise<void>;
}

// ICE servers for STUN/TURN
const ICE_SERVERS = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
    { urls: 'stun:stun2.l.google.com:19302' },
  ]
};

export const useWebRTC = (): UseWebRTCReturn => {
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [participants, setParticipants] = useState<Map<string, Participant>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [signalingConnected, setSignalingConnected] = useState(false);

  const peerConnections = useRef<Map<string, RTCPeerConnection>>(new Map());
  const signalingWs = useRef<WebSocket | null>(null);
  const currentUserId = useRef<string | null>(null);
  const roomId = useRef<string | null>(null);

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

  // Create peer connection for a remote user
  const createPeerConnection = useCallback((remoteUserId: string): RTCPeerConnection => {
    console.log('🔗 Creating peer connection for:', remoteUserId);
    console.log('📹 Current localStream status:', localStream ? `Ready with ${localStream.getTracks().length} tracks` : 'NOT READY');

    const pc = new RTCPeerConnection(ICE_SERVERS);

    // Add local stream tracks to peer connection
    if (localStream) {
      localStream.getTracks().forEach(track => {
        pc.addTrack(track, localStream);
        console.log('➕ Added local track:', track.kind, 'to', remoteUserId);
      });
    } else {
      console.warn('⚠️ Creating peer connection WITHOUT local stream tracks!');
      console.warn('   This will be fixed when localStream becomes available');
    }

    // Handle incoming remote stream
    pc.ontrack = (event) => {
      console.log('📥 Received remote track:', event.track.kind, 'from:', remoteUserId);
      const remoteStream = event.streams[0];

      setParticipants(prev => {
        const updated = new Map(prev);
        const existing = updated.get(remoteUserId);
        updated.set(remoteUserId, {
          id: remoteUserId,
          stream: remoteStream,
          isMuted: false,
          isVideoOff: false,
          language: 'en',
          userName: existing?.userName
        });
        return updated;
      });
    };

    // Handle ICE candidates
    pc.onicecandidate = (event) => {
      if (event.candidate && signalingWs.current?.readyState === WebSocket.OPEN) {
        console.log('🧊 Sending ICE candidate to:', remoteUserId);
        signalingWs.current.send(JSON.stringify({
          type: 'ice_candidate',
          target_user_id: remoteUserId,
          candidate: event.candidate
        }));
      }
    };

    // Handle connection state changes
    pc.onconnectionstatechange = () => {
      console.log(`🔌 Connection state with ${remoteUserId}:`, pc.connectionState);
      if (pc.connectionState === 'connected') {
        console.log('✅ WebRTC connected to:', remoteUserId);
      } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
        console.log('❌ WebRTC connection failed/disconnected:', remoteUserId);
      }
    };

    pc.oniceconnectionstatechange = () => {
      console.log(`❄️ ICE state with ${remoteUserId}:`, pc.iceConnectionState);
    };

    // Handle negotiation needed (for adding tracks later)
    pc.onnegotiationneeded = async () => {
      console.log(`🔄 Negotiation needed with ${remoteUserId}`);
      try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        if (signalingWs.current?.readyState === WebSocket.OPEN) {
          signalingWs.current.send(JSON.stringify({
            type: 'webrtc_offer',
            target_user_id: remoteUserId,
            offer: offer
          }));
          console.log(`📤 Sent renegotiation offer to ${remoteUserId}`);
        }
      } catch (err) {
        console.error(`❌ Negotiation failed with ${remoteUserId}:`, err);
      }
    };

    peerConnections.current.set(remoteUserId, pc);
    return pc;
  }, [localStream]);

  // Handle signaling messages - exposed for external WebSocket
  const handleSignalingMessage = useCallback(async (data: any) => {
    const messageType = data.type;

    try {
      if (messageType === 'connected') {
        currentUserId.current = data.user_id;
        console.log('👤 Our user ID:', currentUserId.current);
        setSignalingConnected(true);
        return;
      }

      if (messageType === 'webrtc_offer') {
        const fromUserId = data.from_user_id;
        const offer = data.offer;

        console.log('📨 Received WebRTC offer from:', fromUserId);

        // Create peer connection if it doesn't exist
        let pc = peerConnections.current.get(fromUserId);
        if (!pc) {
          pc = createPeerConnection(fromUserId);
        }

        // Set remote description
        await pc.setRemoteDescription(new RTCSessionDescription(offer));

        // Create and send answer
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        if (signalingWs.current?.readyState === WebSocket.OPEN) {
          signalingWs.current.send(JSON.stringify({
            type: 'webrtc_answer',
            target_user_id: fromUserId,
            answer: answer
          }));
          console.log('📤 Sent WebRTC answer to:', fromUserId);
        }
      }
      else if (messageType === 'webrtc_answer') {
        const fromUserId = data.from_user_id;
        const answer = data.answer;

        console.log('📨 Received WebRTC answer from:', fromUserId);

        const pc = peerConnections.current.get(fromUserId);
        if (pc) {
          await pc.setRemoteDescription(new RTCSessionDescription(answer));
          console.log('✅ Set remote description for:', fromUserId);
        }
      }
      else if (messageType === 'ice_candidate') {
        const fromUserId = data.from_user_id;
        const candidate = data.candidate;

        console.log('🧊 Received ICE candidate from:', fromUserId);

        const pc = peerConnections.current.get(fromUserId);
        if (pc) {
          await pc.addIceCandidate(new RTCIceCandidate(candidate));
        }
      }
      else if (messageType === 'participant_joined') {
        const joinedUserId = data.user_id;

        // Don't create connection to ourselves
        if (joinedUserId === currentUserId.current) {
          console.log('👤 Ignoring self join');
          return;
        }

        console.log('👋 Participant joined, creating offer for:', joinedUserId, 'Has localStream:', !!localStream);

        // Create peer connection and send offer
        const pc = createPeerConnection(joinedUserId);

        // Create and send offer
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        if (signalingWs.current?.readyState === WebSocket.OPEN) {
          signalingWs.current.send(JSON.stringify({
            type: 'webrtc_offer',
            target_user_id: joinedUserId,
            offer: offer
          }));
          console.log('📤 Sent WebRTC offer to:', joinedUserId);
        }
      }
      else if (messageType === 'participant_left') {
        const leftUserId = data.user_id;
        console.log('👋 Participant left:', leftUserId);

        // Close peer connection
        const pc = peerConnections.current.get(leftUserId);
        if (pc) {
          pc.close();
          peerConnections.current.delete(leftUserId);
        }

        // Remove from participants
        setParticipants(prev => {
          const updated = new Map(prev);
          updated.delete(leftUserId);
          return updated;
        });
      }
    } catch (err) {
      console.error('Error handling signaling message:', err);
    }
  }, [createPeerConnection]);

  // Start WebRTC call - now uses existing WebSocket
  const startCall = useCallback(async (roomIdParam: string, existingWs: WebSocket) => {
    try {
      console.log('🚀 Starting WebRTC call in room:', roomIdParam);
      roomId.current = roomIdParam;

      // Get local media first
      const stream = await getUserMedia();
      setIsConnected(true);
      setError(null);

      // Use the existing WebSocket for signaling (shared with translation)
      signalingWs.current = existingWs;

      console.log('✅ WebRTC using shared WebSocket for signaling');
      console.log('📹 Local stream ready with tracks:', stream.getTracks().map(t => t.kind).join(', '));

      // Add tracks to any existing peer connections that were created before localStream was ready
      console.log('🔄 Checking for existing peer connections to add tracks to...');
      peerConnections.current.forEach((pc, userId) => {
        const senders = pc.getSenders();
        console.log(`👤 Peer ${userId} has ${senders.length} senders`);
        
        // Check if this peer connection has any tracks
        if (senders.length === 0) {
          console.log(`➕ Adding tracks to existing peer connection for ${userId}`);
          stream.getTracks().forEach(track => {
            pc.addTrack(track, stream);
            console.log(`  ✅ Added ${track.kind} track to ${userId}`);
          });

          // Renegotiate by creating a new offer
          console.log(`🔄 Renegotiating connection with ${userId}...`);
          pc.createOffer()
            .then(offer => pc.setLocalDescription(offer))
            .then(() => {
              if (signalingWs.current?.readyState === WebSocket.OPEN) {
                signalingWs.current.send(JSON.stringify({
                  type: 'webrtc_offer',
                  target_user_id: userId,
                  offer: pc.localDescription
                }));
                console.log(`📤 Sent renegotiation offer to ${userId}`);
              }
            })
            .catch(err => {
              console.error(`❌ Failed to renegotiate with ${userId}:`, err);
            });
        }
      });

    } catch (err) {
      setError(`Failed to start call: ${err}`);
      console.error('Call start error:', err);
    }
  }, [getUserMedia]);

  // End WebRTC call
  const endCall = useCallback(() => {
    console.log('🛑 Ending WebRTC call');

    // Stop all tracks
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      setLocalStream(null);
    }

    // Close all peer connections
    peerConnections.current.forEach(pc => pc.close());
    peerConnections.current.clear();

    // Don't close the WebSocket - it's shared with translation service
    signalingWs.current = null;

    setParticipants(new Map());
    setIsConnected(false);
    setIsMuted(false);
    setIsVideoOff(false);
    setSignalingConnected(false);
    currentUserId.current = null;
    roomId.current = null;
  }, [localStream]);

  // Add tracks to existing peer connections when localStream becomes available
  useEffect(() => {
    if (!localStream) return;

    console.log('🎥 LocalStream is now available, checking existing peer connections...');
    
    peerConnections.current.forEach((pc, userId) => {
      const senders = pc.getSenders();
      
      // Only add tracks if peer connection has no senders (tracks not added yet)
      if (senders.length === 0) {
        console.log(`➕ Adding tracks to peer connection for ${userId} (delayed stream)`);
        
        localStream.getTracks().forEach(track => {
          try {
            pc.addTrack(track, localStream);
            console.log(`  ✅ Added ${track.kind} track to ${userId}`);
          } catch (err) {
            console.error(`  ❌ Failed to add ${track.kind} track to ${userId}:`, err);
          }
        });
        
        // The onnegotiationneeded event will automatically trigger renegotiation
        console.log(`  ⏳ Waiting for automatic renegotiation with ${userId}...`);
      }
    });
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
    endCall,
    signalingConnected,
    handleSignalingMessage
  };
};