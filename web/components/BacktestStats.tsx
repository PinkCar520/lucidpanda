'use client';

import React, { useMemo } from 'react';
import { Intelligence } from '@/lib/db';
import { useLocale } from 'next-intl';
import { TrendingDown, TrendingUp, Activity, CheckCircle2, AlertTriangle, FileText, ArrowRight, XCircle, Zap, ExternalLink } from 'lucide-react';
import { useTranslations } from 'next-intl';
import AnimatedNumber from './AnimatedNumber';
import { motion } from 'framer-motion';
import { 
    Sheet, 
    SheetContent, 
    SheetHeader, 
    SheetTitle, 
    SheetDescription 
} from './ui/Sheet';
import { Badge } from './ui/Badge';

interface BacktestItem {
    id: number;
    title: string | Record<string, string>; // Localized JSON string or object
    timestamp: string;
    score: number;
    entry: number;
    exit: number;
    is_win: boolean;
    change_pct: number;
}

interface BacktestStatsProps {
    intelligence: Intelligence[];
    marketData: unknown; 
    showConfig?: boolean;
    window?: '1h' | '24h';
    minScore?: number;
    sentiment?: 'bearish' | 'bullish';
    onConfigChange?: (config: { window: '1h' | '24h', minScore: number, sentiment: 'bearish' | 'bullish' }) => void;
}

export default function BacktestStats({ 
    showConfig = false,
    window: initialWindow = '1h',
    minScore: initialMinScore = 8,
    sentiment: initialSentiment = 'bearish',
    onConfigChange
}: BacktestStatsProps) {
    const t = useTranslations('Backtest');
    const locale = useLocale();
    
    // Helper to get localized text from JSON string or object
    const getLocalizedText = (textSource: string | Record<string, string> | undefined, locale: string) => {
        if (!textSource) return '';
        try {
            const data = typeof textSource === 'string' ? JSON.parse(textSource) : textSource;
            return data[locale] || data['en'] || Object.values(data)[0] || '';
        } catch {
            return String(textSource);
        }
    };

    const [loading, setLoading] = React.useState(true);
    const [selectedItem, setSelectedItem] = React.useState<BacktestItem | null>(null);
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
        items?: BacktestItem[];
    } | null>(null);
    
    // Configuration State - Initialize directly from props to avoid sync effect
    const [window, setWindow] = React.useState<'1h' | '24h'>(initialWindow);
    const [minScore, setMinScore] = React.useState(initialMinScore);
    const [debouncedMinScore, setDebouncedMinScore] = React.useState(initialMinScore);
    const [sentiment, setSentiment] = React.useState<'bearish' | 'bullish'>(initialSentiment);

    // Sync state from props ONLY when they change externally (e.g. initial load from URL)
    // Use a ref to track if it's the first mount to avoid redundant internal state updates
    const isFirstMount = React.useRef(true);
    React.useEffect(() => {
        if (isFirstMount.current) {
            isFirstMount.current = false;
            return;
        }
        setWindow(initialWindow);
        setMinScore(initialMinScore);
        setSentiment(initialSentiment);
        setDebouncedMinScore(initialMinScore);
    }, [initialWindow, initialMinScore, initialSentiment]);

    // Debounce minScore and trigger onConfigChange
    React.useEffect(() => {
        // If values match already, don't trigger anything
        if (debouncedMinScore === minScore) return;

        const handler = setTimeout(() => {
            setDebouncedMinScore(minScore);
            onConfigChange?.({ window, minScore, sentiment });
        }, 400); // 400ms debounce

        return () => {
            clearTimeout(handler);
        };
    }, [minScore, debouncedMinScore, window, sentiment, onConfigChange]);

    // Separate effect for immediate config changes (window/sentiment)
    React.useEffect(() => {
        // Only trigger if window or sentiment changed and they don't match initial props
        // to avoid infinite loops or redundant calls on mount
        if (window !== initialWindow || sentiment !== initialSentiment) {
            onConfigChange?.({ window, minScore, sentiment });
        }
    }, [window, initialWindow, sentiment, initialSentiment, minScore, onConfigChange]);

    React.useEffect(() => {
        const fetchStats = async () => {
            setLoading(true);
            try {
                const res = await fetch(`/api/stats?window=${window}&min_score=${debouncedMinScore}&sentiment=${sentiment}`);
                if (res.ok) {
                    const data = await res.json();
                    if (!data.error) {
                        setStats(data);
                    }
                }
            } catch {
                console.error("Failed to fetch stats");
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, [window, debouncedMinScore, sentiment]); 

    const bestSession = useMemo(() => {
        if (!stats?.sessionStats || stats.sessionStats.length === 0) return null;
        return [...stats.sessionStats].sort((a, b) => b.winRate - a.winRate)[0];
    }, [stats]);

    const isBearish = sentiment === 'bearish';
    const mainColorClass = isBearish ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500';
    const accentColorClass = isBearish ? 'text-blue-600 dark:text-emerald-500' : 'text-emerald-600 dark:text-blue-500';
    const borderAccentClass = isBearish ? 'border-blue-100 dark:border-emerald-500/20' : 'border-emerald-100 dark:border-blue-500/20';
    const bgAccentClass = isBearish ? 'bg-blue-100 dark:bg-emerald-500/20' : 'bg-emerald-100 dark:bg-blue-500/20';

    if (!stats && loading) return (
        <div className="mb-6 p-12 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg text-center flex flex-col items-center justify-center gap-3">
            <Activity className="w-8 h-8 text-slate-200 dark:text-slate-800 animate-pulse" />
            <span className="text-slate-400 dark:text-slate-500 text-xs">{t('waiting')}</span>
        </div>
    );

    return (
        <div className="flex flex-col gap-4 mb-6">
            {/* Header with Toggle & Config Trigger */}
            <div className="flex items-center justify-between px-1">
                <div className="flex flex-col">
                    <h3 className="text-xs font-bold text-slate-500 dark:text-slate-500 uppercase tracking-widest flex items-center gap-2">
                        <Activity className={`w-4 h-4 ${accentColorClass} ${loading ? 'animate-pulse' : ''}`} />
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
                            disabled={loading}
                            className={`px-3 py-1 text-[10px] font-bold uppercase tracking-tighter rounded-md transition-all ${window === '1h' ? `bg-white dark:bg-slate-800 ${isBearish ? 'text-blue-600' : 'text-emerald-500'} shadow-sm` : 'text-slate-500 dark:text-slate-600 hover:text-slate-700 dark:hover:text-slate-400'}`}
                        >
                            {t('window1h')}
                        </button>
                        <button
                            onClick={() => setWindow('24h')}
                            disabled={loading}
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
                        <div className="flex flex-col gap-1.5">
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
                            {/* Smart Hint below slider */}
                            <div className="h-4">
                                {stats && stats.count === 0 && !loading && (
                                    <span className="text-[9px] text-rose-500 font-bold animate-in fade-in duration-300">{t('tooHighScore')}</span>
                                )}
                                {stats && stats.count > 0 && stats.count < 5 && !loading && (
                                    <span className="text-[9px] text-amber-500 font-medium animate-in fade-in duration-300">{t('smallSample', { count: stats.count })}</span>
                                )}
                            </div>
                        </div>
                        <div className="flex flex-col gap-3">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('sentimentDirection')}</label>
                            <div className="flex bg-white dark:bg-slate-950 p-1 rounded-lg border border-slate-200 dark:border-slate-800">
                                <button 
                                    onClick={() => setSentiment('bearish')}
                                    disabled={loading}
                                    className={`flex-1 py-1.5 text-[10px] font-bold uppercase rounded-md transition-all ${sentiment === 'bearish' ? 'bg-rose-500 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900'}`}
                                >
                                    {t('bearishSell')}
                                </button>
                                <button 
                                    onClick={() => setSentiment('bullish')}
                                    disabled={loading}
                                    className={`flex-1 py-1.5 text-[10px] font-bold uppercase rounded-md transition-all ${sentiment === 'bullish' ? 'bg-emerald-500 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900'}`}
                                >
                                    {t('bullishBuy')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div className="flex flex-col gap-4 relative">
                {/* Dynamic Empty State Overlay */}
                {stats && stats.count === 0 && !loading && (
                    <div className="absolute inset-0 z-10 bg-white/60 dark:bg-slate-950/60 backdrop-blur-[2px] rounded-xl flex items-center justify-center p-6 text-center animate-in fade-in duration-300">
                        <div className="flex flex-col items-center gap-2 max-w-sm">
                            <AlertTriangle className="w-8 h-8 text-amber-500 opacity-50 mb-2" />
                            <p className="text-sm font-bold text-slate-600 dark:text-slate-300 leading-relaxed">
                                {t('noData', { sentiment: t(sentiment), score: debouncedMinScore })}
                            </p>
                        </div>
                    </div>
                )}

                <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 transition-opacity duration-300 ${stats && stats.count === 0 && !loading ? 'opacity-30 grayscale pointer-events-none' : ''}`}>
                    {/* Stat 1: Signal Count */}
                    <div className="bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/50 rounded-lg p-4 flex items-center justify-between shadow-sm dark:shadow-none">
                        <div>
                            <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">{t(isBearish ? 'bearishSignals' : 'bullishSignals', { score: minScore })}</p>
                            <div className={`flex items-baseline gap-1 ${loading ? 'animate-pulse' : ''}`}>
                                {loading ? (
                                    <span className="text-3xl font-mono text-slate-900 dark:text-white font-black">--</span>
                                ) : (
                                    <AnimatedNumber 
                                        value={stats?.count || 0} 
                                        className="text-3xl font-mono text-slate-900 dark:text-white font-black"
                                    />
                                )}
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
                            <div className={`flex items-baseline gap-1 ${loading ? 'animate-pulse' : ''}`}>
                                {loading ? (
                                    <span className="text-3xl font-mono font-black text-slate-600 dark:text-slate-300">--%</span>
                                ) : (
                                    <AnimatedNumber 
                                        value={stats?.adjWinRate || 0}
                                        suffix="%"
                                        className={`text-3xl font-mono font-black ${stats?.adjWinRate && stats.adjWinRate > 50 ? (isBearish ? 'text-blue-600 dark:text-blue-400' : 'text-emerald-600 dark:text-emerald-400') : 'text-slate-600 dark:text-slate-300'}`}
                                    />
                                )}
                                {!loading && stats && (
                                    <div className="text-xs text-slate-400 dark:text-slate-600 line-through decoration-slate-200 dark:decoration-slate-700 flex">
                                        (<AnimatedNumber value={stats.winRate} suffix="%" />)
                                    </div>
                                )}
                            </div>
                        </div>
                        <TrendingUp className={`w-5 h-5 ${stats?.adjWinRate && stats.adjWinRate > 50 ? (isBearish ? 'text-blue-500/30' : 'text-emerald-500/50') : 'text-slate-300 dark:text-slate-700'}`} />
                    </div>

                    {/* Stat 3: Avg Performance */}
                    <div className="bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/50 rounded-lg p-4 flex items-center justify-between shadow-sm dark:shadow-none">
                        <div>
                            <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                                <span className={`${mainColorClass} mr-1`}>{t('window' + window)}</span>
                                {t(isBearish ? 'avgDrop' : 'avgGain')}
                            </p>
                            <div className={`flex items-baseline gap-1 ${loading ? 'animate-pulse' : ''}`}>
                                {loading ? (
                                    <span className="text-3xl font-mono font-black text-slate-600 dark:text-slate-400">--%</span>
                                ) : (
                                    <AnimatedNumber 
                                        value={Math.abs(stats?.avgDrop || 0)}
                                        precision={2}
                                        suffix="%"
                                        prefix={isBearish ? (stats?.avgDrop && stats.avgDrop > 0 ? '↓ ' : '') : (stats?.avgDrop && stats.avgDrop < 0 ? '↑ ' : '')}
                                        className={`text-3xl font-mono font-black ${stats?.avgDrop && stats.avgDrop !== 0 ? (isBearish ? 'text-rose-600' : 'text-emerald-600') : 'text-slate-600 dark:text-slate-400'}`}
                                    />
                                )}
                            </div>
                        </div>
                        {isBearish ? (
                            <TrendingDown className={`w-5 h-5 ${stats?.avgDrop && stats.avgDrop > 0 ? 'text-rose-500/30' : 'text-slate-300 dark:text-slate-700'}`} />
                        ) : (
                            <TrendingUp className={`w-5 h-5 ${stats?.avgDrop && stats.avgDrop < 0 ? 'text-emerald-500/30' : 'text-slate-300 dark:text-slate-700'}`} />
                        )}
                    </div>
                </div>

                {/* Hygiene & Sensitivities remain in the same structure, updated with loading states */}
                <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 transition-opacity duration-300 ${stats && stats.count === 0 && !loading ? 'opacity-30 grayscale pointer-events-none' : ''}`}>
                    {/* Stat 4: Hygiene Score */}
                    <div className="bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/50 rounded-lg p-4 shadow-sm dark:shadow-none">
                        <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-2 underline decoration-slate-200 dark:decoration-slate-700 underline-offset-4">{t('marketHygiene')}</p>
                        <div className={`space-y-1 ${loading ? 'animate-pulse opacity-50' : ''}`}>
                            <div className="flex justify-between items-center text-[10px]">
                                <span className="text-slate-400 dark:text-slate-600 font-bold uppercase tracking-tighter">{t('density')}</span>
                                <span className={`font-mono font-bold ${stats?.hygiene && stats.hygiene.avgClustering > 2 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-600 dark:text-slate-400'}`}>
                                    {loading ? '-' : <AnimatedNumber value={stats?.hygiene?.avgClustering || 0} precision={1} />}
                                </span>
                            </div>
                            <div className="flex justify-between items-center text-[10px]">
                                <span className="text-slate-400 dark:text-slate-600 font-bold uppercase tracking-tighter">{t('exhaustion')}</span>
                                <span className={`font-mono font-bold ${stats?.hygiene && stats.hygiene.avgExhaustion > 4 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-600 dark:text-slate-400'}`}>
                                    {loading ? '-' : <AnimatedNumber value={stats?.hygiene?.avgExhaustion || 0} precision={1} />}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className={`grid grid-cols-1 lg:grid-cols-3 gap-4 transition-opacity duration-300 ${stats && stats.count === 0 && !loading ? 'opacity-30 grayscale pointer-events-none' : ''}`}>
                    {/* Correlation Card */}
                    {stats?.correlation && (
                        <div className="bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none">
                            <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                <span className={`w-1.5 h-1.5 rounded-full ${isBearish ? 'bg-blue-600' : 'bg-emerald-600'}`}></span>
                                {t('dxySensitivity')}
                            </h4>
                            <div className={`space-y-4 ${loading ? 'animate-pulse opacity-50' : ''}`}>
                                <div className="flex flex-col gap-2">
                                    <div className="flex justify-between items-center px-1">
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">{t('strongUsd')}</span>
                                        <span className={`text-[10px] font-mono ${isBearish ? 'text-emerald-600' : 'text-blue-600'} font-bold flex`}>
                                            <AnimatedNumber value={stats.correlation['DXY_STRONG']?.winRate || 0} suffix="%" /> 
                                            <span className="ml-1">{t('win')}</span>
                                        </span>
                                    </div>
                                    <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }}
                                            animate={{ width: `${stats.correlation['DXY_STRONG']?.winRate || 0}%` }}
                                            className={`h-full ${isBearish ? 'bg-emerald-500/50' : 'bg-blue-500/50'}`} 
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col gap-2 opacity-60">
                                    <div className="flex justify-between items-center px-1">
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">{t('weakUsd')}</span>
                                        <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400 font-bold flex">
                                            <AnimatedNumber value={stats.correlation['DXY_WEAK']?.winRate || 0} suffix="%" /> 
                                            <span className="ml-1">{t('win')}</span>
                                        </span>
                                    </div>
                                    <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }}
                                            animate={{ width: `${stats.correlation['DXY_WEAK']?.winRate || 0}%` }}
                                            className="h-full bg-slate-400 dark:bg-slate-700" 
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Positioning Card */}
                    {stats?.positioning && (
                        <div className="bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none">
                            <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                                {t('positioningCot')}
                            </h4>
                            <div className={`space-y-4 ${loading ? 'animate-pulse opacity-50' : ''}`}>
                                <div className="flex flex-col gap-2">
                                    <div className="flex justify-between items-center px-1">
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">{t('overcrowdedLong')}</span>
                                        <span className="text-[10px] font-mono text-amber-600 dark:text-amber-500 font-bold flex">
                                            <AnimatedNumber value={stats.positioning['OVERCROWDED_LONG']?.winRate || 0} suffix="%" />
                                            <span className="ml-1">{t('win')}</span>
                                        </span>
                                    </div>
                                    <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }}
                                            animate={{ width: `${stats.positioning['OVERCROWDED_LONG']?.winRate || 0}%` }}
                                            className="h-full bg-amber-500/50" 
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col gap-2">
                                    <div className="flex justify-between items-center px-1">
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">{t('neutralRange')}</span>
                                        <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400 font-bold flex">
                                            <AnimatedNumber 
                                                value={(((stats.positioning['NEUTRAL_POSITION']?.winRate || 0) * (stats.positioning['NEUTRAL_POSITION']?.count || 0) +
                                                    (stats.positioning['OVERCROWDED_SHORT']?.winRate || 0) * (stats.positioning['OVERCROWDED_SHORT']?.count || 0)) /
                                                    Math.max(1, (stats.positioning['NEUTRAL_POSITION']?.count || 0) + (stats.positioning['OVERCROWDED_SHORT']?.count || 0)))}
                                                suffix="%"
                                            />
                                            <span className="ml-1">{t('win')}</span>
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
                    {stats?.volatility && (
                        <div className="bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none">
                            <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                                <span className={`w-1.5 h-1.5 rounded-full ${isBearish ? 'bg-rose-600' : 'bg-emerald-600'}`}></span>
                                {t('volatilityRegime')}
                            </h4>
                            <div className={`space-y-4 ${loading ? 'animate-pulse opacity-50' : ''}`}>
                                <div className="flex flex-col gap-2">
                                    <div className="flex justify-between items-center px-1">
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">{t('highVol')}</span>
                                        <span className={`text-[10px] font-mono ${isBearish ? 'text-rose-600' : 'text-emerald-600'} font-bold flex`}>
                                            <AnimatedNumber value={stats.volatility['HIGH_VOL']?.winRate || 0} suffix="%" />
                                            <span className="ml-1">{t('win')}</span>
                                        </span>
                                    </div>
                                    <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }}
                                            animate={{ width: `${stats.volatility['HIGH_VOL']?.winRate || 0}%` }}
                                            className={`h-full ${isBearish ? 'bg-rose-500/50' : 'bg-emerald-500/50'}`} 
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-col gap-2">
                                    <div className="flex justify-between items-center px-1">
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">{t('lowVol')}</span>
                                        <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400 font-bold flex">
                                            <AnimatedNumber value={stats.volatility['LOW_VOL']?.winRate || 0} suffix="%" />
                                            <span className="ml-1">{t('win')}</span>
                                        </span>
                                    </div>
                                    <div className="h-1 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }}
                                            animate={{ width: `${stats.volatility['LOW_VOL']?.winRate || 0}%` }}
                                            className="h-full bg-slate-400 dark:bg-slate-700" 
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Session Performance Breakdown */}
                {stats?.sessionStats && stats.sessionStats.length > 0 && (
                    <div className={`bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/30 rounded-lg p-3 shadow-sm dark:shadow-none transition-opacity duration-300 ${stats && stats.count === 0 && !loading ? 'opacity-30 grayscale pointer-events-none' : ''}`}>
                        <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-600 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600"></span>
                            {t('sessionBreakdown')}
                        </h4>
                        <div className={`grid grid-cols-2 lg:grid-cols-4 gap-3 ${loading ? 'animate-pulse opacity-50' : ''}`}>
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
                                            <span className="text-base font-mono font-bold text-slate-900 dark:text-white">
                                                {s ? <AnimatedNumber value={s.winRate} suffix="%" /> : '-%'}
                                            </span>
                                            <span className="text-[10px] text-slate-400 dark:text-slate-600 font-mono flex">
                                                n=<AnimatedNumber value={s?.count || 0} />
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Evidence List (Breaking the Black Box) */}
                {!loading && stats?.items && stats.items.length > 0 && (
                    <div className="flex flex-col gap-3 mt-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        <h4 className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em] px-1 flex items-center gap-2">
                            <FileText className="w-4 h-4 text-blue-500" />
                            {t('evidenceList')} ({stats.count})
                        </h4>
                        <div className="space-y-2">
                            {stats.items.map((item) => (
                                <div 
                                    key={item.id} 
                                    onClick={() => setSelectedItem(item)}
                                    className="group relative bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/50 rounded-xl p-3 hover:border-blue-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-all cursor-pointer shadow-sm dark:shadow-none"
                                >
                                    <div className="flex items-center justify-between gap-4">
                                        <div className="flex items-center gap-3 flex-1 min-w-0">
                                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${item.is_win ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                                                {item.is_win ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                                            </div>
                                            <div className="flex flex-col min-w-0">
                                                <span className="text-xs font-bold text-slate-700 dark:text-slate-200 truncate group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors">
                                                    {getLocalizedText(item.title, locale)}
                                                </span>
                                                <div className="flex items-center gap-2 text-[9px] text-slate-400 font-mono mt-0.5">
                                                    <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                                    <span className="opacity-30">|</span>
                                                    <span className="bg-slate-100 dark:bg-slate-800 px-1 rounded font-bold">Score {item.score}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-8 shrink-0">
                                            <div className="hidden md:flex flex-col items-end">
                                                <span className="text-[8px] text-slate-400 uppercase font-black tracking-tighter leading-none mb-1">{t('priceAction')}</span>
                                                <div className="text-[10px] font-mono font-bold flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                                                    <span className="bg-slate-100 dark:bg-slate-800 px-1 rounded">{item.entry.toFixed(1)}</span>
                                                    <ArrowRight className="w-3 h-3 opacity-30" />
                                                    <span className="bg-slate-100 dark:bg-slate-800 px-1 rounded">{item.exit.toFixed(1)}</span>
                                                </div>
                                            </div>
                                            <div className={`w-14 text-right font-mono font-black text-xs ${item.is_win ? 'text-emerald-500' : 'text-rose-500'}`}>
                                                {item.change_pct > 0 ? '↑' : '↓'} {Math.abs(item.change_pct).toFixed(2)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Detail Drawer (Sheet) */}
                <Sheet open={!!selectedItem} onOpenChange={(open) => !open && setSelectedItem(null)}>
                    <SheetContent className="overflow-y-auto">
                        <SheetHeader className="mb-6">
                            <div className="flex items-center gap-2 mb-2">
                                <Badge variant={selectedItem?.is_win ? 'bullish' : 'bearish'}>
                                    {selectedItem?.is_win ? t('winStatus') : t('lossStatus')}
                                </Badge>
                                <span className="text-[10px] font-mono text-slate-400">{t('idLabel')}: {selectedItem?.id}</span>
                            </div>
                            <SheetTitle className="text-xl leading-snug">{getLocalizedText(selectedItem?.title, locale)}</SheetTitle>
                            <SheetDescription className="flex items-center gap-2 font-mono text-[10px] mt-1">
                                <Activity className="w-3 h-3" />
                                {selectedItem && new Date(selectedItem.timestamp).toLocaleString()}
                            </SheetDescription>
                        </SheetHeader>

                        <div className="flex flex-col gap-6">
                            {/* Price Snapshot */}
                            <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4 border border-slate-100 dark:border-slate-800">
                                <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">{t('priceActionDetail')}</h5>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="flex flex-col">
                                        <span className="text-[10px] text-slate-500 font-bold uppercase">{t('entryPrice')}</span>
                                        <span className="text-xl font-mono font-black">{selectedItem?.entry?.toFixed(2) || '0.00'}</span>
                                    </div>
                                    <div className="flex flex-col items-end">
                                        <span className="text-[10px] text-slate-500 font-bold uppercase">{t('exitPrice')} ({t('window' + window)})</span>
                                        <span className="text-xl font-mono font-black">{selectedItem?.exit?.toFixed(2) || '0.00'}</span>
                                    </div>
                                </div>
                                <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800 flex justify-between items-center">
                                    <span className="text-xs font-bold text-slate-500">{t('netChange')}</span>
                                    <span className={`text-lg font-mono font-black ${selectedItem?.is_win ? 'text-emerald-500' : 'text-rose-500'}`}>
                                        {(selectedItem?.change_pct ?? 0) > 0 ? '+' : ''}{selectedItem?.change_pct?.toFixed(3) || '0.000'}%
                                    </span>
                                </div>
                            </div>

                            {/* Intelligence Metadata */}
                            <div className="space-y-4">
                                <div className="flex flex-col gap-1.5">
                                    <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                        <Zap className="w-3 h-3 text-amber-500" />
                                        {t('urgencyImpact')}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="h-2 flex-1 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                            <div 
                                                className="h-full bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.4)]" 
                                                style={{ width: `${(selectedItem?.score || 0) * 10}%` }} 
                                            />
                                        </div>
                                        <span className="text-sm font-black font-mono">{selectedItem?.score}/10</span>
                                    </div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="pt-6 border-t border-slate-100 dark:border-slate-900 flex flex-col gap-3">
                                <button className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-sm transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2">
                                    {t('viewFullAnalysis')}
                                    <ExternalLink className="w-4 h-4" />
                                </button>
                                <p className="text-[10px] text-slate-400 text-center px-4 leading-relaxed italic">
                                    {t('analysisDisclaimer', { 
                                        window: t('window' + window), 
                                        sentiment: t(sentiment) 
                                    })}
                                </p>
                            </div>
                        </div>
                    </SheetContent>
                </Sheet>
            </div>
        </div>
    );
}
