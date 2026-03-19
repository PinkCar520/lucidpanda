'use client';

import React, { useMemo, useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Card } from './ui/Card';
import { useTranslations } from 'next-intl';
import { Intelligence } from '@/lib/db';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false }) as any;

interface ChartProps {
  marketData: any;
  intelligence: Intelligence[];
  onRangeChange: (range: string, interval: string) => void;
}

const RANGES = [
  { label: 'intraday', range: '1d', interval: '5m' },
  { label: 'day', range: '1mo', interval: '1d' },
  { label: 'week', range: '2y', interval: '1wk' },
  { label: 'month', range: '5y', interval: '1mo' },
  { label: 'quarter', range: '10y', interval: '3mo' }, // Provider limits might apply
  { label: 'year', range: 'max', interval: '3mo' }, // 1y interval often unstable
  { label: 'all', range: 'max', interval: '1mo' },
];

export default function Chart({ marketData, intelligence, onRangeChange }: ChartProps) {
  const t = useTranslations('Chart');
  const [activeLabel, setActiveLabel] = useState('day');
  const [isDark, setIsDark] = useState(false);

  const indicators = marketData?.indicators;

  // Sync with document theme class
  useEffect(() => {
    const checkTheme = () => {
      setIsDark(document.documentElement.classList.contains('dark'));
    };
    checkTheme();

    // Observer for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  const handleRangeClick = (range: string, interval: string, label: string) => {
    setActiveLabel(label);
    onRangeChange(range, interval);
  };

  const ChartHeader = (
    <div className="flex flex-col md:flex-row md:items-center gap-4">
      {indicators && (
        <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-900/50 px-3 py-1 rounded-lg border border-slate-200 dark:border-slate-800/50">
          <div className="flex flex-col">
            <span className="text-[8px] uppercase font-bold text-slate-400 tracking-tight">Gold Spread (CNY/g)</span>
            <div className="flex items-center gap-1.5">
              <span className={`text-sm font-black font-mono ${indicators.spread >= 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                {indicators.spread > 0 ? '+' : ''}{indicators.spread.toFixed(2)}
              </span>
              <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
                ({indicators.spread_pct > 0 ? '+' : ''}{indicators.spread_pct.toFixed(2)}%)
              </span>
            </div>
          </div>
          <div className="w-px h-6 bg-slate-200 dark:border-slate-800/50 mx-1"></div>
          <div className="flex flex-col">
            <span className="text-[8px] uppercase font-bold text-slate-400 tracking-tight">AU9999 Spot</span>
            <span className="text-sm font-black font-mono text-slate-700 dark:text-slate-300">
              {indicators.domestic_spot.toFixed(2)}
            </span>
          </div>
        </div>
      )}
      <div className="flex bg-slate-100 dark:bg-slate-900/50 rounded-lg p-0.5 border border-slate-200 dark:border-slate-800/50 overflow-x-auto max-w-[180px] md:max-w-none no-scrollbar">
        {RANGES.map((r) => (
          <button
            key={r.label}
            onClick={() => handleRangeClick(r.range, r.interval, r.label)}
            className={`flex-shrink-0 px-2 md:px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all duration-200 ${activeLabel === r.label
              ? 'bg-blue-600 dark:bg-emerald-500/20 text-white dark:text-emerald-400 shadow-sm border border-blue-700 dark:border-emerald-500/20'
              : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-white dark:hover:bg-slate-800/50'
              }`}
          >
            {t(r.label)}
          </button>
        ))}
      </div>
    </div>
  );

  if (!marketData || !marketData.quotes) return (
    <Card className="h-[450px] p-0 border-slate-200 dark:border-slate-800" title={t('title')} action={ChartHeader}>
      <div className="h-full flex flex-col justify-between p-6 animate-pulse">
        {/* Skeleton: Y-axis labels */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex flex-col gap-3">
            <div className="h-3 w-16 bg-slate-200 dark:bg-slate-800 rounded"></div>
            <div className="h-3 w-16 bg-slate-200 dark:bg-slate-800 rounded"></div>
            <div className="h-3 w-16 bg-slate-200 dark:bg-slate-800 rounded"></div>
          </div>
          <div className="text-slate-400 dark:text-slate-600 text-xs">{t('loadingData')}</div>
        </div>

        {/* Skeleton: Chart area with candlestick-like bars */}
        <div className="flex-1 flex items-end justify-around gap-1 px-4">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="bg-slate-200/50 dark:bg-slate-800/50 rounded-sm"
              style={{
                height: `${Math.random() * 60 + 20}%`,
                width: '3%',
                opacity: 0.3 + Math.random() * 0.4
              }}
            ></div>
          ))}
        </div>

        {/* Skeleton: X-axis labels */}
        <div className="flex justify-between mt-4 px-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-3 w-20 bg-slate-200 dark:bg-slate-800 rounded"></div>
          ))}
        </div>
      </div>
    </Card>
  );

  // Prepare data for Plotly
  const traces = [
    // Candlestick trace
    {
      x: marketData.quotes.map((q: any) => q.date),
      close: marketData.quotes.map((q: any) => q.close),
      high: marketData.quotes.map((q: any) => q.high),
      low: marketData.quotes.map((q: any) => q.low),
      open: marketData.quotes.map((q: any) => q.open),

      // increasing: { line: { color: '#10B981', width: 1 }, fillcolor: '#10B981' },
      // decreasing: { line: { color: '#F43F5E', width: 1 }, fillcolor: '#F43F5E' },
      // increasing: { line: { color: '#EF4444' } }, // Red (Up)
      // decreasing: { line: { color: '#10B981' } }, // Green (Down)
      increasing: { line: { color: '#EF4444' } },
      decreasing: { line: { color: '#10B981' } },

      type: 'candlestick',
      xaxis: 'x',
      yaxis: 'y',
      name: 'Gold Futures',
      showlegend: false,
    },
    // Markers for Bullish Events
    {
      x: intelligence.filter(i => !/鹰|利空|下跌|风险|Bearish/.test(i.sentiment)).map(i => i.timestamp),
      y: intelligence.filter(i => !/鹰|利空|下跌|风险|Bearish/.test(i.sentiment)).map(i => i.gold_price_snapshot || marketData.quotes[marketData.quotes.length - 1].close), // Fallback price
      mode: 'markers',
      type: 'scatter',
      name: 'Bullish Signal',
      marker: { symbol: 'triangle-up', size: 10, color: '#EF4444' }, // Red 500 (Up)
      hoverinfo: 'text',
      text: intelligence.filter(i => !/鹰|利空|下跌|风险|Bearish/.test(i.sentiment)).map(i => `${i.summary} (Score: ${i.urgency_score})`),
    },
    // Markers for Bearish Events
    {
      x: intelligence.filter(i => /鹰|利空|下跌|风险|Bearish/.test(i.sentiment)).map(i => i.timestamp),
      y: intelligence.filter(i => /鹰|利空|下跌|风险|Bearish/.test(i.sentiment)).map(i => i.gold_price_snapshot || marketData.quotes[marketData.quotes.length - 1].close),
      mode: 'markers',
      type: 'scatter',
      name: 'Bearish Signal',
      marker: { symbol: 'triangle-down', size: 10, color: '#10B981' }, // Emerald 500 (Down)
      hoverinfo: 'text',
      text: intelligence.filter(i => /鹰|利空|下跌|风险|Bearish/.test(i.sentiment)).map(i => `${i.summary} (Score: ${i.urgency_score})`),
    }
  ];

  return (
    <Card className="h-[350px] md:h-[450px] p-0 border-slate-200 dark:border-slate-800" title={t('title')} action={ChartHeader}>
      <Plot
        data={traces}
        layout={{
          autosize: true,
          // height: 450, // Removed to allow responsive parent control
          margin: { l: 40, r: 10, t: 30, b: 40 }, // Tighter margins for mobile
          plot_bgcolor: 'transparent',
          paper_bgcolor: 'transparent',
          font: { color: isDark ? '#94a3b8' : '#475569', family: 'monospace' },
          xaxis: {
            gridcolor: isDark ? '#1e293b' : '#f1f5f9', // slate-800 : slate-100
            linecolor: isDark ? '#334155' : '#e2e8f0', // slate-700 : slate-200 (Subtle)
            showline: true, // Distinct axis line
            zeroline: false, // Remove heavy zero line
            tickcolor: isDark ? '#334155' : '#e2e8f0',
            rangeslider: { visible: false },
            type: 'date',
            tickformat: activeLabel === 'intraday' ? '%H:%M' : '%Y-%m-%d'
          },
          yaxis: {
            gridcolor: isDark ? '#1e293b' : '#f1f5f9',
            linecolor: isDark ? '#334155' : '#e2e8f0',
            showline: true,
            zeroline: false,
            tickcolor: isDark ? '#334155' : '#e2e8f0',
            side: 'right'
          },
          showlegend: !(/iPhone|Android/.test(typeof navigator !== 'undefined' ? navigator.userAgent : '')), // Hide legend on mobile to save space
          legend: {
            x: 0,
            y: 1,
            font: { color: isDark ? '#94a3b8' : '#475569' },
            bgcolor: 'rgba(0,0,0,0)'
          },
          hovermode: 'x unified',
          hoverlabel: {
            bgcolor: isDark ? '#0f172a' : '#ffffff',
            bordercolor: isDark ? '#334155' : '#e2e8f0',
            font: { color: isDark ? '#e2e8f0' : '#0f172a' }
          }
        }}
        useResizeHandler={true}
        style={{ width: '100%' }}
        config={{ responsive: true, displayModeBar: false }}
      />
    </Card>
  );
}