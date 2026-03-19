'use client';

import React, { useState, useEffect } from 'react';
import { Activity, Globe } from 'lucide-react';

interface SystemStatusProps {
    isConnected?: boolean;
    t: (key: string) => string;
    className?: string;
    hideBackground?: boolean;
}

export default function SystemStatus({ isConnected = false, t, className = '', hideBackground = false }: SystemStatusProps) {
    const [time, setTime] = useState<string>('');

    useEffect(() => {
        const updateTime = () => {
            const now = new Date();
            const timeString = now.toISOString().split('T')[1].split('.')[0];
            setTime(`${timeString} UTC`);
        };

        updateTime();
        const interval = setInterval(updateTime, 1000);
        return () => clearInterval(interval);
    }, []);

    if (!time) return null; // Prevent hydration mismatch

    return (
        <div className={`flex items-center gap-2 sm:gap-4 px-2 sm:px-4 py-1.5 sm:py-2 ${hideBackground ? '' : 'bg-slate-100 dark:bg-slate-900/40 rounded-lg border border-slate-200 dark:border-slate-800/60 shadow-sm'} backdrop-blur-sm ${className}`}>
            {/* System Status - Real-time SSE Connection */}
            <div className="flex items-center gap-1 sm:gap-2">
                <span className={`flex items-center text-[10px] font-bold uppercase tracking-wider ${isConnected ? 'text-emerald-600 dark:text-emerald-500 animate-pulse' : 'text-slate-400 dark:text-slate-500'}`}>
                    <span className="text-lg leading-none">●</span>
                    <span className="hidden sm:inline ml-1.5">{isConnected ? t('live') : t('offline')}</span>
                </span>
            </div>

            {/* Separator */}
            <div className="h-3 w-px bg-slate-300 dark:bg-slate-700/50 hidden sm:block"></div>

            {/* UTC Clock */}
            <div className="flex items-center gap-1.5 sm:gap-2">
                <Activity className="w-3 h-3 text-slate-500 dark:text-slate-400 hidden sm:block" />
                <span className="text-[10px] sm:text-xs font-mono text-slate-600 dark:text-slate-300 font-medium sm:w-[90px] w-auto">
                    {time}
                </span>
            </div>
        </div>
    );
}
