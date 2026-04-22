import { useState, useRef, useCallback } from 'react';

export function useGeminiVoice() {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const outCtxRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  
  const nextPlayTimeRef = useRef<number>(0);

  const startSession = useCallback(async () => {
    try {
      setError(null);
      setIsConnecting(true);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';
      const wsUrl = apiUrl.replace('http', 'ws') + '/v1/voice/gemini/stream';
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioContextClass({ sampleRate: 16000 });
      audioCtxRef.current = audioCtx;
      
      const outCtx = new AudioContextClass({ sampleRate: 24000 });
      outCtxRef.current = outCtx;

      ws.onopen = async () => {
        setIsConnected(true);
        setIsConnecting(false);
        
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000 } });
          mediaStreamRef.current = stream;
          
          const source = audioCtx.createMediaStreamSource(stream);
          const processor = audioCtx.createScriptProcessor(4096, 1, 1);
          processorRef.current = processor;
          
          source.connect(processor);
          processor.connect(audioCtx.destination);
          
          processor.onaudioprocess = (e) => {
            if (ws.readyState !== WebSocket.OPEN) return;
            const inputData = e.inputBuffer.getChannelData(0);
            const pcm16 = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              const s = Math.max(-1, Math.min(1, inputData[i]));
              pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            
            const bytes = new Uint8Array(pcm16.buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i += 1024) {
               const chunk = bytes.subarray(i, Math.min(i + 1024, bytes.byteLength));
               binary += String.fromCharCode.apply(null, Array.from(chunk));
            }
            const base64 = btoa(binary);
            
            ws.send(JSON.stringify({
              realtimeInput: { mediaChunks: [{ mimeType: "audio/pcm;rate=16000", data: base64 }] }
            }));
          };
        } catch (mediaErr) {
          setError('Microphone access denied or error occurred.');
          ws.close();
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Gemini Live API Audio Structure
          if (data.serverContent?.modelTurn?.parts?.[0]?.inlineData) {
            const base64 = data.serverContent.modelTurn.parts[0].inlineData.data;
            const binary = atob(base64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
              bytes[i] = binary.charCodeAt(i);
            }
            const pcm16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(pcm16.length);
            for (let i = 0; i < pcm16.length; i++) {
              float32[i] = pcm16[i] / 0x8000;
            }
            
            const buffer = outCtx.createBuffer(1, float32.length, 24000);
            buffer.getChannelData(0).set(float32);
            
            const source = outCtx.createBufferSource();
            source.buffer = buffer;
            source.connect(outCtx.destination);
            
            const currTime = outCtx.currentTime;
            if (nextPlayTimeRef.current < currTime) {
                nextPlayTimeRef.current = currTime;
            }
            source.start(nextPlayTimeRef.current);
            nextPlayTimeRef.current += buffer.duration;
          }
        } catch (e) {
          console.error("Gemini parse error", e);
        }
      };

      ws.onclose = () => {
        stopSession();
      };
      
      ws.onerror = () => {
        setError('WebSocket error connecting to Gemini proxy.');
        stopSession();
      };

    } catch (err: any) {
      setError(err.message || 'Failed to start Gemini session');
      setIsConnecting(false);
    }
  }, []);

  const stopSession = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(console.error);
      audioCtxRef.current = null;
    }
    if (outCtxRef.current) {
      outCtxRef.current.close().catch(console.error);
      outCtxRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsConnecting(false);
    nextPlayTimeRef.current = 0;
  }, []);

  return { isConnecting, isConnected, error, startSession, stopSession };
}
