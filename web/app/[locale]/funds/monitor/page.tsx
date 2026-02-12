'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useQuery } from '@tanstack/react-query';
import { fundService } from '@/lib/services/fund-service';
import { 
    Activity, 
    AlertCircle, 
    CheckCircle2, 
    Clock, 
    ChevronLeft,
    TrendingDown,
    ShieldCheck
} from 'lucide-react';
import Link from 'next/link';
import dynamic from 'next/dynamic';

// Dynamic import for Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false }) as any;

export default function FundMonitorPage() {
    const t = useTranslations('Monitor');
    const { data: session } = useSession();

    const { data: stats, isLoading } = useQuery({
        queryKey: ['admin', 'fund-monitor'],
        queryFn: () => fundService.getMonitorStats(session),
        refetchInterval: 1000 * 60 * 5, // 5 min
    });

    if (isLoading) {
        return <div className="p-8 text-center text-slate-500 animate-pulse">{t('initializing')}</div>;
    }

    const latest = stats?.daily?.[0];
    const reconciliationRate = latest ? (latest.reconciled_count / latest.total_count) * 100 : 0;

    // --- Heatmap Data Transformation ---
    const heatmapTraces = React.useMemo(() => {
        if (!stats?.heatmap || stats.heatmap.length === 0) return null;

        const dates = Array.from(new Set(stats.heatmap.map((h: any) => h.trade_date))).sort().reverse();
        const categories = Array.from(new Set(stats.heatmap.map((h: any) => h.category)));
        
        const zMatrix = dates.map(d => {
            return categories.map(c => {
                const match = stats.heatmap.find((h: any) => h.trade_date === d && h.category === c);
                return match ? match.mae : null;
            });
        });

        return {
            x: categories,
            y: dates,
            z: zMatrix,
            type: 'heatmap',
            colorscale: [
                [0, '#10b981'],   // Green (Perfect)
                [0.2, '#3b82f6'], // Blue
                [0.5, '#f59e0b'], // Amber (Warning)
                [1.0, '#ef4444']  // Red (Danger)
            ],
            showscale: true,
            hoverongaps: false,
            hovertemplate: 'Category: %{x}<br>Date: %{y}<br>MAE: %{z:.4f}%<extra></extra>'
        };
    }, [stats?.heatmap]);

    return (
        <div className="flex flex-col p-4 md:p-8 gap-8 min-h-screen bg-slate-50/30 dark:bg-[#020617] transition-colors">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2 text-blue-500 dark:text-blue-400 mb-1">
                        <Link href="/funds" className="flex items-center gap-1 text-xs font-bold uppercase tracking-tighter hover:underline">
                            <ChevronLeft className="w-3 h-3" /> {t('backToFunds')}
                        </Link>
                    </div>
                    <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
                        <Activity className="w-8 h-8 text-blue-600" />
                        {t('title')}
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 text-sm max-w-lg">
                        {t('subtitle')}
                    </p>
                </div>
                
                {stats?.updated_at && (
                    <Badge variant="outline" className="font-mono text-[10px] py-1 px-3 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
                        <Clock className="w-3 h-3 mr-1.5 opacity-60" />
                        {t('lastSync', { time: new Date(stats.updated_at).toLocaleTimeString() })}
                    </Badge>
                )}
            </div>

            {/* Quick KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="border-l-4 border-l-blue-500">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{t('successRate')}</p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black">{reconciliationRate.toFixed(1)}%</span>
                        <Badge variant={reconciliationRate > 90 ? 'bullish' : 'warning'} className="text-[10px]">
                            {latest?.reconciled_count}/{latest?.total_count}
                        </Badge>
                    </div>
                </Card>
                <Card className="border-l-4 border-l-emerald-500">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{t('currentMae')}</p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black">{(latest?.avg_mae || 0).toFixed(3)}%</span>
                        <TrendingDown className="w-4 h-4 text-emerald-500" />
                    </div>
                </Card>
                <Card className="border-l-4 border-l-amber-500">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{t('systemHealth')}</p>
                    <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{t('statusOptimal')}</span>
                        <ShieldCheck className="w-5 h-5 text-amber-500" />
                    </div>
                </Card>
                <Card className="border-l-4 border-l-purple-500">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{t('activeWindow')}</p>
                    <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{t('fiveDays')}</span>
                        <Clock className="w-5 h-5 text-purple-500" />
                    </div>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Accuracy Heatmap */}
                <Card title={t('heatmapTitle') || "Accuracy Heatmap by Category"} className="lg:col-span-3 overflow-hidden">
                    <div className="h-[300px] w-full">
                        {heatmapTraces ? (
                            <Plot
                                data={[heatmapTraces]}
                                layout={{
                                    autosize: true,
                                    margin: { l: 100, r: 20, t: 20, b: 80 },
                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                    xaxis: { tickangle: -45, tickfont: { size: 10, color: '#94a3b8' } },
                                    yaxis: { tickfont: { size: 10, color: '#94a3b8' }, type: 'category' },
                                    font: { family: 'inherit' }
                                }}
                                config={{ displayModeBar: false, responsive: true }}
                                className="w-full h-full"
                            />
                        ) : (
                            <div className="h-full flex items-center justify-center text-slate-500 italic">Insufficient data for heatmap</div>
                        )}
                    </div>
                </Card>

                {/* Trend Chart */}
                <Card title={t('trendTitle')} className="lg:col-span-2">
                    <div className="h-[350px] w-full">
                        <Plot
                            data={[
                                {
                                    x: stats?.daily?.map((d: any) => d.trade_date).reverse(),
                                    y: stats?.daily?.map((d: any) => d.avg_mae).reverse(),
                                    type: 'scatter',
                                    mode: 'lines+markers',
                                    name: t('maeLabel'),
                                    line: { color: '#3b82f6', width: 3, shape: 'spline' },
                                    marker: { color: '#3b82f6', size: 8 },
                                    fill: 'tozeroy',
                                    fillcolor: 'rgba(59, 130, 246, 0.1)'
                                }
                            ]}
                            layout={{
                                autosize: true,
                                margin: { l: 40, r: 20, t: 20, b: 40 },
                                paper_bgcolor: 'rgba(0,0,0,0)',
                                plot_bgcolor: 'rgba(0,0,0,0)',
                                xaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { size: 10, color: '#94a3b8' } },
                                yaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { size: 10, color: '#94a3b8' }, title: { text: t('errorPercent'), font: { size: 10 } } },
                                font: { family: 'inherit' }
                            }}
                            config={{ displayModeBar: false, responsive: true }}
                            className="w-full h-full"
                        />
                    </div>
                </Card>

                {/* Anomalies List */}
                <Card title={t('anomaliesTitle')} action={<Badge variant="bearish">{t('alertsCount', { count: stats?.anomalies?.length || 0 })}</Badge>}>
                    <div className="flex flex-col gap-3 max-h-[350px] overflow-y-auto custom-scrollbar pr-2">
                        {stats?.anomalies?.length > 0 ? (
                            stats.anomalies.map((a: any, i: number) => (
                                <div key={i} className="group p-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg flex flex-col gap-2 hover:border-rose-500/50 transition-colors">
                                    <div className="flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono font-bold text-blue-500">{a.fund_code}</span>
                                            <span className="text-[10px] opacity-60 font-mono">{a.trade_date}</span>
                                        </div>
                                        <Badge variant="bearish" className="text-[10px] px-1.5">{a.deviation.toFixed(2)}%</Badge>
                                    </div>
                                    <div className="flex justify-between items-center text-[10px] font-mono">
                                        <span className="opacity-60">{t('estLabel')} {a.frozen_est_growth.toFixed(2)}%</span>
                                        <span className="opacity-60">{t('actLabel')} {a.official_growth.toFixed(2)}%</span>
                                        <span className="font-bold text-rose-500">{t('gradeLabel')} {a.tracking_status}</span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12 text-slate-400 opacity-20">
                                <CheckCircle2 className="w-12 h-12 mb-2" />
                                <p className="text-sm font-bold">{t('noAnomalies')}</p>
                            </div>
                        )}
                    </div>
                </Card>
            </div>

            {/* Daily Detailed Table */}
            <Card title={t('ledgerTitle')}>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase tracking-wider font-bold">
                                <th className="p-3">{t('tableDate')}</th>
                                <th className="p-3">{t('tableTotal')}</th>
                                <th className="p-3">{t('tableMatched')}</th>
                                <th className="p-3 text-right">{t('tableMae')}</th>
                                <th className="p-3 text-center">{t('tableStatus')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                            {stats?.daily?.map((d: any, i: number) => {
                                const rate = (d.reconciled_count / d.total_count) * 100;
                                return (
                                    <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors">
                                        <td className="p-3 font-mono">{d.trade_date}</td>
                                        <td className="p-3">{d.total_count}</td>
                                        <td className="p-3">
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                                                    <div className="h-full bg-blue-500" style={{ width: `${rate}%` }}></div>
                                                </div>
                                                <span className="font-mono">{d.reconciled_count} ({rate.toFixed(0)}%)</span>
                                            </div>
                                        </td>
                                        <td className={`p-3 text-right font-mono font-bold ${d.avg_mae > 0.5 ? 'text-amber-500' : 'text-emerald-500'}`}>
                                            {d.avg_mae ? `${d.avg_mae.toFixed(4)}%` : '--'}
                                        </td>
                                        <td className="p-3 text-center">
                                            {rate >= 95 ? (
                                                <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" />
                                            ) : (
                                                <AlertCircle className="w-4 h-4 text-amber-500 mx-auto" />
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    );
}
