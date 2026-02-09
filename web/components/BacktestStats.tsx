'use client';

import React, { useMemo } from 'react';
import { Card } from './ui/Card';
import { Intelligence } from '@/lib/db';
import { TrendingDown, TrendingUp, Activity, CheckCircle2, Settings } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface BacktestStatsProps {
    intelligence: Intelligence[];
    marketData: any;
    showConfig?: boolean;
}

export default function BacktestStats({ intelligence, marketData, showConfig = false }: BacktestStatsProps) {
    const t = useTranslations('Backtest');
    const [stats, setStats] = React.useState<{
        count: number;
        winRate: number;
        adjWinRate?: number;
        avgDrop: number;
        hygiene?: { avgClustering: number; avgExhaustion: number; avgDxy?: number };
        correlation?: Record<string, { count: number; winRate: number }>;
        positioning?: Record<string, { count: number; winRate: number }>;
        volatility?: Record<string, { count: number; winRate: number }>;
        sessionStats?: Array<{ session: string; count: number; winRate: number; avgDrop: number }>;
    } | null>(null);
    
    // Configuration State
    const [window, setWindow] = React.useState<'1h' | '24h'>('1h');
    const [minScore, setMinScore] = React.useState(8);
    const [sentiment, setSentiment] = React.useState<'bearish' | 'bullish'>('bearish');

    React.useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await fetch(`/api/stats?window=${window}&min_score=${minScore}&sentiment=${sentiment}`);
                if (res.ok) {
                    const data = await res.json();
                    if (!data.error) {
                        setStats(data);
                    }
                }
            } catch (e) {
                console.error("Failed to fetch stats", e);
            }
        };

        fetchStats();
    }, [intelligence, window, minScore, sentiment]);

    const bestSession = useMemo(() => {
        if (!stats?.sessionStats || stats.sessionStats.length === 0) return null;
        return [...stats.sessionStats].sort((a, b) => b.winRate - a.winRate)[0];
    }, [stats]);

    const isBearish = sentiment === 'bearish';
    const mainColorClass = isBearish ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500';
    const accentColorClass = isBearish ? 'text-blue-600 dark:text-emerald-500' : 'text-emerald-600 dark:text-blue-500';
    const borderAccentClass = isBearish ? 'border-blue-100 dark:border-emerald-500/20' : 'border-emerald-100 dark:border-blue-500/20';
    const bgAccentClass = isBearish ? 'bg-blue-100 dark:bg-emerald-500/20' : 'bg-emerald-100 dark:bg-blue-500/20';
    const winRateBgClass = isBearish ? 'bg-blue-500/50' : 'bg-emerald-500/50';

    if (!stats) return (
        <div className="mb-6 p-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg text-center text-slate-400 dark:text-slate-500 text-xs transition-colors">
            {t('waiting')}
        </div>
    );

    return (
        <div className="flex flex-col gap-4 mb-6">
            {/* Header with Toggle & Config Trigger */}
            <div className="flex items-center justify-between px-1">
                <div className="flex flex-col">
                    <h3 className="text-xs font-bold text-slate-500 dark:text-slate-500 uppercase tracking-widest flex items-center gap-2">
                        <Activity className={`w-4 h-4 ${accentColorClass}`} />
                        {t('title')}
                    </h3>
                    <div className="flex gap-2 mt-1">
                        <span className="text-[8px] bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-500 font-bold uppercase">
                            {t('scoreLabel', { minScore })}
                        </span>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded font-black uppercase ${isBearish ? 'bg-rose-500/10 text-rose-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
                            {t(sentiment)}
                        </span>
                    </div>
                </div>
                
                <div className="flex items-center gap-2">
                    <div className="flex items-center bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-lg p-1">
                        <button
                            onClick={() => setWindow('1h')}
                            className={`px-3 py-1 text-[10px] font-bold uppercase tracking-tighter rounded-md transition-all ${window === '1h' ? `bg-white dark:bg-slate-800 ${isBearish ? 'text-blue-600' : 'text-emerald-500'} shadow-sm` : 'text-slate-500 dark:text-slate-600 hover:text-slate-700 dark:hover:text-slate-400'}`}
                        >
                            {t('window1h')}
                        </button>
                        <button
                            onClick={() => setWindow('24h')}
                            className={`px-3 py-1 text-[10px] font-bold uppercase tracking-tighter rounded-md transition-all ${window === '24h' ? `bg-white dark:bg-slate-800 ${isBearish ? 'text-blue-600' : 'text-emerald-500'} shadow-sm` : 'text-slate-500 dark:text-slate-600 hover:text-slate-700 dark:hover:text-slate-400'}`}
                        >
                            {t('window24h')}
                        </button>
                    </div>
                </div>
            </div>

            {/* Inline Configuration Panel */}
            {showConfig && (
                <div className={`p-4 bg-slate-50 dark:bg-slate-900/60 border ${isBearish ? 'border-blue-500/30' : 'border-emerald-500/30'} rounded-xl animate-in slide-in-from-top-2 duration-300`}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="flex flex-col gap-3">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('minUrgencyScore')}</label>
                            <div className="flex items-center gap-4">
                                <input 
                                    type="range" min="1" max="10" step="1" 
                                    value={minScore} 
                                    onChange={(e) => setMinScore(parseInt(e.target.value))}
                                    className={`flex-1 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full appearance-none cursor-pointer ${isBearish ? 'accent-blue-600' : 'accent-emerald-600'}`}
                                />
                                <span className="text-xl font-black font-mono w-8">{minScore}</span>
                            </div>
                        </div>
                        <div className="flex flex-col gap-3">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('sentimentDirection')}</label>
                            <div className="flex bg-white dark:bg-slate-950 p-1 rounded-lg border border-slate-200 dark:border-slate-800">
                                <button 
                                    onClick={() => setSentiment('bearish')}
                                    className={`flex-1 py-1.5 text-[10px] font-bold uppercase rounded-md transition-all ${sentiment === 'bearish' ? 'bg-rose-500 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900'}`}
                                >
                                    {t('bearishSell')}
                                </button>
                                <button 
                                    onClick={() => setSentiment('bullish')}
                                    className={`flex-1 py-1.5 text-[10px] font-bold uppercase rounded-md transition-all ${sentiment === 'bullish' ? 'bg-emerald-500 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900'}`}
                                >
                                    {t('bullishBuy')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {stats.count === 0 ? (
                <div className="p-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg text-center text-slate-400 dark:text-slate-500 text-xs">
                    {t('noData')}
                </div>
            ) : (
                <div className="flex flex-col gap-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Stat 1: Signal Count */}
                        <div className="bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/50 rounded-lg p-4 flex items-center justify-between shadow-sm dark:shadow-none">
                            <div>
                                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">{t(isBearish ? 'bearishSignals' : 'bullishSignals')}</p>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-mono text-slate-900 dark:text-white font-black">{stats.count}</span>
                                    <span className="text-sm text-slate-400 dark:text-slate-500">{t('events')}</span>
                                </div>
                            </div>
                            <CheckCircle2 className="w-5 h-5 text-slate-300 dark:text-slate-700" />
                        </div>

                        {/* Stat 2: Adjusted Accuracy */}
                        <div className={`bg-slate-50 dark:bg-slate-900/40 border ${borderAccentClass} rounded-lg p-4 flex items-center justify-between relative overflow-hidden shadow-sm dark:shadow-none`}>
                            <div className="absolute top-0 right-0 p-1">
                                <span className={`${bgAccentClass} ${isBearish ? 'text-blue-600' : 'text-emerald-400'} text-[7px] px-1 rounded font-black uppercase`}>{t('adjusted')}</span>
                            </div>
                            <div>
                                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                                    <span className={`${isBearish ? 'text-blue-600' : 'text-emerald-500/80'} mr-1`}>{t('window' + window)}</span>
                                    {t('adjAccuracy')}
                                </p>
                                <div className="flex items-baseline gap-1">
                                    <span className={`text-3xl font-mono font-black ${stats.adjWinRate && stats.adjWinRate > 50 ? (isBearish ? 'text-blue-600 dark:text-blue-400' : 'text-emerald-600 dark:text-emerald-400') : 'text-slate-600 dark:text-slate-300'}`}>
                                        {stats.adjWinRate?.toFixed(0)}%
                                    </span>
                                    <span className="text-xs text-slate-400 dark:text-slate-600 line-through decoration-slate-200 dark:decoration-slate-700">({stats.winRate.toFixed(0)}%)</span>
                                </div>
                            </div>
                            <TrendingUp className={`w-5 h-5 ${stats.adjWinRate && stats.adjWinRate > 50 ? (isBearish ? 'text-blue-500/30' : 'text-emerald-500/50') : 'text-slate-300 dark:text-slate-700'}`} />
                        </div>

                        {/* Stat 3: Avg Performance */}
                        <div className="bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/50 rounded-lg p-4 flex items-center justify-between shadow-sm dark:shadow-none">
                            <div>
                                <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                                    <span className={`${mainColorClass} mr-1`}>{t('window' + window)}</span>
                                    {t(isBearish ? 'avgDrop' : 'avgGain')}
                                </p>
                                <div className="flex items-baseline gap-1">
                                    <span className={`text-3xl font-mono font-black ${stats.avgDrop !== 0 ? (isBearish ? 'text-rose-600' : 'text-emerald-600') : 'text-slate-600 dark:text-slate-400'}`}>
                                        {isBearish ? (stats.avgDrop > 0 ? '↓' : '') : (stats.avgDrop < 0 ? '↑' : '')} {Math.abs(stats.avgDrop).toFixed(2)}%
                                    </span>
                                </div>
                            </div>
                            {isBearish ? (
                                <TrendingDown className={`w-5 h-5 ${stats.avgDrop > 0 ? 'text-rose-500/30' : 'text-slate-300 dark:text-slate-700'}`} />
                            ) : (
                                <TrendingUp className={`w-5 h-5 ${stats.avgDrop < 0 ? 'text-emerald-500/30' : 'text-slate-300 dark:text-slate-700'}`} />
                            )}
                        </div>

                        {/* Stat 4: Hygiene Score */}
                        <div className="bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/50 rounded-lg p-4 shadow-sm dark:shadow-none">
                            <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2 underline decoration-slate-200 dark:decoration-slate-700 underline-offset-4">{t('marketHygiene')}</p>
                            <div className="space-y-1">
                                <div className="flex justify-between items-center text-[10px]">
                                    <span className="text-slate-400 dark:text-slate-600 font-bold uppercase tracking-tighter">{t('density')}</span>
                                    <span className={`font-mono font-bold ${stats.hygiene && stats.hygiene.avgClustering > 2 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-600 dark:text-slate-400'}`}>
                                        {stats.hygiene?.avgClustering.toFixed(1)}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center text-[10px]">
                                    <span className="text-slate-400 dark:text-slate-600 font-bold uppercase tracking-tighter">{t('exhaustion')}</span>
                                    <span className={`font-mono font-bold ${stats.hygiene && stats.hygiene.avgExhaustion > 4 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-600 dark:text-slate-400'}`}>
                                        {stats.hygiene?.avgExhaustion.toFixed(1)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Market Correlation, Positioning & Volatility Sensitivity */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {/* Correlation Card */}
                        {stats.correlation && (
                            <div className="bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none">
                                <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                    <span className={`w-1.5 h-1.5 rounded-full ${isBearish ? 'bg-blue-600' : 'bg-emerald-600'}`}></span>
                                    {t('dxySensitivity')}
                                </h4>
                                <div className="space-y-4">
                                    <div className="flex flex-col gap-2">
                                        <div className="flex justify-between items-center px-1">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">{t('strongUsd')}</span>
                                            <span className={`text-[10px] font-mono ${isBearish ? 'text-emerald-600' : 'text-blue-600'} font-bold`}>{stats.correlation['DXY_STRONG']?.winRate.toFixed(0)}% {t('win')}</span>
                                        </div>
                                        <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                            <div className={`h-full ${isBearish ? 'bg-emerald-500/50' : 'bg-blue-500/50'}`} style={{ width: `${stats.correlation['DXY_STRONG']?.winRate || 0}%` }}></div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-2 opacity-60">
                                        <div className="flex justify-between items-center px-1">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">{t('weakUsd')}</span>
                                            <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400 font-bold">{stats.correlation['DXY_WEAK']?.winRate.toFixed(0)}% {t('win')}</span>
                                        </div>
                                        <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                            <div className="h-full bg-slate-400 dark:bg-slate-700" style={{ width: `${stats.correlation['DXY_WEAK']?.winRate || 0}%` }}></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Positioning Card */}
                        {stats.positioning && (
                            <div className="bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none">
                                <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                                    {t('positioningCot')}
                                </h4>
                                <div className="space-y-4">
                                    <div className="flex flex-col gap-2">
                                        <div className="flex justify-between items-center px-1">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">{t('overcrowdedLong')}</span>
                                            <span className="text-[10px] font-mono text-amber-600 dark:text-amber-500 font-bold">{stats.positioning['OVERCROWDED_LONG']?.winRate.toFixed(0) || 0}% {t('win')}</span>
                                        </div>
                                        <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                            <div className="h-full bg-amber-500/50" style={{ width: `${stats.positioning['OVERCROWDED_LONG']?.winRate || 0}%` }}></div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <div className="flex justify-between items-center px-1">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">{t('neutralRange')}</span>
                                            <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400 font-bold">
                                                {(((stats.positioning['NEUTRAL_POSITION']?.winRate || 0) * (stats.positioning['NEUTRAL_POSITION']?.count || 0) +
                                                    (stats.positioning['OVERCROWDED_SHORT']?.winRate || 0) * (stats.positioning['OVERCROWDED_SHORT']?.count || 0)) /
                                                    Math.max(1, (stats.positioning['NEUTRAL_POSITION']?.count || 0) + (stats.positioning['OVERCROWDED_SHORT']?.count || 0))).toFixed(0)}% {t('win')}
                                            </span>
                                        </div>
                                        <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                            <div className="h-full bg-slate-400 dark:bg-slate-700" style={{ width: '50%' }}></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Volatility Card */}
                        {stats.volatility && (
                            <div className="bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none">
                                <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                    <span className={`w-1.5 h-1.5 rounded-full ${isBearish ? 'bg-rose-600' : 'bg-emerald-600'}`}></span>
                                    {t('volatilityRegime')}
                                </h4>
                                <div className="space-y-4">
                                    <div className="flex flex-col gap-2">
                                        <div className="flex justify-between items-center px-1">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">{t('highVol')}</span>
                                            <span className={`text-[10px] font-mono ${isBearish ? 'text-rose-600' : 'text-emerald-600'} font-bold`}>{stats.volatility['HIGH_VOL']?.winRate.toFixed(0) || 0}% {t('win')}</span>
                                        </div>
                                        <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                            <div className={`h-full ${isBearish ? 'bg-rose-500/50' : 'bg-emerald-500/50'}`} style={{ width: `${stats.volatility['HIGH_VOL']?.winRate || 0}%` }}></div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <div className="flex justify-between items-center px-1">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase">{t('lowVol')}</span>
                                            <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400 font-bold">{stats.volatility['LOW_VOL']?.winRate.toFixed(0) || 0}% {t('win')}</span>
                                        </div>
                                        <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                            <div className="h-full bg-slate-400 dark:bg-slate-700" style={{ width: `${stats.volatility['LOW_VOL']?.winRate || 0}%` }}></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Session Performance Breakdown */}
                    {stats.sessionStats && stats.sessionStats.length > 0 && (
                        <div className="bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none">
                            <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600"></span>
                                {t('sessionBreakdown')}
                            </h4>
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                                {['ASIA', 'LONDON', 'NEWYORK', 'LATE_NY'].map(sessionName => {
                                    const s = stats.sessionStats?.find(item => item.session === sessionName);
                                    const isBest = bestSession?.session === sessionName;

                                    return (
                                        <div key={sessionName} className={`p-2 rounded border ${isBest ? 'bg-emerald-50 dark:bg-emerald-500/5 border-emerald-200 dark:border-emerald-500/20 shadow-sm' : 'bg-white dark:bg-slate-900/20 border-slate-100 dark:border-slate-800/50'}`}>
                                            <div className="flex justify-between items-start mb-1">
                                                <span className={`text-[10px] font-black tracking-tighter ${isBest ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400 dark:text-slate-500'}`}>
                                                    {t(`sessions.${sessionName}`)}
                                                </span>
                                                {isBest && <span className="text-[9px] bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 px-1 rounded uppercase font-bold">{t('best')}</span>}
                                            </div>
                                            <div className="flex items-baseline gap-2">
                                                <span className={`text-base font-mono font-bold ${s ? 'text-slate-900 dark:text-white' : 'text-slate-300 dark:text-slate-700'}`}>
                                                    {s ? `${s.winRate.toFixed(0)}%` : '-%'}
                                                </span>
                                                <span className="text-[10px] text-slate-400 dark:text-slate-600 font-mono">
                                                    n={s?.count || 0}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

