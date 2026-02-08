'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import BacktestStats from '@/components/BacktestStats';
import { Loader2, Activity, Play, Settings, History } from 'lucide-react';
import { Card } from '@/components/ui/Card';

export default function BacktestPage() {
    const t = useTranslations('App');
    const tBacktest = useTranslations('Backtest');
    const [loading, setLoading] = useState(false);
    
    // Mock data or fetch data if needed
    // For now, we'll just show the BacktestStats component with some mock data or empty
    
    return (
        <div className="flex flex-col gap-8 p-4 md:p-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <h1 className="text-2xl font-black tracking-tight flex items-center gap-3">
                        <Activity className="w-8 h-8 text-blue-600" />
                        {t('sidebar.backtest')}
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 text-sm max-w-2xl">
                        {tBacktest('subtitle')}
                    </p>
                </div>
                
                <div className="flex items-center gap-3">
                    <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-sm font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
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
                    <BacktestStats intelligence={[]} marketData={[]} />
                </div>
                
                <div className="flex flex-col gap-6">
                    <div className="flex items-center gap-2 text-sm font-bold text-slate-400 uppercase tracking-widest">
                        <History className="w-4 h-4" />
                        {tBacktest('recentResults')}
                    </div>
                    
                    <Card className="p-12 flex flex-col items-center justify-center text-center gap-4 border-dashed">
                        <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                            <Activity className="w-8 h-8" />
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
