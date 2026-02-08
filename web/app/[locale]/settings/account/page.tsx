'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { 
    Wallet, TrendingUp, ShieldCheck, Zap, 
    ArrowUpRight, ArrowDownRight, Activity, 
    ExternalLink, Star, Shield, Loader2 
} from 'lucide-react';
import { authenticatedFetch } from '@/lib/api-client';

interface AssetOverview {
    total_assets: number;
    available_funds: number;
    frozen_funds: number;
    pnl_today: number;
    pnl_percentage: number;
    active_strategies: number;
    watchlist_count: number;
}

export default function AccountOverviewPage() {
  const t = useTranslations('Settings');
  const { data: sessionData } = useSession();
  
  const [overview, setOverview] = useState<AssetOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (sessionData) {
        fetchOverview();
    }
  }, [sessionData]);

  const fetchOverview = async () => {
    try {
        const res = await authenticatedFetch('/api/v1/auth/assets/me/overview', sessionData);
        if (res.ok) {
            const data = await res.json();
            setOverview(data);
        }
    } catch (error) {
        console.error("Failed to fetch asset overview", error);
    } finally {
        setLoading(false);
    }
  };

  if (loading) {
      return (
          <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
      );
  }

  return (
    <div className="flex flex-col gap-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold">{t('accountOverview')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Your financial health and system status at a glance.
        </p>
      </div>

      {/* Asset Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6 bg-gradient-to-br from-blue-600 to-indigo-700 text-white border-none shadow-xl shadow-blue-500/20">
              <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                      <Wallet className="w-6 h-6 opacity-80" />
                      <Badge variant="neutral" className="bg-white/20 border-none text-white backdrop-blur-md">
                          USD
                      </Badge>
                  </div>
                  <div>
                      <div className="text-[10px] font-bold uppercase tracking-widest opacity-70 mb-1">{t('totalAssets')}</div>
                      <div className="text-2xl font-black">${overview?.total_assets.toLocaleString()}</div>
                  </div>
                  <div className="flex items-center gap-4 mt-2 pt-4 border-t border-white/10 text-xs">
                      <div className="flex flex-col">
                          <span className="opacity-60">{t('availableFunds')}</span>
                          <span className="font-bold">${overview?.available_funds.toLocaleString()}</span>
                      </div>
                      <div className="flex flex-col">
                          <span className="opacity-60">{t('frozenFunds')}</span>
                          <span className="font-bold">${overview?.frozen_funds.toLocaleString()}</span>
                      </div>
                  </div>
              </div>
          </Card>

          <Card className="p-6">
              <div className="flex flex-col gap-4 h-full">
                  <div className="flex items-center justify-between">
                      <TrendingUp className="w-6 h-6 text-emerald-500" />
                      <div className={`flex items-center gap-1 text-xs font-bold ${overview && overview.pnl_today >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                          {overview && overview.pnl_today >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                          {overview?.pnl_percentage}%
                      </div>
                  </div>
                  <div>
                      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">{t('todayPnL')}</div>
                      <div className={`text-2xl font-black ${overview && overview.pnl_today >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600'}`}>
                          {overview && overview.pnl_today >= 0 ? '+' : ''}${overview?.pnl_today.toLocaleString()}
                      </div>
                  </div>
                  <div className="mt-auto">
                      <p className="text-[10px] text-slate-400 italic">Market performance across all active strategies.</p>
                  </div>
              </div>
          </Card>

          <Card className="p-6">
              <div className="flex flex-col gap-4 h-full">
                  <div className="flex items-center justify-between">
                      <Zap className="w-6 h-6 text-amber-500" />
                      <div className="flex items-center gap-1 text-xs font-bold text-slate-500">
                          <Activity className="w-3 h-3" />
                          Live
                      </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                      <div>
                          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">{t('activeStrategies')}</div>
                          <div className="text-xl font-black">{overview?.active_strategies}</div>
                      </div>
                      <div>
                          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">{t('watchlistCount')}</div>
                          <div className="text-xl font-black">{overview?.watchlist_count}</div>
                      </div>
                  </div>
                  <div className="mt-auto pt-4 flex gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[10px] text-slate-500 font-bold uppercase">System Engine Optimal</span>
                  </div>
              </div>
          </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Quick Links */}
          <div className="lg:col-span-1">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
                  <ExternalLink className="w-4 h-4 text-blue-500" />
                  {t('quickLinks')}
              </div>
              <div className="flex flex-col gap-3">
                  <Link href={`/${sessionData?.user?.id ? sessionData.user.id : ''}`} className="group">
                      <Card className="p-4 hover:border-blue-500/50 transition-all group-hover:shadow-md">
                          <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600">
                                      <Activity className="w-4 h-4" />
                                  </div>
                                  <span className="text-sm font-bold">{t('viewTrading')}</span>
                              </div>
                              <ArrowUpRight className="w-4 h-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                          </div>
                      </Card>
                  </Link>
                  <Link href={`/en/funds`} className="group">
                      <Card className="p-4 hover:border-emerald-500/50 transition-all group-hover:shadow-md">
                          <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600">
                                      <TrendingUp className="w-4 h-4" />
                                  </div>
                                  <span className="text-sm font-bold">{t('viewFunds')}</span>
                              </div>
                              <ArrowUpRight className="w-4 h-4 text-slate-300 group-hover:text-emerald-500 transition-colors" />
                          </div>
                      </Card>
                  </Link>
              </div>
          </div>

          {/* Security Status */}
          <div className="lg:col-span-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
                  <Shield className="w-4 h-4 text-purple-500" />
                  Security Status
              </div>
              <Card className="p-6">
                  <div className="flex flex-col md:flex-row gap-8">
                      <div className="flex-1 flex flex-col gap-4">
                          <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${sessionData?.user?.is_two_fa_enabled ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'}`}>
                                  <ShieldCheck className="w-6 h-6" />
                              </div>
                              <div>
                                  <div className="text-sm font-bold">Two-Factor Authentication</div>
                                  <div className={`text-xs font-medium ${sessionData?.user?.is_two_fa_enabled ? 'text-emerald-500' : 'text-amber-500'}`}>
                                      {sessionData?.user?.is_two_fa_enabled ? 'Enabled & Protecting your account' : 'Action Required: Enable 2FA for better security'}
                                  </div>
                              </div>
                          </div>
                          {!sessionData?.user?.is_two_fa_enabled && (
                              <Link href="/en/settings/security">
                                  <button className="text-xs font-bold text-blue-600 hover:text-blue-700 underline underline-offset-4">
                                      Protect my account now →
                                  </button>
                              </Link>
                          )}
                      </div>
                      <div className="flex-1 flex flex-col gap-4 border-t md:border-t-0 md:border-l border-slate-100 dark:border-slate-800 pt-4 md:pt-0 md:pl-8">
                          <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                                  <Star className="w-6 h-6" />
                              </div>
                              <div>
                                  <div className="text-sm font-bold">Identity Status</div>
                                  <div className="text-xs text-slate-500 font-medium">
                                      Member Tier: Standard (Level 1)
                                  </div>
                              </div>
                          </div>
                          <div className="text-[10px] text-slate-400 italic">Verify your identity to increase limits.</div>
                      </div>
                  </div>
              </Card>
          </div>
      </div>
    </div>
  );
}
