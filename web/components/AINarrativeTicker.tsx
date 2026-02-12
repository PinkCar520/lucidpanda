'use client';

import React, { useMemo } from 'react';
import { Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface TickerItem {
    summary?: any;
    content?: any;
    [key: string]: any;
}

interface AINarrativeTickerProps {
    items?: TickerItem[];
    locale: string;
    getLocalizedText: (input: any, locale: string) => string;
}


export default function AINarrativeTicker({
    items = [],
    locale,
    getLocalizedText
}: AINarrativeTickerProps) {
    const t = useTranslations('AIInsights');

    // AI Insight Optimization: Ticker/Rapid Stream Logic
    const urgentRecentItems = useMemo(() => {
        const now = Date.now();
        const FOUR_HOURS_MS = 4 * 60 * 60 * 1000;

        return items.filter(item => {
            const urgency = item.urgency_score || 0;
            const itemTime = new Date(item.timestamp).getTime();
            const isUrgent = urgency > 7;
            const isRecent = (now - itemTime) <= FOUR_HOURS_MS;

            return isUrgent && isRecent;
        });
    }, [items]);

    // Construct display items with metadata for dots
    const displayItems = useMemo(() => {
        if (urgentRecentItems.length > 0) {
            return urgentRecentItems.map(item => {
                const text = getLocalizedText(item.summary || item.content, locale);
                const sentimentStr = JSON.stringify(item.sentiment || '').toLowerCase();

                let sentimentType: 'bearish' | 'bullish' | 'neutral' = 'neutral';
                if (['鹰', '利空', '下跌', '风险', 'bearish', 'hawkish', 'risk', 'negative'].some(k => sentimentStr.includes(k))) {
                    sentimentType = 'bearish';
                } else if (['鸽', '利多', '上涨', '积极', 'bullish', 'dovish', 'positive', 'safe-haven'].some(k => sentimentStr.includes(k))) {
                    sentimentType = 'bullish';
                }

                return {
                    text,
                    urgency: item.urgency_score || 0,
                    sentiment: sentimentType
                };
            }).filter(item => item.text.length > 0);
        }

        // "All Clear" Signal: No urgent drivers in the last 4 hours
        return [{
            text: t('stable'),
            urgency: 0,
            sentiment: 'neutral'
        }];
    }, [urgentRecentItems, locale, getLocalizedText]);

    const narratives = displayItems;
    const getDotClass = (urgency: number, sentiment: string) => {
        if (urgency >= 8) return 'bg-rose-500 animate-pulse shadow-[0_0_8px_rgba(244,63,94,0.8)]';
        if (sentiment === 'bearish' || sentiment === 'hawkish') return 'bg-rose-500 shadow-[0_0_4px_rgba(244,63,94,0.4)]';
        if (sentiment === 'bullish' || sentiment === 'dovish') return 'bg-emerald-500 shadow-[0_0_4px_rgba(16,185,129,0.4)]';
        return 'bg-slate-500';
    };

    return (
        <div className="flex items-center gap-3 bg-slate-50 dark:bg-slate-900/30 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-800/50 relative overflow-hidden">
            <div className="flex items-center gap-1.5 shrink-0 z-20 pr-2 bg-gradient-to-r from-slate-50 via-slate-50 to-transparent dark:from-[#0b101e] dark:via-[#0b101e] dark:to-transparent">
                <Sparkles className="w-3.5 h-3.5 text-blue-500 dark:text-cyan-400" />
                <span className="text-[10px] font-bold text-blue-600 dark:text-cyan-500 uppercase tracking-widest whitespace-nowrap">{t('title')}</span>
            </div>

            <div className="h-3 w-px bg-slate-200 dark:bg-slate-800 shrink-0 z-20"></div>

            <div className="w-[300px] lg:w-[500px] overflow-hidden relative ticker-wrapper">
                {/* Gradient Masks */}
                <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-slate-50 dark:from-[#020617] to-transparent z-10 pointer-events-none"></div>
                <div className="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-slate-50 dark:from-[#020617] to-transparent z-10 pointer-events-none"></div>

                <div className="flex whitespace-nowrap animate-ticker">
                    {/* Duplicate list for seamless loop */}
                    {[...narratives, ...narratives].map((item, i) => (
                        <div key={i} className="flex items-center mx-10">
                            {/* Dynamic Indicator Dot */}
                            <div className={`w-2 h-2 rounded-full mr-3 shrink-0 ${getDotClass(item.urgency, item.sentiment)}`} />

                            <span className="text-sm font-mono text-slate-600 dark:text-slate-300">
                                {item.text}
                            </span>
                            <span className="ml-10 text-slate-300 dark:text-slate-600 text-[10px]">•</span>
                        </div>
                    ))}
                </div>
            </div>
            <style jsx global>{`
        @keyframes ticker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-ticker {
          animation: ticker 60s linear infinite;
          width: max-content;
        }
        .ticker-wrapper:hover .animate-ticker {
          animation-play-state: paused;
        }
      `}</style>
        </div>
    );
}
