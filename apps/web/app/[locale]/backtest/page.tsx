'use client';

import React, { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { useSearchParams } from 'next/navigation';
import BacktestStats from '@/components/BacktestStats';
import { FlaskConical, Play, Settings, History } from 'lucide-react';
import { Card } from '@/components/ui/Card';

const STORAGE_KEY = 'backtest_config';

export default function BacktestPage() {
    const t = useTranslations('App');
    const tBacktest = useTranslations('Backtest');
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    const [showConfig, setShowConfig] = useState(false);

    // Initial state logic: URL > LocalStorage > Defaults
    const getInitialConfig = () => {
        const urlW = searchParams.get('w') as '15m' | '1h' | '4h' | '12h' | '24h' | null;
        const urlS = searchParams.get('s');
        const urlDir = searchParams.get('dir') as 'bearish' | 'bullish' | null;

        let stored: { window?: '15m' | '1h' | '4h' | '12h' | '24h', minScore?: number, sentiment?: 'bearish' | 'bullish' } = {};
        if (typeof window !== 'undefined') {
            try {
                const item = localStorage.getItem(STORAGE_KEY);
                if (item) stored = JSON.parse(item);
            } catch {
                console.error("Failed to parse stored config");
            }
        }

        return {
            window: urlW || stored.window || '1h',
            minScore: urlS ? parseInt(urlS) : (stored.minScore || 8),
            sentiment: urlDir || stored.sentiment || 'bearish'
        };
    };

    const [config, setConfig] = useState(getInitialConfig());

    // Sync to URL and LocalStorage
    const handleConfigChange = useCallback((newConfig: { window: '15m' | '1h' | '4h' | '12h' | '24h', minScore: number, sentiment: 'bearish' | 'bullish' }) => {
        // Update URL
        const params = new URLSearchParams(searchParams.toString());
        params.set('w', newConfig.window);
        params.set('s', newConfig.minScore.toString());
        params.set('dir', newConfig.sentiment);
        
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });

        // Update LocalStorage
        if (typeof window !== 'undefined') {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig));
        }
        
        setConfig(newConfig);
    }, [pathname, router, searchParams]);

    return (
        <div className="flex flex-col gap-8 p-4 md:p-6 lg:p-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <h1 className="text-2xl font-black tracking-tight flex items-center gap-3">
                        <FlaskConical className="w-8 h-8 text-blue-600" />
                        {t('sidebar.backtest')}
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 text-sm max-w-2xl">
                        {tBacktest('subtitle')}
                    </p>
                </div>
                
                <div className="flex items-center gap-3">
                    <button 
                        onClick={() => setShowConfig(!showConfig)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all border ${showConfig ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/20' : 'bg-slate-100 dark:bg-slate-800 border-transparent text-slate-900 dark:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-700'}`}
                    >
                        <Settings className="w-4 h-4" />
                        {tBacktest('configure')}
                    </button>
                    <button className="flex items-center gap-2 px-6 py-2 rounded-xl bg-blue-600 text-white text-sm font-bold hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/20">
                        <Play className="w-4 h-4 fill-current" />
                        {tBacktest('runBacktest')}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                    {/* Placeholder for Backtest UI */}
                    <BacktestStats 
                        intelligence={[]} 
                        marketData={[]} 
                        showConfig={showConfig}
                        window={config.window}
                        minScore={config.minScore}
                        sentiment={config.sentiment}
                        onConfigChange={handleConfigChange}
                    />
                </div>
                
                <div className="flex flex-col gap-6">
                    <div className="flex items-center gap-2 text-sm font-bold text-slate-400 uppercase tracking-widest">
                        <History className="w-4 h-4" />
                        {tBacktest('recentResults')}
                    </div>
                    
                    <Card className="p-12 flex flex-col items-center justify-center text-center gap-4 border-dashed">
                        <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                            <FlaskConical className="w-8 h-8" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <h3 className="font-bold">{tBacktest('noResultsYet')}</h3>
                            <p className="text-xs text-slate-500">{tBacktest('runFirstBacktest')}</p>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}
