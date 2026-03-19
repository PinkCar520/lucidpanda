'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useSourceMonitorQuery } from '@/hooks/api/use-source-monitor-query';
import { Activity, ShieldCheck, BarChart3, Clock } from 'lucide-react';

export default function SourceMonitorPage() {
  const t = useTranslations('SourceMonitor');
  const { data, isLoading, error } = useSourceMonitorQuery(14, 15);

  if (isLoading) {
    return <div className="p-8 text-center text-slate-500 animate-pulse">{t('loading')}</div>;
  }

  if (error || !data) {
    return <div className="p-8 text-center text-rose-500">{t('loadFailed')}</div>;
  }

  const overview = data.overview || { active_sources: 0, total_signals: 0, overall_accuracy_pct: 0 };
  const leaderboard = data.leaderboard || [];
  const trend = data.trend || [];
  const trendMap: Record<string, Array<{ day: string; accuracy_pct: number | null; total_signals: number }>> = {};
  for (const row of trend) {
    const key = row.source_name;
    if (!trendMap[key]) trendMap[key] = [];
    trendMap[key].push({
      day: row.day,
      accuracy_pct: row.accuracy_pct,
      total_signals: row.total_signals,
    });
  }

  return (
    <div className="flex flex-col p-4 md:p-6 lg:p-8 gap-6 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-black tracking-tight flex items-center gap-3">
            <ShieldCheck className="w-7 h-7 text-blue-600" />
            {t('title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{t('subtitle')}</p>
        </div>
        <Badge variant="outline" className="font-mono text-[10px]">
          <Clock className="w-3 h-3 mr-1" />
          {t('windowDays', { days: data.window_days })}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-blue-500">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">{t('activeSources')}</p>
          <p className="text-2xl font-black">{overview.active_sources || 0}</p>
        </Card>
        <Card className="border-l-4 border-l-emerald-500">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">{t('totalSignals')}</p>
          <p className="text-2xl font-black">{overview.total_signals || 0}</p>
        </Card>
        <Card className="border-l-4 border-l-amber-500">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">{t('overallAccuracy')}</p>
          <p className="text-2xl font-black">
            {overview.overall_accuracy_pct != null ? `${Number(overview.overall_accuracy_pct).toFixed(2)}%` : '--'}
          </p>
        </Card>
      </div>

      <Card title={t('leaderboardTitle')} className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase tracking-wider font-bold">
                <th className="p-3">#</th>
                <th className="p-3">{t('source')}</th>
                <th className="p-3">{t('signals')}</th>
                <th className="p-3">{t('hits')}</th>
                <th className="p-3">{t('conservativeAccuracy')}</th>
                <th className="p-3">{t('lastSeen')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
              {leaderboard.map((row, index) => {
                const accuracy = row.accuracy_lower_bound ?? 0;
                const variant = accuracy >= 65 ? 'bullish' : accuracy >= 50 ? 'neutral' : 'bearish';
                return (
                  <tr key={row.source_name} className="hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors">
                    <td className="p-3 font-mono">{index + 1}</td>
                    <td className="p-3 font-semibold">{row.source_name}</td>
                    <td className="p-3">{row.total_signals}</td>
                    <td className="p-3">{row.hits}</td>
                    <td className="p-3">
                      <Badge variant={variant}>{Number(accuracy).toFixed(2)}%</Badge>
                    </td>
                    <td className="p-3 font-mono text-[11px]">
                      {row.last_seen ? new Date(row.last_seen).toLocaleString() : '--'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title={t('trendTitle')}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {leaderboard.slice(0, 6).map((item) => {
            const points = (trendMap[item.source_name] || []).slice(-7);
            return (
              <div key={item.source_name} className="p-3 rounded-lg border border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm">{item.source_name}</span>
                  <BarChart3 className="w-4 h-4 text-slate-400" />
                </div>
                <div className="flex flex-wrap gap-2">
                  {points.length > 0 ? points.map((point) => (
                    <Badge key={`${item.source_name}-${point.day}`} variant="outline">
                      {new Date(point.day).toLocaleDateString()} · {point.accuracy_pct != null ? `${Number(point.accuracy_pct).toFixed(1)}%` : '--'}
                    </Badge>
                  )) : <span className="text-xs text-slate-500">{t('noTrendData')}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="text-xs text-slate-500 flex items-center gap-2">
        <Activity className="w-4 h-4" />
        {t('footnote')}
      </div>
    </div>
  );
}
