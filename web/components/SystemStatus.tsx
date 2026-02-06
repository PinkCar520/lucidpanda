'use client';

import React, { useState, useEffect } from 'react';
import { Activity, Globe } from 'lucide-react';

interface SystemStatusProps {
    isConnected?: boolean;
}

export default function SystemStatus({ isConnected = false }: SystemStatusProps) {
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
        <div className="flex items-center gap-4 px-4 py-2 bg-slate-100 dark:bg-slate-900/40 rounded-lg border border-slate-200 dark:border-slate-800/60 backdrop-blur-sm shadow-sm">
            {/* System Status - Real-time SSE Connection */}
            <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold uppercase tracking-wider ${isConnected ? 'text-emerald-600 dark:text-emerald-500 animate-pulse' : 'text-slate-400 dark:text-slate-500'}`}>
                    ● {isConnected ? 'LIVE' : 'OFFLINE'}
                </span>
            </div>

            {/* Separator */}
            <div className="h-3 w-px bg-slate-300 dark:bg-slate-700/50 hidden sm:block"></div>

            {/* UTC Clock */}
            <div className="flex items-center gap-2">
                <Activity className="w-3 h-3 text-slate-500 dark:text-slate-400" />
                <span className="text-xs font-mono text-slate-600 dark:text-slate-300 font-medium w-[90px]">
                    {time}
                </span>
            </div>
        </div>
    );
}
