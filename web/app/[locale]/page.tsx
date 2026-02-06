'use client';

import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Alert } from '@/components/Alert';

import Chart from '@/components/Chart';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Intelligence } from '@/lib/db';
import { AlertTriangle, Radio, ExternalLink, Zap, Search, Filter, X } from 'lucide-react';

import LanguageSwitcher from '@/components/LanguageSwitcher';
import AINarrativeTicker from '@/components/AINarrativeTicker';
import SystemStatus from '@/components/SystemStatus';
import TradingViewTickerTape from '@/components/TradingViewTickerTape';
import TradingViewMiniCharts from '@/components/TradingViewMiniCharts';
import BacktestStats from '@/components/BacktestStats';
import { useSSE } from '@/hooks/useSSE';
import IntelligenceCard from '@/components/IntelligenceCard';
import Paginator from '@/components/Paginator';


export default function Dashboard({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = React.use(params);

  const t = useTranslations('Dashboard');
  const tTable = useTranslations('Table');
  const tSentiment = useTranslations('Sentiment');

  const [liveIntelligence, setLiveIntelligence] = useState<Intelligence[]>([]);
  const [tableIntelligence, setTableIntelligence] = useState<Intelligence[]>([]);
  const [marketData, setMarketData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [globalHighUrgency, setGlobalHighUrgency] = useState(0);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [itemsPerPage, setItemsPerPage] = useState(20);

  const [chartConfig, setChartConfig] = useState({ range: '1mo', interval: '60m' });
  const [activeTab, setActiveTab] = useState<'feed' | 'charts'>('feed');

  // SSE callbacks - memoized to prevent infinite reconnection loop
  const handleSSEMessage = useCallback((newItems: Intelligence[]) => {
    if (newItems.length > 0) {
      // 1. 始终更新实时流 (只保留最新的 100 条)
      setLiveIntelligence(prev => {
        const merged = [...newItems, ...prev];
        return merged.slice(0, 100);
      });

      // 2. 如果在第一页，也更新表格 (维持无感实时更新)
      if (currentPage === 1) {
        setTableIntelligence(prev => {
          const merged = [...newItems, ...prev];
          return merged.slice(0, itemsPerPage);
        });
      }

      // 3. 更新全局高分警报数
      const newUrgencyCount = newItems.filter(i => i.urgency_score >= 8).length;
      if (newUrgencyCount > 0) {
        setGlobalHighUrgency(prev => prev + newUrgencyCount);
      }

      console.log(`[SSE] Received ${newItems.length} new intelligence items`);
    }
  }, [currentPage, itemsPerPage]);

  const handleSSEError = useCallback((err: Event) => {
    console.error('[SSE] Connection error:', err);
  }, []);

  // SSE Connection for real-time updates
  const { isConnected, error: sseError } = useSSE({
    url: '/api/sse/intelligence/stream',
    enabled: !loading, // Only connect after initial load
    onMessage: handleSSEMessage,
    onError: handleSSEError
  });

  // Sidebar Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'all' | 'essential' | 'bearish'>('all');

  // Helper function to extract localized text from JSON strings or objects
  const getLocalizedText = useCallback((input: any, currentLocale: string) => {
    let data = input;

    // If input is string, try to parse it (compatibility for SQLite/legacy)
    if (typeof input === 'string') {
      try {
        data = JSON.parse(input);
      } catch (e) {
        return input;
      }
    }

    // If it's already an object (Postgres JSONB), or successfully parsed
    if (typeof data === 'object' && data !== null) {
      return data[currentLocale] || data['en'] || data['zh'] || Object.values(data)[0] || '';
    }

    return String(data || '');
  }, []);

  // Helper function to detect bearish sentiment (language-agnostic)
  const isBearishSentiment = useCallback((sentimentInput: any) => {
    const bearishKeywords = ['鹰', '利空', '下跌', 'Bearish', 'Hawkish', 'Pressure'];

    let sentimentStr = '';
    if (typeof sentimentInput === 'string') {
      sentimentStr = sentimentInput;
    } else if (typeof sentimentInput === 'object' && sentimentInput !== null) {
      sentimentStr = JSON.stringify(sentimentInput);
    }

    return bearishKeywords.some(keyword => sentimentStr.includes(keyword));
  }, []);

  // Filter Logic with useMemo (只过滤实时流)
  const filteredLiveIntelligence = useMemo(() => {
    const now = Date.now();
    const ONE_DAY_MS = 24 * 60 * 60 * 1000;

    return liveIntelligence.filter(item => {
      // 0. Smart Archiving (Quant Standard)
      // Rule: Hide items > 24h UNLESS urgency >= 8 (Major Macro Context)
      const itemTime = new Date(item.timestamp).getTime();
      const isOld = (now - itemTime) > ONE_DAY_MS;
      const isMajor = item.urgency_score >= 8;

      if (isOld && !isMajor) return false;

      // 1. Text Search
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const summaryText = getLocalizedText(item.summary, locale).toLowerCase();
        const contentText = getLocalizedText(item.content, locale).toLowerCase();
        const authorText = item.author.toLowerCase();
        const sentimentText = getLocalizedText(item.sentiment, locale).toLowerCase();

        const textMatch =
          summaryText.includes(q) ||
          contentText.includes(q) ||
          authorText.includes(q) ||
          sentimentText.includes(q);

        if (!textMatch) return false;
      }

      // 2. Mode Filter
      if (filterMode === 'essential') return item.urgency_score >= 8;
      if (filterMode === 'bearish') return isBearishSentiment(item.sentiment);

      return true;
    });
  }, [liveIntelligence, searchQuery, filterMode, locale, getLocalizedText, isBearishSentiment]);



  const [latestIntelId, setLatestIntelId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    async function fetchData(isInitialLoad = false) {
      try {
        // Build intelligence API URL with incremental update support
        const intelUrl = isInitialLoad || !latestIntelId
          ? '/api/intelligence?limit=100'
          : `/api/intelligence?since_id=${latestIntelId}&limit=50`;

        const [intelRes, marketRes] = await Promise.all([
          fetch(intelUrl),
          fetch(`/api/market?symbol=GC=F&range=${chartConfig.range}&interval=${chartConfig.interval}`)
        ]);

        const intelResponse = await intelRes.json();
        const mData = await marketRes.json();

        // Handle intelligence data (now returns {data, latest_id, count})
        if (intelResponse.data) {
          if (isInitialLoad || !latestIntelId) {
            // 初始加载：同时填充实时流和表格第一页
            setLiveIntelligence(intelResponse.data.slice(0, 100));
            setTableIntelligence(intelResponse.data.slice(0, itemsPerPage));
          } else if (intelResponse.count > 0) {
            // 增量更新 (轮询回退)
            setLiveIntelligence(prev => [...intelResponse.data, ...prev].slice(0, 100));
            if (currentPage === 1) {
              setTableIntelligence(prev => [...intelResponse.data, ...prev].slice(0, itemsPerPage));
            }
          }

          // Update latest ID tracker
          if (intelResponse.latest_id) {
            setLatestIntelId(intelResponse.latest_id);
          }
        }

        setMarketData(mData);
      } catch (err: any) {
        console.error('Fetch error:', err);
        const errorMessage = err.message || 'Failed to load data. Please check your connection.';
        setError(errorMessage);

        // Auto-retry logic (max 3 attempts)
        if (retryCount < 3) {
          console.log(`[Error] Auto-retry ${retryCount + 1}/3 in 5 seconds...`);
          setTimeout(() => {
            setRetryCount(prev => prev + 1);
            setError(null);
            fetchData(isInitialLoad);
          }, 5000);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData(true); // Initial load
    const intervalId = setInterval(() => fetchData(false), 30000); // Poll every 30s (reduced from 60s)
    return () => clearInterval(intervalId);
  }, [chartConfig, latestIntelId, retryCount]);

  const handlePageChange = useCallback(async (page: number) => {
    try {
      setLoading(true);
      const offset = (page - 1) * itemsPerPage;
      const response = await fetch(`/api/intelligence?limit=${itemsPerPage}&offset=${offset}`);

      if (!response.ok) {
        throw new Error('Failed to fetch page data');
      }

      const data = await response.json();
      setTableIntelligence(data.data || []);
      setTotalPages(data.total_pages || 0);
      setTotalItems(data.total || 0);
      setCurrentPage(data.page || page);

      // 滚动到表格顶部
      document.getElementById('tactical-matrix')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
      console.error('Error fetching page:', error);
    } finally {
      setLoading(false);
    }
  }, [itemsPerPage]);

  // 处理每页条数变化
  const handleItemsPerPageChange = useCallback(async (newLimit: number) => {
    setItemsPerPage(newLimit);
    setCurrentPage(1); // 切换条数时重置到第一页
    // 这里不需要手动 fetch，因为 handlePageChange 或 initial useEffect 之后会处理
    // 但是我们需要确保 fetchData 或 handlePageChange 使用最新的 limit
  }, []);

  // 初始加载时获取分页信息以及全局高分总数
  useEffect(() => {
    if (liveIntelligence.length > 0 && totalItems === 0) {
      // 1. 分页基本信息
      fetch(`/api/intelligence?limit=${itemsPerPage}`)
        .then(res => res.json())
        .then(data => {
          setTotalPages(data.total_pages || 0);
          setTotalItems(data.total || 0);
        })
        .catch(err => console.error('Failed to fetch pagination info:', err));

      // 2. 获取 24h 内的高分预警数
      fetch('/api/alerts/24h')
        .then(res => res.json())
        .then(data => {
          if (data.count !== undefined) {
            setGlobalHighUrgency(data.count);
          }
        })
        .catch(err => console.error('Failed to fetch 24h alerts:', err));
    }
  }, [liveIntelligence.length, totalItems, itemsPerPage]);

  // 当 itemsPerPage 变化时重新加载第一页
  useEffect(() => {
    if (totalPages > 0) {
      handlePageChange(1);
    }
  }, [itemsPerPage, handlePageChange]);


  // Manual retry function
  const handleRetry = useCallback(() => {
    setError(null);
    setRetryCount(0);
    setLoading(true);
    // Trigger re-fetch by updating a dependency
    setLatestIntelId(null);
  }, []);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617]">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-slate-800 rounded-full"></div>
          <div className="w-16 h-16 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
        </div>
        <p className="text-slate-400 font-mono text-sm tracking-widest animate-pulse">{t('loading')}</p>
      </div>
    </div>
  );

  // const highUrgencyCount = liveIntelligence.filter(i => i.urgency_score >= 8).length; // 不再实时计算，使用全局状态

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 font-sans">

      {/* Error Alert */}
      {error && (
        <div className="mb-4">
          <Alert variant="error" onClose={() => setError(null)}>
            <div className="flex flex-col gap-2">
              <p className="font-semibold">Failed to load data</p>
              <p className="text-sm opacity-90">{error}</p>
              {retryCount >= 3 && (
                <button
                  onClick={handleRetry}
                  className="mt-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-md text-sm font-medium transition-colors w-fit"
                >
                  Retry Now
                </button>
              )}
              {retryCount > 0 && retryCount < 3 && (
                <p className="text-xs opacity-75">Auto-retrying... (Attempt {retryCount}/3)</p>
              )}
            </div>
          </Alert>
        </div>
      )}

      {/* 1. Brand Header (Scrolls away) */}
      <header className="flex flex-col md:flex-row justify-between items-start gap-4 mb-2">
        {/* Left: Brand Identity */}
        <div>
          <h1 className="text-3xl md:text-4xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400 flex items-center gap-3">
            <span className="text-4xl">🍍</span>
            {t('title')}
          </h1>
          <p className="text-slate-500 font-mono text-xs mt-1 uppercase tracking-widest pl-14">
            {t('subtitle')}
          </p>
        </div>

        {/* Right: Utilities */}
        <div className="flex items-center gap-4">
          <div className="hidden lg:block mr-4 flex-1 max-w-4xl">
            <AINarrativeTicker 
              items={liveIntelligence} 
              locale={locale} 
              getLocalizedText={getLocalizedText} 
            />
          </div>

          <SystemStatus isConnected={isConnected} />
        </div>
      </header>

      {/* 2. Sticky Toolbar (Tactical Cockpit: Alerts + Regime + Mini Charts) */}
      <div className="sticky top-0 z-50 bg-[#020617]/95 backdrop-blur-md border-b border-slate-800/50 -mx-4 px-4 md:-mx-6 md:px-6 lg:-mx-8 lg:px-8 py-2 mb-6 shadow-2xl shadow-black/50">
        {/* Mobile Tab Switcher */}
        <div className="flex lg:hidden w-full bg-slate-900/50 rounded-lg p-1 mb-3 border border-slate-800/50">
          <button
            onClick={() => setActiveTab('feed')}
            className={`flex-1 py-2 text-xs font-bold rounded-md transition-all flex items-center justify-center gap-2 ${activeTab === 'feed'
              ? 'bg-emerald-500 text-white shadow-lg'
              : 'text-slate-500 hover:text-slate-300'
              }`}
          >
            <Radio className="w-3.5 h-3.5" />
            {t('liveFeedLabel')}
          </button>
          <button
            onClick={() => setActiveTab('charts')}
            className={`flex-1 py-2 text-xs font-bold rounded-md transition-all flex items-center justify-center gap-2 ${activeTab === 'charts'
              ? 'bg-emerald-500 text-white shadow-lg'
              : 'text-slate-500 hover:text-slate-300'
              }`}
          >
            <Zap className="w-3.5 h-3.5" />
            {t('dataVisualization') || 'Data Analysis'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[84px] lg:h-[72px]">

          {/* Left (col-span-3): System State (Regime + Risk + Alerts) */}
          <div className="hidden lg:block lg:col-span-3 h-full">
            <div className="h-full flex items-stretch gap-2">

              {/* 1. Alert Counter (Enhanced) */}
              <div className="w-[140px] bg-slate-900/40 border border-slate-800/50 rounded-lg flex flex-col items-center justify-center shrink-0 px-4">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">{t('activeAlerts')}</span>
                <span className={`text-2xl font-black font-mono tracking-tighter ${globalHighUrgency > 0 ? 'text-rose-500 animate-pulse' : 'text-slate-600'}`}>
                  {globalHighUrgency}
                </span>
              </div>

            </div>
          </div>

          {/* Right (col-span-9): TradingView Mini Charts */}
          <div className="hidden lg:block lg:col-span-9 h-full">
            <div className="h-full overflow-hidden rounded-lg border border-slate-800/50 bg-slate-900/20">
              <TradingViewMiniCharts />
            </div>
          </div>
        </div>
      </div>

      {/* 2. Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* Left: Intelligence Stream (Sticky Sidebar) */}
        {/* Adjusted top offset (~130px) because the Sticky Header (Widgets) is ~100px. */}
        <div className={`lg:col-span-3 lg:sticky lg:top-[130px] flex flex-col gap-4 h-[calc(100vh-140px)] overflow-hidden pr-2 ${activeTab === 'feed' ? 'flex' : 'hidden lg:flex'
          }`}>

          {/* Sidebar Header: Search & Filter */}
          <div className="flex flex-col gap-3 mb-2 bg-[#020617] z-10 pb-2 border-b border-slate-800/50 flex-shrink-0">

            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder={t('searchPlaceholder') || "Search intelligence..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-800 rounded-md py-2 pl-9 pr-8 text-xs text-slate-200 focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Filter Toggles */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setFilterMode('all')}
                className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md border transition-all ${filterMode === 'all'
                  ? 'bg-slate-700 text-white border-slate-600'
                  : 'bg-transparent text-slate-500 border-slate-800 hover:bg-slate-800'
                  }`}
              >
                {t('filterAll')}
              </button>
              <button
                onClick={() => setFilterMode('essential')}
                className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md border transition-all ${filterMode === 'essential'
                  ? 'bg-rose-500/20 text-rose-400 border-rose-500/50'
                  : 'bg-transparent text-slate-500 border-slate-800 hover:bg-slate-800'
                  }`}
              >
                {t('filterEssential')}
              </button>
              <button
                onClick={() => setFilterMode('bearish')}
                className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md border transition-all ${filterMode === 'bearish'
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50'
                  : 'bg-transparent text-slate-500 border-slate-800 hover:bg-slate-800'
                  }`}
              >
                {t('filterBearish')}
              </button>
            </div>

            <div className="flex items-center justify-between mt-1">
              <h2 className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                <Radio className="w-3 h-3 text-emerald-500" /> {t('liveFeedLabel')}
              </h2>
              <Badge variant="neutral" className="text-[10px] h-5">{filteredLiveIntelligence.length} / {liveIntelligence.length}</Badge>
            </div>
          </div>

          {/* Native List with Scroll */}
          <div className="flex-1 min-h-0 w-full overflow-y-auto custom-scrollbar">
            {filteredLiveIntelligence.map((item: Intelligence) => (
              <IntelligenceCard
                key={item.id}
                item={item}
                locale={locale}
                getLocalizedText={getLocalizedText}
                t={t}
                tSentiment={tSentiment}
                isBearish={isBearishSentiment(item.sentiment)}
              />
            ))}
            {/* Empty State */}
            {filteredLiveIntelligence.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-slate-500">
                <p className="text-sm">No intelligence found</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Visualization & Data */}
        <div className={`lg:col-span-9 flex flex-col gap-6 ${activeTab === 'charts' ? 'flex' : 'hidden lg:flex'
          }`}>
          <Chart
            marketData={marketData}
            intelligence={liveIntelligence}
            onRangeChange={(range, interval) => setChartConfig({ range, interval })}
          />

          {/* AI Backtest Stats */}
          <BacktestStats intelligence={liveIntelligence} marketData={marketData} />

          {/* Strategy Matrix (Integrated into Right Column) */}
          <Card title={tTable('title')} className="min-h-[300px]" id="tactical-matrix">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-500 text-[10px] uppercase tracking-wider">
                    <th className="p-4 font-semibold">{tTable('time')}</th>
                    <th className="p-4 font-semibold w-[40%]">{tTable('context')}</th>
                    <th className="p-4 font-semibold w-[30%]">{tTable('strategy')}</th>
                    <th className="p-4 font-semibold text-right">{tTable('goldRef')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-sm">
                  {loading ? (
                    <tr>
                      <td colSpan={4} className="p-8 text-center text-slate-500">
                        {t('loading')}
                      </td>
                    </tr>
                  ) : tableIntelligence.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="p-8 text-center text-slate-500">
                        暂无数据
                      </td>
                    </tr>
                  ) : (
                    tableIntelligence.map((item: Intelligence) => (
                      <tr key={item.id} className="group hover:bg-slate-800/30 transition-colors">
                        <td className="p-4 font-mono text-slate-500 text-xs whitespace-nowrap">
                          {(() => {
                            const date = new Date(item.timestamp);
                            const year = date.getUTCFullYear();
                            const month = String(date.getUTCMonth() + 1).padStart(2, '0');
                            const day = String(date.getUTCDate()).padStart(2, '0');
                            const hours = String(date.getUTCHours()).padStart(2, '0');
                            const minutes = String(date.getUTCMinutes()).padStart(2, '0');
                            const seconds = String(date.getUTCSeconds()).padStart(2, '0');
                            return `${year}/${month}/${day} ${hours}:${minutes}:${seconds} (UTC)`;
                          })()}
                        </td>
                        <td className="p-4 text-slate-300">
                          {getLocalizedText(item.summary, locale)}
                        </td>
                        <td className="p-4 text-emerald-400 font-mono text-xs">
                          {getLocalizedText(item.actionable_advice, locale)}
                        </td>
                        <td className="p-4 text-right font-mono text-slate-400">
                          ${item.gold_price_snapshot?.toFixed(1) || '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* 分页器 */}
            {!loading && totalPages > 1 && (
              <div className="mt-6 pt-4 border-t border-slate-800">
                <Paginator
                  currentPage={currentPage}
                  totalPages={totalPages}
                  totalItems={totalItems}
                  itemsPerPage={itemsPerPage}
                  onPageChange={handlePageChange}
                  onItemsPerPageChange={handleItemsPerPageChange}
                />
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Floating Language Switcher */}
      <div className="fixed bottom-6 right-6 z-50 shadow-2xl shadow-emerald-500/20">
        <LanguageSwitcher />
      </div>
    </div >
  );
}
