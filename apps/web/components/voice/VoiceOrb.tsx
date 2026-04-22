'use client';

import React, { useState } from 'react';
import { useRealtimeVoice } from '@/hooks/useRealtimeVoice';
import { useGeminiVoice } from '@/hooks/useGeminiVoice';

export default function VoiceOrb() {
  const [provider, setProvider] = useState<'openai' | 'gemini'>('openai');

  const openaiVoice = useRealtimeVoice();
  const geminiVoice = useGeminiVoice();

  // Active Provider Proxy
  const activeVoice = provider === 'openai' ? openaiVoice : geminiVoice;
  const inactiveVoice = provider === 'openai' ? geminiVoice : openaiVoice;

  const handleProviderSwitch = (newProvider: 'openai' | 'gemini') => {
    // Cannot switch while connected
    if (activeVoice.isConnected || activeVoice.isConnecting) return;
    setProvider(newProvider);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Settings / Provider Switcher */}
      {(!activeVoice.isConnected && !activeVoice.isConnecting) && (
        <div className="flex bg-white/90 dark:bg-slate-800/90 shadow-lg rounded-full overflow-hidden border border-slate-200 dark:border-slate-700 p-1">
          <button
            onClick={() => handleProviderSwitch('openai')}
            className={`px-3 py-1.5 text-[10px] font-bold uppercase rounded-full transition-colors ${
              provider === 'openai' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            OpenAI
          </button>
          <button
            onClick={() => handleProviderSwitch('gemini')}
            className={`px-3 py-1.5 text-[10px] font-bold uppercase rounded-full transition-colors ${
              provider === 'gemini' ? 'bg-blue-500 text-white' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            Gemini
          </button>
        </div>
      )}

      {/* Floating Errors */}
      {activeVoice.error && (
        <div className="mb-2 rounded bg-red-100 p-2 text-xs text-red-600 shadow-md">
          {activeVoice.error}
        </div>
      )}

      {/* Main Orb */}
      <button
        onClick={activeVoice.isConnected ? activeVoice.stopSession : activeVoice.startSession}
        disabled={activeVoice.isConnecting}
        className={`flex h-14 w-14 items-center justify-center rounded-full shadow-lg shadow-black/20 transition-all 
          ${activeVoice.isConnecting ? 'animate-pulse bg-slate-400' : 
            activeVoice.isConnected ? 'bg-rose-500 hover:bg-rose-600' : 
            (provider === 'openai' ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-blue-600 hover:bg-blue-700')
          } text-white`}
      >
        {activeVoice.isConnecting ? (
          <span className="text-sm font-medium">...</span>
        ) : activeVoice.isConnected ? (
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <rect x="6" y="6" width="12" height="12" fill="currentColor" />
          </svg>
        ) : (
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        )}
      </button>
    </div>
  );
}
