'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useQuery } from '@tanstack/react-query';
import { fundService, type FundMonitorStats } from '@/lib/services/fund-service';
import { 
    Activity, 
    AlertCircle, 
    CheckCircle2, 
    Clock, 
    ChevronLeft,
    TrendingDown,
    ShieldCheck,
    RefreshCw,
    Zap,
    BarChart3
} from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';
import dynamic from 'next/dynamic';
interface PlotlyComponentProps {
    data: unknown;
    layout?: Record<string, unknown>;
    config?: Record<string, unknown>;
    className?: string;
}

// Dynamic import for Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false }) as unknown as React.ComponentType<PlotlyComponentProps>;

export default function FundMonitorPage() {
    const t = useTranslations('Monitor');
    const { data: session } = useSession();
    const [isMounted, setIsMounted] = React.useState(false);

    // Ensure we only render time-sensitive UI on client
    React.useEffect(() => {
        setIsMounted(true);
    setIsMounted(true);
    }, []);

    const [retryingId, setRetryingId] = React.useState<string | null>(null);

    const { data: stats, isLoading, refetch } = useQuery<FundMonitorStats>({
        queryKey: ['admin', 'fund-monitor'],
        queryFn: () => fundService.getMonitorStats(session),
        refetchInterval: 1000 * 60 * 5, // 5 min
    });

    const handleRetry = async (date: string, code?: string) => {
        const id = code ? `${date}-${code}` : date;
        setRetryingId(id);
        try {
            const res = await fundService.triggerReconciliation({ trade_date: date, fund_code: code }, session);
            if (res.success) {
                toast.success(t('retrySuccess'), {
                    description: `${code ? code : 'All funds'} on ${date}: matched ${res.matched_count}`
                });
                refetch();
            } else {
                toast.error(t('retryFailed'), { description: res.error });
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            toast.error(t('retryFailed'), { description: message });
        } finally {
            setRetryingId(null);
        }
    };

    const anomalies = stats?.anomalies ?? [];

    const heatmapTraces = React.useMemo(() => {
        const heatmap = stats?.heatmap ?? [];
        if (heatmap.length === 0) return null;

        const dates = Array.from(new Set(heatmap.map((h) => h.trade_date))).sort().reverse();
        const categories = Array.from(new Set(heatmap.map((h) => h.category)));
        
        const zMatrix = dates.map(d => {
            return categories.map(c => {
                const match = heatmap.find((h) => h.trade_date === d && h.category === c);
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

    if (isLoading || !isMounted) {
        return <div className="p-8 text-center text-slate-500 animate-pulse">{t('initializing')}</div>;
    }

    const latest = stats?.daily?.[0];
    const reconciliationRate = latest ? (latest.reconciled_count / latest.total_count) * 100 : 0;

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
                
                {stats?.updated_at && isMounted && (
                    <Badge variant="outline" className="font-mono text-[10px] py-1 px-3 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
                        <Clock className="w-3 h-3 mr-1.5 opacity-60" />
                        {t('lastSync', { time: new Date(stats.updated_at).toLocaleTimeString() })}
                    </Badge>
                )}
            </div>

            {/* Health Score Hero */}
            {stats?.health && (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                    <Card className="lg:col-span-2 bg-gradient-to-br from-blue-600 to-indigo-700 text-white border-none shadow-xl shadow-blue-500/20 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform">
                            <ShieldCheck className="w-32 h-32" />
                        </div>
                        <div className="relative z-10 p-2">
                            <p className="text-blue-100 text-xs font-bold uppercase tracking-widest mb-4 flex items-center gap-2">
                                <Zap className="w-3 h-3 fill-current" /> {t('healthScore')}
                            </p>
                            <div className="flex items-center gap-6">
                                <div className="text-6xl font-black tabular-nums tracking-tighter">
                                    {stats.health.score}
                                </div>
                                <div className="flex flex-col">
                                    <div className="text-sm font-bold opacity-80 mb-1">{t('systemHealth')}</div>
                                    <div className="h-2 w-32 bg-white/20 rounded-full overflow-hidden">
                                        <div 
                                            className="h-full bg-white transition-all duration-1000" 
                                            style={{ width: `${stats.health.score}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Card>
                    
                    <div className="grid grid-cols-1 gap-4 lg:col-span-2">
                        <div className="grid grid-cols-3 gap-4 h-full">
                            <Card className="flex flex-col justify-center items-center text-center border-b-4 border-b-emerald-500">
                                <p className="text-[10px] font-bold text-slate-500 uppercase mb-2">{t('coverageLabel')}</p>
                                <span className="text-xl font-black">{stats.health.components.coverage}%</span>
                            </Card>
                            <Card className="flex flex-col justify-center items-center text-center border-b-4 border-b-blue-500">
                                <p className="text-[10px] font-bold text-slate-500 uppercase mb-2">{t('accuracyLabel')}</p>
                                <span className="text-xl font-black">{stats.health.components.accuracy}%</span>
                            </Card>
                            <Card className="flex flex-col justify-center items-center text-center border-b-4 border-b-amber-500">
                                <p className="text-[10px] font-bold text-slate-500 uppercase mb-2">{t('anomalyRate')}</p>
                                <span className="text-xl font-black">{stats.health.components.anomaly}%</span>
                            </Card>
                        </div>
                    </div>
                </div>
            )}

            {/* Quick KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 opacity-50 contrast-75 grayscale-[0.5] hover:opacity-100 hover:grayscale-0 hover:contrast-100 transition-all">
                <Card className="border-l-4 border-l-blue-500">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{t('successRate')}</p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black">{Number(reconciliationRate).toFixed(1)}%</span>
                        <Badge variant={reconciliationRate > 90 ? 'bullish' : 'warning'} className="text-[10px]">
                            {latest?.reconciled_count}/{latest?.total_count}
                        </Badge>
                    </div>
                </Card>
                <Card className="border-l-4 border-l-emerald-500">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">{t('currentMae')}</p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black">{Number(latest?.avg_mae || 0).toFixed(3)}%</span>
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
                                    x: stats?.daily?.map((d) => d.trade_date).reverse(),
                                    y: stats?.daily?.map((d) => d.avg_mae).reverse(),
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
                        {anomalies.length > 0 ? (
                            anomalies.map((a, i: number) => (
                                <div key={i} className="group p-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg flex flex-col gap-2 hover:border-rose-500/50 transition-colors">
                                    <div className="flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono font-bold text-blue-500">{a.fund_code}</span>
                                            <span className="text-[10px] opacity-60 font-mono">{a.trade_date}</span>
                                        </div>
                                        <Badge variant="bearish" className="text-[10px] px-1.5">{Number(a.deviation).toFixed(2)}%</Badge>
                                    </div>
                                    <div className="flex justify-between items-center text-[10px] font-mono mb-1">
                                        <span className="opacity-60">{t('estLabel')} {Number(a.frozen_est_growth).toFixed(2)}%</span>
                                        <span className="opacity-60">{t('actLabel')} {Number(a.official_growth).toFixed(2)}%</span>
                                        <span className="font-bold text-rose-500">{t('gradeLabel')} {a.tracking_status}</span>
                                    </div>
                                    
                                    {/* Sector Drift Drill-down */}
                                    {a.frozen_sector_attribution && (
                                        <div className="mt-2 p-2 bg-white/50 dark:bg-black/20 rounded border border-slate-100 dark:border-slate-800/50">
                                            <p className="text-[9px] font-bold text-slate-500 uppercase flex items-center gap-1 mb-1.5">
                                                <BarChart3 className="w-2.5 h-2.5" /> {t('sectorDrift')}
                                            </p>
                                            <div className="flex flex-col gap-1 max-h-[80px] overflow-y-auto pr-1">
                                                {Object.entries(a.frozen_sector_attribution).slice(0, 5).map(([sector, impact]) => (
                                                    <div key={sector} className="flex justify-between items-center text-[9px]">
                                                        <span className="truncate max-w-[100px] opacity-70">{sector}</span>
                                                        <span className={`font-mono ${Number(impact) >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                                            {Number(impact) >= 0 ? '+' : ''}{Number(impact).toFixed(3)}%
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    <button 
                                        onClick={() => handleRetry(a.trade_date, a.fund_code)}
                                        disabled={retryingId === `${a.trade_date}-${a.fund_code}`}
                                        className="mt-2 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md bg-blue-500 hover:bg-blue-600 text-white text-[10px] font-bold transition-all disabled:opacity-50"
                                    >
                                        <RefreshCw className={`w-3 h-3 ${retryingId === `${a.trade_date}-${a.fund_code}` ? 'animate-spin' : ''}`} />
                                        {retryingId === `${a.trade_date}-${a.fund_code}` ? t('retrying') : t('fixNow')}
                                    </button>
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
                            {stats?.daily?.map((d, i: number) => {
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
                                                <span className="font-mono">{d.reconciled_count} ({Number(rate).toFixed(0)}%)</span>
                                            </div>
                                        </td>
                                        <td className={`p-3 text-right font-mono font-bold ${d.avg_mae > 0.5 ? 'text-amber-500' : 'text-emerald-500'}`}>
                                            {d.avg_mae ? `${Number(d.avg_mae).toFixed(4)}%` : '--'}
                                        </td>
                                        <td className="p-3 text-center">
                                            <div className="flex items-center justify-center gap-4">
                                                {rate >= 95 ? (
                                                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                                ) : (
                                                    <AlertCircle className="w-4 h-4 text-amber-500" />
                                                )}
                                                <button 
                                                    onClick={() => handleRetry(d.trade_date)}
                                                    disabled={retryingId === d.trade_date}
                                                    className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors disabled:opacity-30"
                                                    title={t('retry')}
                                                >
                                                    <RefreshCw className={`w-3.5 h-3.5 text-blue-500 ${retryingId === d.trade_date ? 'animate-spin' : ''}`} />
                                                </button>
                                            </div>
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
