'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import {
    Activity,
    ArrowLeft,
    Zap,
    Clock,
    Globe,
    ExternalLink,
    Shield,
    TrendingUp,
    TrendingDown,
    FileText
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useRouter } from '@/i18n/navigation';
import { Intelligence } from '@/lib/db';

export default function IntelligenceDetailPage() {
    const params = useParams();
    const id = params?.id;
    const locale = useLocale();
    const router = useRouter();
    const t = useTranslations('IntelligenceDetail');
    const tBacktest = useTranslations('Backtest');
    const tSentiment = useTranslations('Sentiment');

    const [item, setItem] = useState<Intelligence | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchItem = async () => {
            if (!id) return;
            setLoading(true);
            try {
                const res = await fetch(`/api/v1/web/intelligence/${id}`);
                if (res.ok) {
                    const data = await res.json();
                    setItem(data);
                } else {
                    setError(t('notFound'));
                }
            } catch {
                setError(t('notFound'));
            } finally {
                setLoading(false);
            }
        };

        fetchItem();
    }, [id, t]);

    const getLocalizedText = (textSource: string | Record<string, string> | undefined) => {
        if (!textSource) return '';
        try {
            const data = typeof textSource === 'string' ? JSON.parse(textSource) : textSource;
            return data[locale] || data['en'] || Object.values(data)[0] || '';
        } catch {
            return String(textSource);
        }
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
            <Activity className="w-10 h-10 text-blue-600 animate-spin" />
            <span className="text-slate-500 font-bold animate-pulse">{t('loading')}</span>
        </div>
    );

    if (error || !item) return (
        <div className="p-8 flex flex-col items-center justify-center gap-4">
            <div className="w-16 h-16 rounded-full bg-rose-50 dark:bg-rose-500/10 flex items-center justify-center text-rose-500">
                <Shield className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold">{error || t('notFound')}</h2>
            <button
                onClick={() => router.back()}
                className="px-6 py-2 bg-slate-100 dark:bg-slate-800 rounded-xl font-bold text-sm"
            >
                {t('backToTerminal')}
            </button>
        </div>
    );

    const isBearish = (getLocalizedText(item.sentiment).toLowerCase().includes('bearish') ||
        getLocalizedText(item.sentiment).includes('看跌') ||
        getLocalizedText(item.sentiment).includes('медвежий'));

    return (
        <div className="flex flex-col gap-8 p-4 md:p-6 lg:p-8 animate-in fade-in slide-in-from-bottom-2 duration-700 max-w-5xl mx-auto">
            {/* Header */}
            <div className="flex flex-col gap-6">
                <button
                    onClick={() => router.back()}
                    className="flex items-center gap-2 text-slate-500 hover:text-blue-600 transition-colors text-xs font-bold uppercase tracking-widest group w-fit"
                >
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                    {t('backToResearch')}
                </button>

                <div className="flex flex-col gap-4">
                    <div className="flex flex-wrap items-center gap-3">
                        <Badge variant={item.urgency_score >= 8 ? 'bearish' : 'neutral'}>
                            {tSentiment('score')}: {item.urgency_score}/10
                        </Badge>
                        <Badge variant={isBearish ? 'bearish' : 'bullish'}>
                            {getLocalizedText(item.sentiment)}
                        </Badge>
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                            <Clock className="w-3 h-3" />
                            {new Date(item.timestamp).toLocaleString()}
                        </div>
                    </div>
                    <h1 className="text-2xl md:text-3xl lg:text-4xl font-black leading-tight text-slate-900 dark:text-white">
                        {getLocalizedText(item.summary)}
                    </h1>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content */}
                <div className="lg:col-span-2 flex flex-col gap-8">
                    {/* Deep Analysis Section */}
                    <section className="flex flex-col gap-4">
                        <h2 className="text-xs font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                            <FileText className="w-4 h-4 text-blue-500" />
                            {t('deepAnalysis')}
                        </h2>
                        <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
                            <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-lg italic serif">
                                &quot;{item.content}&quot;
                            </p>
                        </div>
                    </section>

                    {/* Market Implication Section */}
                    <section className="flex flex-col gap-4">
                        <h2 className="text-xs font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                            <Globe className="w-4 h-4 text-emerald-500" />
                            {t('marketImplication')}
                        </h2>
                        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl p-6">
                            <div className="prose dark:prose-invert max-w-none text-slate-600 dark:text-slate-400">
                                {getLocalizedText(item.market_implication)}
                            </div>
                        </div>
                    </section>

                    {/* Actionable Advice Section */}
                    <section className="flex flex-col gap-4">
                        <h2 className="text-xs font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                            <Zap className="w-4 h-4 text-amber-500" />
                            {t('actionableRecommendation')}
                        </h2>
                        <div className={`rounded-2xl p-6 border ${isBearish ? 'bg-rose-50 dark:bg-rose-500/5 border-rose-100 dark:border-rose-500/20' : 'bg-emerald-50 dark:bg-emerald-500/5 border-emerald-100 dark:border-emerald-500/20'}`}>
                            <div className={`prose dark:prose-invert max-w-none font-bold ${isBearish ? 'text-rose-700 dark:text-rose-400' : 'text-emerald-700 dark:text-emerald-400'}`}>
                                {getLocalizedText(item.actionable_advice)}
                            </div>
                        </div>
                    </section>
                </div>

                {/* Sidebar Metrics */}
                <div className="flex flex-col gap-6">
                    {/* Performance Snapshot */}
                    <Card className="p-6 flex flex-col gap-4 bg-slate-900 dark:bg-slate-950 text-white border-none shadow-2xl">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-800 pb-3">
                            {t('priceActionLog')}
                        </h3>
                        <div className="flex flex-col gap-6">
                            <div className="flex flex-col gap-1">
                                <span className="text-[10px] text-slate-500 font-bold uppercase">{t('triggerPrice')}</span>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-3xl font-mono font-black">${item.gold_price_snapshot?.toFixed(2)}</span>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 gap-4">
                                {[
                                    { label: '15M Window', val: item.price_15m },
                                    { label: '1H Window', val: item.price_1h },
                                    { label: '4H Window', val: item.price_4h },
                                    { label: '12H Window', val: item.price_12h },
                                    { label: '24H Window', val: item.price_24h }
                                ].map((window) => window.val && (
                                    <div key={window.label} className="flex justify-between items-center bg-white/5 p-3 rounded-xl">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] text-slate-500 font-bold">{window.label}</span>
                                            <span className="text-sm font-mono font-bold">${window.val.toFixed(2)}</span>
                                        </div>
                                        <div className={`flex items-center gap-1 font-black font-mono text-xs ${((window.val - (item.gold_price_snapshot || 0)) > 0) !== isBearish ? 'text-emerald-400' : 'text-rose-400'}`}>
                                            {window.val > (item.gold_price_snapshot || 0) ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                            {(((window.val - (item.gold_price_snapshot || 0)) / (item.gold_price_snapshot || 1)) * 100).toFixed(2)}%
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </Card>

                    {/* Meta Data */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 flex flex-col gap-4 shadow-sm">
                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">{t('sourceAuthenticity')}</span>
                            <span className="text-sm font-bold text-slate-700 dark:text-slate-200 flex items-center gap-2">
                                <Shield className="w-4 h-4 text-blue-500" />
                                {item.author}
                            </span>
                        </div>
                        <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-full py-3 bg-slate-100 dark:bg-slate-800 hover:bg-blue-600 hover:text-white transition-all rounded-xl flex items-center justify-center gap-2 text-xs font-bold"
                        >
                            {t('viewOriginalSource')}
                            <ExternalLink className="w-3 h-3" />
                        </a>
                    </div>

                    {/* Technical Context */}
                    <div className="bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 rounded-2xl p-6 flex flex-col gap-4">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400">{t('contextualMatrix')}</h3>
                        <div className="space-y-3">
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-slate-500">DXY Snapshot</span>
                                <span className="font-mono font-bold">{item.dxy_snapshot || 'N/A'}</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-slate-500">GVZ (Vol)</span>
                                <span className="font-mono font-bold">{item.gvz_snapshot || 'N/A'}</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-slate-500">10Y Yield</span>
                                <span className="font-mono font-bold">{item.us10y_snapshot || 'N/A'}</span>
                            </div>
                        </div>
                    </div>

                    {/* Analysis Note */}
                    <div className="p-4 rounded-xl border border-dashed border-slate-200 dark:border-slate-800">
                        <p className="text-[10px] text-slate-400 leading-relaxed italic text-center">
                            {t('analysisNote', {
                                window: tBacktest('window1h'), // Defaulting to 1H for the general note
                                sentiment: getLocalizedText(item.sentiment)
                            })}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
