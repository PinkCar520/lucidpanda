'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react'; // Added missing import
import { useRouter, useSearchParams } from 'next/navigation'; // Added missing import
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Search, RefreshCw, ArrowUp, ArrowDown, PieChart, X, Target, Scale, Anchor, AlertTriangle } from 'lucide-react';
import FundSearch from '@/components/FundSearch';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import { authenticatedFetch } from '@/lib/api-client';
import useSWR, { mutate } from 'swr';

import { SectorAttribution } from '@/components/SectorAttribution';
import { FundSparkline } from '@/components/FundSparkline';

interface ComponentStock {
    code: string;
    name: string;
    price: number;
    change_pct: number;
    impact: number;
    weight: number;
}

interface FundStats {
    return_1w: number;
    return_1m: number;
    return_3m: number;
    return_1y: number;
    sharpe_ratio: number;
    sharpe_grade: string;
    max_drawdown: number;
    drawdown_grade: string;
    volatility: number;
    sparkline_data: number[];
}

interface FundValuation {
    fund_code: string;
    fund_name: string;
    estimated_growth: number;
    total_weight: number;
    status?: string;
    message?: string;
    components: ComponentStock[];
    sector_attribution?: Record<string, {
        impact: number;
        weight: number;
        sub: Record<string, { impact: number; weight: number; }>;
    }>;
    timestamp: string;
    source?: string;
    stats?: FundStats;
}

interface ValuationHistory {
    trade_date: string;
    frozen_est_growth: number;
    official_growth: number;
    deviation: number;
    tracking_status: string;
    sector_attribution?: Record<string, {
        impact: number;
        weight: number;
        sub: Record<string, { impact: number; weight: number; }>;
    }>;
    timestamp: string;
    source?: string;
}

interface WatchlistItem {
    code: string;
    name: string;
    estimated_growth?: number; // For sorting by daily performance
    previous_growth?: number; // For trend arrows (↑↓)
    source?: string; // For confidence indicators
    stats?: FundStats;
}

export default function FundDashboard({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = React.use(params);
    const { data: session, status } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const t = useTranslations('Funds');
    const tApp = useTranslations('App');

    // State management - UI and sorting
    const [selectedFund, setSelectedFund] = useState<string>('');
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [sortOrder, setSortOrder] = useState<'desc' | 'asc' | 'none'>('desc');
    const [activeTab, setActiveTab] = useState<'attribution' | 'sector' | 'history'>('attribution');
    const [isWatchlistOpen, setIsWatchlistOpen] = useState(false);

    // --- SWR Data Fetching ---

    // 1. Fetch Watchlist
    const { data: watchlistData, mutate: mutateWatchlist, isValidating: watchlistValidating } = useSWR(
        status === 'authenticated' ? '/api/watchlist' : null,
        async (url) => {
            const res = await authenticatedFetch(url, session);
            const json = await res.json();
            return json.data as WatchlistItem[];
        },
        {
            revalidateOnFocus: false, // 禁用失去焦点重新验证
            dedupingInterval: 30000, // 30秒内不重复请求
            onSuccess: (data) => {
                if (data.length > 0 && !selectedFund) {
                    const stored = localStorage.getItem('fund_selected');
                    if (stored && data.some(i => i.code === stored)) {
                        setSelectedFund(stored);
                    } else {
                        setSelectedFund(data[0].code);
                    }
                }
            }
        }
    );

    // 2. Fetch Batch Valuation (Growth only)
    const watchlistCodes = watchlistData?.map(w => w.code).join(',');
    const { data: batchData } = useSWR(
        status === 'authenticated' && watchlistCodes ? `/api/funds/batch-valuation?codes=${watchlistCodes}&mode=summary` : null,
        async (url) => {
            const res = await authenticatedFetch(url, session);
            const json = await res.json();
            return json.data;
        },
        { 
            refreshInterval: 60000, // 延长至 60 秒刷新一次
            dedupingInterval: 20000,
            revalidateOnFocus: false 
        }
    );

    // 3. Fetch Selected Fund Detail
    const { data: valuation, error: valError, isValidating: loading } = useSWR(
        status === 'authenticated' && selectedFund ? `/api/funds/${selectedFund}/valuation` : null,
        async (url) => {
            const res = await authenticatedFetch(url, session);
            return await res.json();
        },
        {
            revalidateOnFocus: false,
            dedupingInterval: 60000, // 详情数据 60 秒内不重复请求
            onSuccess: () => setLastUpdated(new Date())
        }
    );

    // 4. Fetch History
    const { data: historyData, isValidating: historyLoading } = useSWR(
        status === 'authenticated' && selectedFund ? `/api/funds/${selectedFund}/history` : null,
        async (url) => {
            const res = await authenticatedFetch(url, session);
            const json = await res.json();
            return json.data as ValuationHistory[];
        },
        {
            revalidateOnFocus: false,
            dedupingInterval: 300000 // 历史记录 5 分钟内不重复请求
        }
    );

    const watchlist = useMemo(() => {
        if (!watchlistData) return [];
        return watchlistData.map(item => {
            const val = batchData?.find((v: any) => v.fund_code === item.code);
            return {
                ...item,
                estimated_growth: val?.estimated_growth ?? item.estimated_growth,
                source: val?.source ?? item.source,
                stats: val?.stats ?? item.stats
            };
        });
    }, [watchlistData, batchData]);

    const history = historyData || [];


    // Load selected fund preference from URL
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const queryCode = searchParams.get('code');
            if (queryCode) {
                setSelectedFund(queryCode);
            }
        }
    }, [searchParams]);

    // Persist selected fund to localStorage
    useEffect(() => {
        if (selectedFund) {
            localStorage.setItem('fund_selected', selectedFund);
        }
    }, [selectedFund]);




    // Persist selected fund to localStorage
    useEffect(() => {
        if (typeof window !== 'undefined') {
            try {
                localStorage.setItem('fund_selected', selectedFund);
            } catch (e) {
                console.error('Failed to save selected fund to localStorage:', e);
            }
        }
    }, [selectedFund]);

    // Auto refresh every 3 minutes (matching cache TTL)


    // Manual refresh for the entire watchlist
    const handleWatchlistRefresh = async () => {
        // Trigger SWR revalidation
        mutate(status === 'authenticated' && watchlistCodes ? `/api/funds/batch-valuation?codes=${watchlistCodes}&mode=summary` : null);
        if (selectedFund) {
            mutate(status === 'authenticated' && selectedFund ? `/api/funds/${selectedFund}/valuation` : null);
            mutate(status === 'authenticated' && selectedFund ? `/api/funds/${selectedFund}/history` : null);
        }
    };

    const handleDelete = async (e: React.MouseEvent, codeToDelete: string) => {
        e.stopPropagation();

        if (!session?.accessToken) return;

        try {
            const res = await authenticatedFetch(`/api/watchlist/${codeToDelete}`, session, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (data.success) {
                // Optimistically update watchlist
                mutateWatchlist(watchlistData?.filter(i => i.code !== codeToDelete), false);
                if (selectedFund === codeToDelete) {
                    const remaining = watchlistData?.filter(i => i.code !== codeToDelete);
                    if (remaining && remaining.length > 0) setSelectedFund(remaining[0].code);
                    else setSelectedFund("");
                }
            }
        } catch (err) {
            console.error('Failed to delete from watchlist:', err);
        }
    };

    const handleManualRefresh = async () => {
        if (selectedFund) {
            mutate(status === 'authenticated' && selectedFund ? `/api/funds/${selectedFund}/valuation` : null);
        }
    };

    return (
        <div className="flex flex-col p-4 md:p-6 lg:p-8 gap-6 lg:h-full lg:overflow-hidden min-h-screen">
            <div className="flex flex-col lg:grid lg:grid-cols-12 gap-6 flex-1 min-h-0">
                {/* Left: Watchlist (Mobile: Toggleable, Desktop: Fixed Sidebar) */}
                <div className="lg:col-span-4 flex flex-col gap-4 min-h-0">
                    {/* Mobile Fund Switcher / Current Indicator - STICKY Apple Style Glass */}
                    <div
                        onClick={() => setIsWatchlistOpen(!isWatchlistOpen)}
                        className="flex lg:hidden sticky top-0 z-30 items-center justify-between p-4 bg-white/70 dark:bg-slate-900/70 backdrop-blur-xl saturate-150 rounded-xl border border-slate-200/60 dark:border-slate-800/60 cursor-pointer active:bg-slate-100/50 dark:active:bg-slate-800/50 transition-all shadow-sm"
                    >
                        <div className="flex flex-col">
                            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-tighter">{t('currentlyViewing') || 'CURRENTLY VIEWING'}</span>
                            <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                                {valuation?.fund_name || selectedFund || t('selectFund')}
                                <Search className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" />
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            {valuation && (
                                <span className={`text-lg font-black font-mono ${valuation.estimated_growth >= 0 ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500'}`}>
                                    {valuation.estimated_growth > 0 ? '+' : ''}{valuation.estimated_growth.toFixed(2)}%
                                </span>
                            )}
                            <div className={`p-1.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm transition-transform duration-300 ${isWatchlistOpen ? 'rotate-180' : ''}`}>
                                <ArrowDown className="w-4 h-4 text-slate-400 dark:text-slate-500" />
                            </div>
                        </div>
                    </div>

                    {/* The Actual Watchlist Card */}
                    <Card
                        title={t('watchlist')}
                        className={`lg:flex flex-col overflow-hidden transition-all duration-300 ${isWatchlistOpen ? 'flex h-[500px] border-blue-200 dark:border-blue-900 shadow-lg' : 'hidden h-0 lg:h-full'}`}
                        contentClassName="flex-1 min-h-0 flex flex-col p-3"
                        action={
                            <div className="liquid-glass-toolbar">
                                <button
                                    onClick={handleWatchlistRefresh}
                                    className={`liquid-glass-btn ${watchlistValidating ? 'active' : ''}`}
                                    title={t('refreshWatchlist')}
                                    disabled={watchlistValidating}
                                >
                                    <RefreshCw className={`w-4 h-4 ${watchlistValidating ? 'animate-spin' : ''}`} />
                                </button>
                                <div className="w-px h-4 bg-slate-400/20 mx-1"></div>
                                <button
                                    onClick={() => setSortOrder(sortOrder === 'asc' ? 'none' : 'asc')}
                                    className={`liquid-glass-btn ${sortOrder === 'asc' ? 'active' : ''}`}
                                    title={t('sortAsc')}
                                >
                                    <ArrowUp className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => setSortOrder(sortOrder === 'desc' ? 'none' : 'desc')}
                                    className={`liquid-glass-btn ${sortOrder === 'desc' ? 'active' : ''}`}
                                    title={t('sortDesc')}
                                >
                                    <ArrowDown className="w-4 h-4" />
                                </button>
                            </div>
                        }
                    >
                        <div className="flex flex-col flex-1 min-h-0">
                            <div className="mb-4 shrink-0 relative z-20">
                                <FundSearch
                                    onAddFund={async (code, name) => {
                                        if (!session?.accessToken) {
                                            console.warn("No access token available to add to watchlist.");
                                            return;
                                        }
                                        if (!watchlist.some(i => i.code === code)) {
                                            try {
                                                const res = await authenticatedFetch('/api/watchlist', session, {
                                                    method: 'POST',
                                                    headers: { 
                                                        'Content-Type': 'application/json'
                                                    },
                                                    body: JSON.stringify({ code, name })
                                                });
                                                const data = await res.json();
                                                if (data.success) {
                                                    // Optimistically update watchlist
                                                    mutateWatchlist([{ code, name }, ...(watchlistData || [])], false);
                                                    setSelectedFund(code);
                                                    setIsWatchlistOpen(false); // Auto-close on selection
                                                }
                                            } catch (err) {
                                                console.error('Failed to add to watchlist:', err);
                                            }
                                        } else {
                                            setSelectedFund(code);
                                            setIsWatchlistOpen(false);
                                        }
                                    }}
                                    existingCodes={watchlist.map(w => w.code)}
                                />
                            </div>

                            <div className="flex-1 overflow-y-auto min-h-0 space-y-2 pr-1 custom-scrollbar max-h-[400px] lg:max-h-96">
                                {watchlist
                                    .slice() // Create a copy to avoid mutating state
                                    .sort((a, b) => {
                                        if (a.estimated_growth === undefined && b.estimated_growth === undefined) return 0;
                                        if (a.estimated_growth === undefined) return -1;
                                        if (b.estimated_growth === undefined) return 1;

                                        if (sortOrder === 'none') return 0;

                                        const valA = a.estimated_growth;
                                        const valB = b.estimated_growth;

                                        return sortOrder === 'desc'
                                            ? valB - valA
                                            : valA - valB;
                                    })
                                    .map(item => (
                                        <div
                                            key={item.code}
                                            onClick={() => {
                                                setSelectedFund(item.code);
                                                setIsWatchlistOpen(false);
                                            }}
                                            className={`group flex items-center justify-between p-3 rounded-md transition-all cursor-pointer ${selectedFund === item.code
                                                ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400'
                                                : 'bg-white dark:bg-transparent border border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/50 text-slate-900 dark:text-slate-200'
                                                }`}
                                        >
                                            <div className="flex flex-col overflow-hidden flex-1">
                                                <div className="flex items-center justify-between gap-2">
                                                    <div className="flex items-center gap-2 overflow-hidden">
                                                        <span className="font-bold text-sm truncate">{item.name || item.code}</span>
                                                        {/* Risk Grades */}
                                                        {item.stats && (
                                                            <div className="flex gap-1 shrink-0">
                                                                <span className={`text-[8px] font-black px-1 rounded-sm ${
                                                                    item.stats.sharpe_grade === 'S' ? 'bg-amber-500/10 text-amber-600' :
                                                                    item.stats.sharpe_grade === 'A' ? 'bg-blue-500/10 text-blue-600' :
                                                                    'bg-slate-500/10 text-slate-500'
                                                                }`} title={`Sharpe: ${item.stats.sharpe_grade}`}>S:{item.stats.sharpe_grade}</span>
                                                                <span className={`text-[8px] font-black px-1 rounded-sm ${
                                                                    item.stats.drawdown_grade === 'S' ? 'bg-emerald-500/10 text-emerald-600' :
                                                                    item.stats.drawdown_grade === 'A' ? 'bg-cyan-500/10 text-cyan-600' :
                                                                    'bg-slate-500/10 text-slate-500'
                                                                }`} title={`Drawdown: ${item.stats.drawdown_grade}`}>D:{item.stats.drawdown_grade}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                    {item.estimated_growth !== undefined && (
                                                        <div className="flex items-center gap-1 shrink-0">
                                                            <span className={`font-mono text-xs font-bold ${item.estimated_growth >= 0 ? 'text-rose-600' : 'text-emerald-600'
                                                                }`}>
                                                                {item.estimated_growth > 0 ? '+' : ''}{item.estimated_growth.toFixed(2)}%
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="flex items-center justify-between gap-2 mt-0.5">
                                                    <div className="flex items-center gap-1">
                                                        <span className="font-mono text-[10px] opacity-60">{item.code}</span>
                                                        {item.source && (
                                                            <div className="flex gap-1" title={t('sourceLabel', { source: item.source })}>
                                                                {item.source.includes('Calibration') && (
                                                                    <Scale className="w-3 h-3 text-blue-500" />
                                                                )}
                                                                {item.source.includes('ETF') && (
                                                                    <Anchor className="w-3 h-3 text-blue-500" />
                                                                )}
                                                                {(item.code === '002207' || item.code === '022365') && (
                                                                    <AlertTriangle className="w-3 h-3 text-amber-500" />
                                                                )}
                                                                {!item.source.includes('Calibration') && !item.source.includes('ETF') && item.code !== '002207' && item.code !== '022365' && (
                                                                    <Target className="w-3 h-3 text-emerald-500" />
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                    
                                                    {/* Sparkline */}
                                                    {item.stats?.sparkline_data && (
                                                        <FundSparkline 
                                                            data={item.stats.sparkline_data} 
                                                            width={60} 
                                                            height={16}
                                                            isPositive={item.stats.return_1m >= 0}
                                                            className="opacity-60 group-hover:opacity-100 transition-opacity"
                                                        />
                                                    )}
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2 shrink-0 ml-2">
                                                {selectedFund === item.code && loading && <RefreshCw className="w-3 h-3 animate-spin" />}
                                                <button
                                                    onClick={(e) => handleDelete(e, item.code)}
                                                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full text-slate-400 hover:text-slate-900 transition-colors"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    ))}

                            </div>
                        </div>
                    </Card>
                </div>

                {/* Right: Details */}
                <div className="lg:col-span-8 flex flex-col gap-6 min-h-0 lg:overflow-y-auto lg:pr-2 custom-scrollbar">
                    {valuation ? (
                        <div className="flex flex-col gap-6">
                            {/* Main KPI Card */}
                            <div className="flex flex-col md:grid md:grid-cols-3 gap-4">
                                <Card className="md:col-span-2 relative overflow-hidden bg-white dark:bg-slate-900/40">
                                    <div className="flex flex-col h-full justify-between z-10 relative">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <h2 className="text-xs font-mono text-slate-500 dark:text-slate-400 uppercase tracking-widest">{t('estimatedGrowth')}</h2>
                                                <div className="text-4xl lg:text-5xl font-black mt-2 tracking-tighter flex items-center gap-2">
                                                    <span className={valuation.estimated_growth >= 0 ? "text-rose-600 dark:text-rose-500" : "text-emerald-600 dark:text-emerald-500"}>
                                                        {valuation.estimated_growth > 0 ? "+" : ""}{valuation.estimated_growth.toFixed(2)}%
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={handleManualRefresh}
                                                    disabled={loading}
                                                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                                    title={t('refreshData')}
                                                >
                                                    <RefreshCw className={`w-4 h-4 text-slate-400 dark:text-slate-500 transition-transform ${loading ? 'animate-spin' : ''}`} />
                                                </button>
                                                {valuation.status === 'syncing' ? (
                                                    <Badge variant="warning">
                                                        {t('syncing') || 'Syncing'}
                                                    </Badge>
                                                ) : (
                                                    <Badge variant={valuation.estimated_growth >= 0 ? 'bullish' : 'bearish'}>
                                                        {t('live')}
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                        {valuation.status === 'syncing' && (
                                            <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5 animate-pulse">
                                                <RefreshCw className="w-3 h-3 animate-spin" />
                                                {valuation.message || 'Fetching holdings in background...'}
                                            </div>
                                        )}
                                        <div className="mt-4 text-[10px] lg:text-xs text-slate-500 dark:text-slate-400 font-mono">
                                            {t('basedOn', { count: valuation.components?.length || 0, weight: valuation.total_weight?.toFixed(1) || '0.0' })}
                                            <br />
                                            {t('lastUpdated', { time: lastUpdated ? lastUpdated.toLocaleTimeString() : '' })}
                                            {/* Source & Calibration Note */}
                                            {valuation.source && (
                                                <div className="mt-1 opacity-70">
                                                    {t('sourceLabel', { source: valuation.source ?? '' })}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    {/* Background Accents (Subtle) */}
                                    <div className={`absolute -right-10 -top-10 w-40 h-40 blur-3xl opacity-5 rounded-full ${valuation.estimated_growth >= 0 ? 'bg-rose-500' : 'bg-emerald-500'}`}></div>
                                </Card>

                                <Card>
                                    <h2 className="text-sm font-mono text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-4">{t('topDrivers')}</h2>
                                    <div className="flex flex-col gap-2">
                                        {valuation.components?.length > 0 ? (
                                            valuation.components
                                                .sort((a: ComponentStock, b: ComponentStock) => Math.abs(b.impact) - Math.abs(a.impact))
                                                .slice(0, 3)
                                                .map((comp: ComponentStock) => (
                                                    <div key={comp.code} className="flex justify-between items-center text-xs border-b border-slate-100 dark:border-slate-800/50 pb-2 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1 rounded">
                                                        <div className="flex gap-2">
                                                            <span className="font-mono text-slate-500 dark:text-slate-600">{comp.code}</span>
                                                            <span className="text-slate-700 dark:text-slate-300 truncate max-w-[100px] font-medium">{comp.name}</span>
                                                        </div>
                                                        <span className={`font-mono font-bold ${comp.impact >= 0 ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500'}`}>
                                                            {comp.impact > 0 ? "+" : ""}{comp.impact.toFixed(3)}%
                                                        </span>
                                                    </div>
                                                ))
                                        ) : (
                                            <div className="text-xs text-slate-400 dark:text-slate-600 italic py-2">
                                                {valuation.status === 'syncing' ? t('syncingData') || 'Synchronizing holdings...' : t('noComponents') || 'No data'}
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            </div>

                            {/* Attribution & History Tabs */}
                            <Card
                                title={
                                    <div className="flex items-center gap-4 overflow-x-auto no-scrollbar py-1">
                                        <button
                                            onClick={() => setActiveTab('attribution')}
                                            className={`whitespace-nowrap pb-2 px-1 text-sm font-bold transition-all border-b-2 ${activeTab === 'attribution' ? 'border-blue-600 dark:border-blue-500 text-slate-900 dark:text-slate-100' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                                        >
                                            {t('attribution')}
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('sector')}
                                            className={`whitespace-nowrap pb-2 px-1 text-sm font-bold transition-all border-b-2 ${activeTab === 'sector' ? 'border-blue-600 dark:border-blue-500 text-slate-900 dark:text-slate-100' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                                        >
                                            {t('sectorAttribution')}
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('history')}
                                            className={`whitespace-nowrap pb-2 px-1 text-sm font-bold transition-all border-b-2 ${activeTab === 'history' ? 'border-blue-600 dark:border-blue-500 text-slate-900 dark:text-slate-100' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                                        >
                                            {t('valuationReview')}
                                        </button>
                                    </div>
                                }
                                className="lg:flex-1 lg:flex lg:flex-col"
                                contentClassName="lg:flex-1 p-0"
                            >
                                <div className="w-full overflow-hidden">
                                    {activeTab === 'attribution' && (
                                        <div className="max-h-[50vh] lg:max-h-[60vh] overflow-y-auto overflow-x-auto custom-scrollbar">
                                            <table className="w-full min-w-[500px] text-left border-collapse text-sm">
                                                <thead className="sticky top-0 bg-white dark:bg-slate-900 z-30">
                                                    <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-[10px] uppercase tracking-wider shadow-sm bg-slate-50/80 dark:bg-slate-900/80 backdrop-blur">
                                                        <th className="p-3 sticky left-0 top-0 z-40 bg-slate-50/95 dark:bg-slate-900/95 backdrop-blur">{t('tableStock')}</th>
                                                        <th className="p-3 text-right">{t('tablePrice')}</th>
                                                        <th className="p-3 text-right">{t('tableChange')}</th>
                                                        <th className="p-3 text-right">{t('tableWeight')}</th>
                                                        <th className="p-3 text-right">{t('tableImpact')}</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                                                    {valuation.components?.length > 0 ? (
                                                        valuation.components
                                                            .slice()
                                                            .sort((a: ComponentStock, b: ComponentStock) => b.weight - a.weight)
                                                            .map((comp: ComponentStock) => (
                                                                <tr key={comp.code} className="group hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                                                    <td className="p-3 sticky left-0 z-10 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur border-r border-slate-100 dark:border-slate-800/50 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)]">
                                                                        <div className="flex flex-col">
                                                                            <span className="font-bold text-slate-800 dark:text-slate-200 text-xs sm:text-sm whitespace-nowrap">{comp.name}</span>
                                                                            <span className="text-[9px] sm:text-[10px] font-mono text-slate-500 dark:text-slate-500">{comp.code}</span>
                                                                        </div>
                                                                    </td>
                                                                    <td className="p-3 text-right font-mono text-slate-600 dark:text-slate-400">
                                                                        {comp.price.toFixed(2)}
                                                                    </td>
                                                                    <td className={`p-3 text-right font-mono font-bold ${comp.change_pct >= 0 ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500'}`}>
                                                                        {comp.change_pct > 0 ? "+" : ""}{comp.change_pct.toFixed(2)}%
                                                                    </td>
                                                                    <td className="p-3 text-right font-mono text-slate-500 dark:text-slate-500">
                                                                        {comp.weight.toFixed(2)}%
                                                                    </td>
                                                                    <td className={`p-3 text-right font-mono font-bold ${comp.impact >= 0 ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500'}`}>
                                                                        {comp.impact > 0 ? "+" : ""}{comp.impact.toFixed(3)}%
                                                                    </td>
                                                                </tr>
                                                            ))
                                                    ) : (
                                                        <tr>
                                                            <td colSpan={5} className="p-12 text-center text-slate-400 dark:text-slate-600">
                                                                <div className="flex flex-col items-center gap-2">
                                                                    <RefreshCw className={`w-6 h-6 ${valuation.status === 'syncing' ? 'animate-spin' : ''} opacity-20`} />
                                                                    <p className="text-sm">
                                                                        {valuation.status === 'syncing' ? t('syncingMsg') || 'Holdings are being synchronized from Market Source...' : t('noData') || 'No components available'}
                                                                    </p>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    )}
                                                </tbody>
                                            </table>
                                        </div>)}

                                    {activeTab === 'sector' && (
                                        <div className="flex flex-col p-2 lg:p-4">
                                            {valuation.sector_attribution && (
                                                <SectorAttribution data={valuation.sector_attribution} />
                                            )}
                                        </div>
                                    )}

                                    {activeTab === 'history' && (
                                        <div className="flex flex-col">
                                            {historyLoading ? (
                                                <div className="flex-1 flex items-center justify-center py-12">
                                                    <RefreshCw className="w-6 h-6 animate-spin text-slate-300 dark:text-slate-700" />
                                                </div>
                                            ) : history.length > 0 ? (
                                                <div className="max-h-[50vh] lg:max-h-[60vh] overflow-y-auto overflow-x-auto custom-scrollbar">
                                                    <table className="w-full min-w-[500px] text-left border-collapse text-sm">
                                                        <thead className="sticky top-0 bg-white dark:bg-slate-900 z-30">
                                                            <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-[10px] uppercase tracking-wider shadow-sm bg-slate-50/80 dark:bg-slate-900/80 backdrop-blur">
                                                                <th className="p-3 sticky left-0 top-0 z-40 bg-slate-50/95 dark:bg-slate-900/95 backdrop-blur">{t('tableDate')}</th>
                                                                <th className="p-3 text-right">{t('tableEst')}</th>
                                                                <th className="p-3 text-right">{t('tableOfficial')}</th>
                                                                <th className="p-3 text-right">{t('tableDeviation')}</th>
                                                                <th className="p-3 text-center">{t('tableStatus')}</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                                                            {history.map((h, i) => (
                                                                <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                                                    <td className="p-3 sticky left-0 z-10 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur border-r border-slate-100 dark:border-slate-800/50 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)] font-mono text-slate-600 dark:text-slate-400 text-xs whitespace-nowrap">{h.trade_date}</td>
                                                                    <td className={`p-3 text-right font-mono font-bold ${h.frozen_est_growth >= 0 ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500'}`}>
                                                                        {h.frozen_est_growth > 0 ? "+" : ""}{Number(h.frozen_est_growth).toFixed(2)}%
                                                                    </td>
                                                                    <td className={`p-3 text-right font-mono font-bold ${h.official_growth >= 0 ? 'text-rose-600 dark:text-rose-500' : 'text-emerald-600 dark:text-emerald-500'}`}>
                                                                        {h.official_growth > 0 ? "+" : ""}{Number(h.official_growth).toFixed(2)}%
                                                                    </td>
                                                                    <td className="p-3 text-right font-mono text-slate-500 dark:text-slate-500">
                                                                        {h.deviation > 0 ? "+" : ""}{Number(h.deviation).toFixed(2)}%
                                                                    </td>
                                                                    <td className="p-3 text-center">
                                                                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${h.tracking_status === 'S' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' :
                                                                            h.tracking_status === 'A' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400' :
                                                                                h.tracking_status === 'B' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' :
                                                                                    'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400'
                                                                            }`}>
                                                                            {t(`accuracy${h.tracking_status}`)}
                                                                        </span>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            ) : (
                                                <div className="flex-1 flex flex-col items-center justify-center py-12 text-slate-400 dark:text-slate-600">
                                                    <div className="bg-slate-50 dark:bg-slate-900 p-4 rounded-full mb-4">
                                                        <Anchor className="w-8 h-8 opacity-20" />
                                                    </div>
                                                    <p className="text-sm font-medium">{t('noHistoryTitle')}</p>
                                                    <p className="text-xs opacity-60 mt-1 uppercase tracking-tight">{t('noHistoryDesc')}</p>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </Card>
                        </div>
                    ) : (
                        <div className="h-64 flex items-center justify-center text-slate-500">
                            {loading ? t('loading') : t('selectFund')}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}