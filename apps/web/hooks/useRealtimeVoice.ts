import { useState, useRef, useCallback } from 'react';

/**
 * Hook to manage real-time voice session with OpenAI's Realtime API via WebRTC
 */
export function useRealtimeVoice() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dataChannelRef = useRef<RTCDataChannel | null>(null);

  const startSession = useCallback(async () => {
    setIsConnecting(true);
    setError(null);

    try {
      // 1. Get an ephemeral token from our backend API
      const tokenResponse = await fetch('/api/v1/voice/sessions', {
        method: 'POST',
      });
      if (!tokenResponse.ok) {
        throw new Error('Failed to get voice session token');
      }
      const data = await tokenResponse.json();
      const clientSecret = data.client_secret?.value;
      if (!clientSecret) {
        throw new Error('No client secret returned from API');
      }

      // 2. Initialize WebRTC peer connection
      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      // 3. Setup audio output
      const audioEl = document.createElement('audio');
      audioEl.autoplay = true;
      pc.ontrack = (e) => {
        audioEl.srcObject = e.streams[0];
      };

      // 4. Setup microphone input
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      pc.addTrack(ms.getTracks()[0]);

      // 5. Setup data channel
      const dc = pc.createDataChannel('oai-events');
      dataChannelRef.current = dc;

      dc.addEventListener('message', (e) => {
        // Handle events from OpenAI (e.g. transcriptions, audio events)
        console.log('OpenAI Realtime Event:', JSON.parse(e.data));
      });

      // 6. Create WebRTC offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // 7. Connect to OpenAI Realtime API
      const baseUrl = 'https://api.openai.com/v1/realtime';
      const model = 'gpt-4o-realtime-preview-2024-12-17';
      const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
        method: 'POST',
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${clientSecret}`,
          'Content-Type': 'application/sdp',
        },
      });

      if (!sdpResponse.ok) {
        throw new Error(`SDP Exchange Failed: ${sdpResponse.statusText}`);
      }

      const answerSdp = await sdpResponse.text();
      const answer = { type: 'answer' as RTCSdpType, sdp: answerSdp };
      await pc.setRemoteDescription(answer);

      setIsConnected(true);
    } catch (err: any) {
      console.error('Error starting voice session:', err);
      setError(err.message || 'Failed to start session');
      stopSession();
    } finally {
      setIsConnecting(false);
    }
  }, []);

  const stopSession = useCallback(() => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (dataChannelRef.current) {
      dataChannelRef.current.close();
      dataChannelRef.current = null;
    }
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  return {
    isConnecting,
    isConnected,
    error,
    startSession,
    stopSession,
  };
}
