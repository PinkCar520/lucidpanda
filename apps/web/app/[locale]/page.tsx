'use client';

import React, { useMemo, useCallback, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';

import Chart from '@/components/Chart';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/Alert';
import { Intelligence } from '@/lib/db';
import { Radio, Zap, Search, X, Terminal, AlertTriangle } from 'lucide-react';

import LanguageSwitcher from '@/components/LanguageSwitcher';
import AINarrativeTicker from '@/components/AINarrativeTicker';
import SystemStatus from '@/components/SystemStatus';
import TradingViewTickerTape from '@/components/TradingViewTickerTape';
import TradingViewMiniCharts from '@/components/TradingViewMiniCharts';
import BacktestStats from '@/components/BacktestStats';
import { useSSE } from '@/hooks/useSSE';
import VirtualizedIntelligenceList from '@/components/VirtualizedIntelligenceList';
import VirtualizedStrategyTable from '@/components/VirtualizedStrategyTable';
import { Link } from '@/i18n/navigation';
import { useSearchParams } from 'next/navigation';
import { useIntelligenceInfiniteQuery } from '@/hooks/api/use-intelligence-query';
import { useStrategyInfiniteQuery } from '@/hooks/api/use-strategy-query';
import { useMarketQuery } from '@/hooks/api/use-market-query';
import { useQueryClient } from '@tanstack/react-query';
import { intelligenceKeys } from '@/lib/query-keys';


export default function Dashboard({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = React.use(params);
  useSession();
  const searchParams = useSearchParams();
  const focusedCode = searchParams.get('code');
  const queryClient = useQueryClient();

  const t = useTranslations('Dashboard');
  const tTable = useTranslations('Table');
  const tSentiment = useTranslations('Sentiment');

  // Sidebar Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'all' | 'essential' | 'bearish'>('all');

  // --- TanStack Query for Intelligence ---
  const {
    data: infiniteIntelData,
    fetchNextPage: fetchNextIntelPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: intelLoading
  } = useIntelligenceInfiniteQuery({ mode: filterMode, search: searchQuery });

  // --- TanStack Query for Strategy Matrix ---
  const {
    data: infiniteStrategyData,
    fetchNextPage: fetchNextStrategyPage,
    hasNextPage: hasNextStrategyPage,
    isFetchingNextPage: isFetchingNextStrategyPage,
  } = useStrategyInfiniteQuery();

  const [chartConfig, setChartConfig] = useState({ range: '1mo', interval: '60m' });

  // --- TanStack Query for Market Data ---
  const { data: marketData, isLoading: marketLoading } = useMarketQuery('GC=F', chartConfig.range, chartConfig.interval);

  // Flatten the pages into a single items array
  const allIntelligence = useMemo(() => {
    return infiniteIntelData?.pages.flatMap(page => page.data) || [];
  }, [infiniteIntelData]);

  const allStrategies = useMemo(() => {
    return infiniteStrategyData?.pages.flatMap(page => page.data) || [];
  }, [infiniteStrategyData]);

  const [globalHighUrgency, setGlobalHighUrgency] = useState(0);

  const [activeTab, setActiveTab] = useState<'feed' | 'charts'>('feed');

  // SSE callbacks - memoized to prevent infinite reconnection loop
  const handleSSEMessage = useCallback((newItems: Intelligence[]) => {
    if (newItems.length > 0) {
      // 1. Update Intelligence Stream Cache
      queryClient.setQueryData(intelligenceKeys.infinite({ mode: filterMode, search: searchQuery }), (old: { pages: { data: Intelligence[] }[] } | undefined) => {
        if (!old || !old.pages || old.pages.length === 0) return old;
        const newPages = [...old.pages];
        newPages[0] = { ...newPages[0], data: [...newItems, ...newPages[0].data] };
        return { ...old, pages: newPages };
      });

      // 2. Update Strategy Matrix Cache
      queryClient.setQueryData(['intelligence', 'strategy-matrix', 'infinite'], (old: { pages: { data: Intelligence[] }[] } | undefined) => {
        if (!old || !old.pages || old.pages.length === 0) return old;
        const newPages = [...old.pages];
        newPages[0] = { ...newPages[0], data: [...newItems, ...newPages[0].data] };
        return { ...old, pages: newPages };
      });

      // 3. 更新全局高分警报数
      const newUrgencyCount = newItems.filter(i => i.urgency_score >= 8).length;
      if (newUrgencyCount > 0) {
        setGlobalHighUrgency(prev => prev + newUrgencyCount);
      }

      console.log(`[SSE] Received ${newItems.length} new intelligence items`);
    }
  }, [queryClient, filterMode, searchQuery, setGlobalHighUrgency]);

  const handleSSEError = useCallback((err: Event) => {
    console.error('[SSE] Connection error:', err);
  }, []);

  const isLoading = marketLoading || intelLoading;

  // SSE Connection for real-time updates
  useSSE({
    url: '/api/v1/intelligence/stream',
    enabled: !isLoading, // Only connect after initial load
    onMessage: handleSSEMessage,
    onError: handleSSEError
  });

  // Helper function to extract localized text from JSON strings or objects
  const getLocalizedText = useCallback((input: unknown, currentLocale: string) => {
    let data = input;

    // If input is string, try to parse it (compatibility for SQLite/legacy)
    if (typeof input === 'string') {
      try {
        data = JSON.parse(input);
      } catch {
        return input;
      }
    }

    // If it's already an object (Postgres JSONB), or successfully parsed
    if (typeof data === 'object' && data !== null) {
      const records = data as Record<string, string>;
      return records[currentLocale] || records['en'] || records['zh'] || Object.values(records)[0] || '';
    }

    return String(data || '');
  }, []);

  // Helper function to detect bearish sentiment (language-agnostic)
  const isBearishSentiment = useCallback((sentimentInput: unknown) => {
    const bearishKeywords = ['鹰', '利空', '下跌', 'Bearish', 'Hawkish', 'Pressure'];

    let sentimentStr = '';
    if (typeof sentimentInput === 'string') {
      sentimentStr = sentimentInput;
    } else if (typeof sentimentInput === 'object' && sentimentInput !== null) {
      sentimentStr = JSON.stringify(sentimentInput);
    }

    return bearishKeywords.some(keyword => sentimentStr.includes(keyword));
  }, []);

  if (isLoading) return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-[#020617]">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-slate-200 dark:border-slate-800 rounded-full"></div>
          <div className="w-16 h-16 border-4 border-blue-600 dark:border-emerald-500 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
        </div>
        <p className="text-slate-500 dark:text-slate-400 font-mono text-sm tracking-widest animate-pulse">{t('loading')}</p>
      </div>
    </div>
  );

  return (
    <div className="p-4 md:p-6 lg:p-8 flex flex-col gap-6 h-screen overflow-hidden">
      
      {focusedCode && (
          <div className="animate-in slide-in-from-top-4 duration-500">
              <Alert variant="info" className="bg-indigo-500/10 border-indigo-500/30 text-indigo-600 dark:text-indigo-400 py-3 shadow-lg shadow-indigo-500/5">
                  <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-indigo-500 text-white flex items-center justify-center shadow-lg shadow-indigo-500/20">
                              <Terminal className="w-4 h-4" />
                          </div>
                          <div>
                              <div className="text-[10px] font-bold uppercase tracking-widest opacity-70">{t('contextAlert.title')}</div>
                              <div className="text-sm font-black font-data tracking-tight">{t('contextAlert.message', { code: focusedCode })}</div>
                          </div>
                      </div>
                      <Link href="/">
                          <button className="p-1.5 hover:bg-indigo-500/20 rounded-full transition-colors">
                              <X className="w-4 h-4" />
                          </button>
                      </Link>
                  </div>
              </Alert>
          </div>
      )}

      {/* 2. Sticky Toolbar (Tactical Cockpit: Alerts + Regime + Mini Charts) */}
      <div className="sticky top-0 z-50 bg-white/95 dark:bg-[#020617]/95 backdrop-blur-md border-b border-slate-200 dark:border-slate-800/50 -mx-4 px-4 md:-mx-6 md:px-6 lg:-mx-8 lg:px-8 py-2 mb-6 shadow-2xl shadow-black/5">
        {/* Mobile Tab Switcher */}
        <div className="flex lg:hidden w-full bg-slate-100 dark:bg-slate-900/50 rounded-lg p-1 mb-3 border border-slate-200 dark:border-slate-800/50">
          <button
            onClick={() => setActiveTab('feed')}
            className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all flex items-center justify-center gap-2 relative ${activeTab === 'feed'
              ? 'bg-blue-600 dark:bg-emerald-500 text-white shadow-lg'
              : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
          >
            <div className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5" />
              <span>{t('liveFeedLabel')}</span>
              {globalHighUrgency > 0 && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full bg-rose-500 text-white text-[9px] font-black leading-none">
                  {globalHighUrgency}
                </span>
              )}
            </div>
          </button>
          <button
            onClick={() => setActiveTab('charts')}
            className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all flex items-center justify-center gap-2 ${activeTab === 'charts'
              ? 'bg-blue-600 dark:bg-emerald-500 text-white shadow-lg'
              : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
          >
            <Zap className="w-3.5 h-3.5" />
            {t('dataVisualization')}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-auto lg:h-[72px]">

          {/* Left: Alerts + System Status */}
          <div className="hidden lg:flex lg:col-span-4 h-full items-stretch gap-2">
            <AINarrativeTicker 
                items={allIntelligence} 
                locale={locale}
                getLocalizedText={getLocalizedText}
            />
          </div>

          {/* Middle: Live Market Snapshot (Mini Charts) */}
          <div className="lg:col-span-5 h-full flex items-center overflow-x-auto no-scrollbar gap-4 px-2">
             <TradingViewTickerTape />
             <TradingViewMiniCharts />
          </div>

          {/* Right: Global Ops / Status / Time */}
          <div className="lg:col-span-3 h-full flex items-center justify-end gap-3 pr-2">
             <SystemStatus />
             <div className="w-px h-6 bg-slate-200 dark:bg-slate-800 hidden sm:block"></div>
             <LanguageSwitcher />
          </div>

        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left Sidebar: Feed Filters & Stats */}
        <div className={`lg:col-span-3 flex flex-col gap-4 min-h-0 ${activeTab === 'feed' ? 'flex' : 'hidden lg:flex'
          }`}>
          <div className="bg-slate-50/50 dark:bg-slate-900/20 rounded-xl p-3 border border-slate-200/60 dark:border-slate-800/60 flex flex-col gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder={t('searchPlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full">
                  <X className="w-3 h-3 text-slate-400" />
                </button>
              )}
            </div>

            {/* Filter Toggles */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setFilterMode('all')}
                className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md border transition-all ${filterMode === 'all'
                  ? 'bg-blue-600 dark:bg-slate-700 text-white border-blue-700 dark:border-slate-600 shadow-md'
                  : 'bg-transparent text-slate-500 dark:text-slate-500 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
              >
                {t('filterAll')}
              </button>
              <button
                onClick={() => setFilterMode('essential')}
                className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md border transition-all ${filterMode === 'essential'
                  ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400 border-rose-500/50'
                  : 'bg-transparent text-slate-500 dark:text-slate-500 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
              >
                {t('filterEssential')}
              </button>
              <button
                onClick={() => setFilterMode('bearish')}
                className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md border transition-all ${filterMode === 'bearish'
                  ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/50'
                  : 'bg-transparent text-slate-500 dark:text-slate-500 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
              >
                {t('filterBearish')}
              </button>
            </div>

            <div className="flex items-center justify-between mt-1">
              <h2 className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                <Radio className="w-3 h-3 text-blue-500 dark:text-emerald-500" /> {t('liveFeedLabel')}
              </h2>
              <Badge variant="neutral" className="text-[10px] h-5">{allIntelligence.length}</Badge>
            </div>
          </div>

          {/* Virtualized Infinite List */}
          <VirtualizedIntelligenceList
            items={allIntelligence}
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            fetchNextPage={fetchNextIntelPage}
            locale={locale}
            getLocalizedText={getLocalizedText}
            t={t}
            tSentiment={tSentiment}
            isBearishSentiment={isBearishSentiment}
          />
        </div>

        {/* Right: Visualization & Data */}
        <div className={`lg:col-span-9 flex flex-col gap-6 ${activeTab === 'charts' ? 'flex' : 'hidden lg:flex'
          }`}>
          <Chart
            marketData={marketData}
            intelligence={allIntelligence}
            onRangeChange={(range, interval) => setChartConfig({ range, interval })}
          />

          {/* AI Backtest Stats - Minimal Contextual Insight Mode */}
          <BacktestStats intelligence={allIntelligence} marketData={marketData} minimal={true} />

          {/* Strategy Matrix (Virtualized Infinite Log) */}
          <Card title={tTable('title')} id="tactical-matrix">
            <VirtualizedStrategyTable
                items={allStrategies}
                hasNextPage={hasNextStrategyPage}
                isFetchingNextPage={isFetchingNextStrategyPage}
                fetchNextPage={fetchNextStrategyPage}
                locale={locale}
                getLocalizedText={getLocalizedText}
                tTable={tTable}
            />
          </Card>
        </div>
      </div>

      {/* Global Alerts for High Urgency Items */}
      {globalHighUrgency > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] w-[90%] max-w-md animate-in slide-in-from-bottom-4">
            <Alert variant="destructive" className="animate-bounce border-rose-500 bg-rose-500/10 text-rose-600 dark:text-rose-400 shadow-2xl">
              <AlertTriangle className="h-4 w-4" />
              <div className="flex justify-between items-center w-full">
                <span>{t('highUrgencyAlert', { count: globalHighUrgency })}</span>
                <button onClick={() => setGlobalHighUrgency(0)} className="p-1 hover:bg-rose-500/20 rounded-full">
                  <X className="w-3 h-3" />
                </button>
              </div>
            </Alert>
        </div>
      )}
    </div>
  );
}
