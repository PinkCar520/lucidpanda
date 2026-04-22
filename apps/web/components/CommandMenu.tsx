'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Command } from 'cmdk';
import { 
    Search, Terminal, BarChart3, Activity, 
    User, Settings, Key, Shield, 
    LogOut,
    Loader2, ChevronRight, RefreshCw, Zap, Network
} from 'lucide-react';
import { useRouter } from '@/i18n/navigation';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { atomicSignOut } from '@/lib/auth-cleanup';

interface FundResult {
    code: string;
    name: string;
    type: string;
    company: string;
}

export default function CommandMenu() {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [funds, setFunds] = useState<FundResult[]>([]);
    const [loading, setLoading] = useState(false);
    
    const router = useRouter();
    const { locale } = useParams();
    const { data: session } = useSession();
    
    const tCommand = useTranslations('CommandMenu'); // New namespace
    const tApp = useTranslations('App');
    const tSettings = useTranslations('Settings');
    const tAuth = useTranslations('Auth'); // For Sign Out
    // Toggle the menu when ⌘K is pressed
    useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setOpen((open) => !open);
            }
        };

        document.addEventListener('keydown', down);
        return () => document.removeEventListener('keydown', down);
    }, []);

    // Async fund search
    useEffect(() => {
        if (!search || search.length < 2) {
            setFunds([]);
            return;
        }

        const delayDebounceFn = setTimeout(async () => {
            setLoading(true);
            try {
                const res = await fetch(`/api/v1/web/funds/search?q=${encodeURIComponent(search)}&limit=5`);
                if (res.ok) {
                    const data = await res.json();
                    setFunds(data.results || []);
                }
            } catch (error) {
                console.error('CommandMenu search error:', error);
            } finally {
                setLoading(false);
            }
        }, 300);

        return () => clearTimeout(delayDebounceFn);
    }, [search]);

    const runCommand = useCallback((command: () => void) => {
        setOpen(false);
        command();
    }, []);

    if (!session) return null;

    return (
        <Command.Dialog
            open={open}
            onOpenChange={setOpen}
            label="Global Command Menu"
            className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] p-4 bg-on-surface/20 dark:bg-slate-950/40 backdrop-blur-sm animate-in fade-in duration-300"
        >
            <div className="w-full max-w-[640px] bg-surface dark:bg-slate-900 border border-outline-variant/30 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
                <div className="flex items-center px-4 border-b border-outline-variant/10 dark:border-slate-800">
                    <Search className="w-5 h-5 text-on-surface-variant/40 dark:text-slate-500 mr-3" />
                    <Command.Input
                        autoFocus
                        placeholder={tCommand('placeholder')}
                        value={search}
                        onValueChange={setSearch}
                        className="flex-1 h-14 bg-transparent outline-none text-sm font-sans text-on-surface dark:text-slate-100 placeholder:text-on-surface-variant/30 dark:placeholder:text-slate-500"
                    />
                    <div className="flex items-center gap-1 px-1.5 py-0.5 rounded border border-outline-variant/20 dark:border-slate-700 bg-surface-container-low dark:bg-slate-800 text-[10px] font-bold text-on-surface-variant/40 dark:text-slate-500">
                        {tCommand('escLabel')}
                    </div>
                </div>

                <Command.List className="max-h-[400px] overflow-y-auto p-2 custom-scrollbar">
                    <Command.Empty className="py-10 text-center text-sm font-sans text-on-surface-variant/60 dark:text-slate-500">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center gap-3">
                                <Loader2 className="w-5 h-5 animate-spin text-primary dark:text-blue-500" />
                                <span className="text-xs uppercase tracking-widest font-bold opacity-50">{tCommand('searching')}</span>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center gap-2 opacity-40">
                                <Search className="w-8 h-8 mb-2" />
                                <span>{tCommand('noResults')}</span>
                            </div>
                        )}
                    </Command.Empty>

                    {/* 1. Async Funds Search Results */}
                    {funds.length > 0 && (
                        <Command.Group heading={tCommand('marketFundsGroup')} className="px-3 py-2 text-[10px] font-bold text-on-surface-variant/40 dark:text-slate-500 uppercase tracking-[0.15em]">
                            {funds.map((fund) => (
                                <div key={fund.code} className="flex flex-col gap-1 mb-1">
                                    <Command.Item
                                        onSelect={() => runCommand(() => router.push(`/funds?code=${fund.code}`))}
                                        className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30 aria-selected:text-primary dark:aria-selected:text-blue-400"
                                    >
                                        <div className="w-9 h-9 rounded-lg bg-primary-container/10 dark:bg-emerald-900/30 flex items-center justify-center text-primary dark:text-emerald-500">
                                            <BarChart3 className="w-4 h-4" />
                                        </div>
                                        <div className="flex-1 flex flex-col min-w-0">
                                            <span className="text-sm font-bold font-display truncate">{fund.name}</span>
                                            <span className="text-[10px] font-mono opacity-60 uppercase tracking-tight">{tCommand('viewInFunds')} • {fund.code}</span>
                                        </div>
                                        <ChevronRight className="w-4 h-4 opacity-20" />
                                    </Command.Item>
                                    <Command.Item
                                        onSelect={() => runCommand(() => router.push(`/?code=${fund.code}`))}
                                        className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/10 dark:aria-selected:bg-indigo-900/30 aria-selected:text-primary dark:aria-selected:text-indigo-400"
                                    >
                                        <div className="w-9 h-9 rounded-lg bg-primary-container/20 dark:bg-indigo-900/30 flex items-center justify-center text-primary dark:text-indigo-400">
                                            <Terminal className="w-4 h-4" />
                                        </div>
                                        <div className="flex-1 flex flex-col min-w-0">
                                            <span className="text-sm font-bold font-display truncate">{tCommand('tradeFund', { fundName: fund.name })}</span>
                                            <span className="text-[10px] font-mono opacity-60 uppercase tracking-tight">{tCommand('openInTerminalForExecution')}</span>
                                        </div>
                                        <Zap className="w-4 h-4 opacity-20" />
                                    </Command.Item>
                                </div>
                            ))}
                        </Command.Group>
                    )}


                    {/* 1.5 Quick Actions */}
                    <Command.Group heading={tCommand('quickActionsGroup')} className="px-3 py-2 text-[10px] font-bold text-on-surface-variant/40 dark:text-slate-500 uppercase tracking-[0.15em] mt-3">
                        <Command.Item
                            onSelect={() => runCommand(() => window.location.reload())}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <RefreshCw className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tCommand('reloadAllData')}</span>
                        </Command.Item>
                    </Command.Group>

                    {/* 2. Primary Navigation */}
                    <Command.Group heading={tCommand('navigationGroup')} className="px-3 py-2 text-[10px] font-bold text-on-surface-variant/40 dark:text-slate-500 uppercase tracking-[0.15em] mt-3">
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <Terminal className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tApp('sidebar.terminal')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/funds`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <BarChart3 className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tApp('sidebar.alphaFunds')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/backtest`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <Activity className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tApp('sidebar.backtest')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/graph`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <Network className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tApp('sidebar.graph')}</span>
                        </Command.Item>
                    </Command.Group>

                    {/* 3. Account & Settings */}
                    <Command.Group heading={tCommand('accountSettingsGroup')} className="px-3 py-2 text-[10px] font-bold text-on-surface-variant/40 dark:text-slate-500 uppercase tracking-[0.15em] mt-3">
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/settings/account`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <Settings className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tSettings('accountOverview')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/settings/profile`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <User className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tSettings('profile')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/settings/api-keys`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <Key className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tSettings('apiKeys')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/settings/security`))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all aria-selected:bg-primary/5 dark:aria-selected:bg-blue-900/30"
                        >
                            <Shield className="w-4 h-4 text-on-surface-variant/40 dark:text-slate-500" />
                            <span className="text-sm font-medium">{tSettings('security')}</span>
                        </Command.Item>
                    </Command.Group>

                    {/* 4. System Actions */}
                    <Command.Group heading={tCommand('systemGroup')} className="px-3 py-2 text-[10px] font-bold text-on-surface-variant/40 dark:text-slate-500 uppercase tracking-[0.15em] mt-3">
                        <Command.Item
                            onSelect={() => runCommand(() => atomicSignOut(locale as string))}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 aria-selected:bg-red-500 aria-selected:text-white dark:aria-selected:bg-red-900/40 dark:aria-selected:text-red-400"
                        >
                            <LogOut className="w-4 h-4" />
                            <span className="text-sm font-bold">{tAuth('signOut')}</span>
                        </Command.Item>
                    </Command.Group>
                </Command.List>

                {/* Footer */}
                <div className="px-4 py-3.5 bg-surface-container-low dark:bg-slate-950/50 border-t border-outline-variant/10 dark:border-slate-800 flex items-center justify-between text-[9px] font-bold text-on-surface-variant/40 dark:text-slate-600 uppercase tracking-[0.1em]">
                    <div className="flex items-center gap-5">
                        <span className="flex items-center gap-2">
                            <kbd className="px-1.5 py-0.5 rounded bg-surface-container-lowest dark:bg-slate-800 border border-outline-variant/20 dark:border-slate-700 shadow-sm text-on-surface-variant/60 dark:text-slate-400">↑↓</kbd> {tCommand('navigateHint')}
                        </span>
                        <span className="flex items-center gap-2">
                            <kbd className="px-1.5 py-0.5 rounded bg-surface-container-lowest dark:bg-slate-800 border border-outline-variant/20 dark:border-slate-700 shadow-sm text-on-surface-variant/60 dark:text-slate-400">ENTER</kbd> {tCommand('selectHint')}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 font-mono opacity-60">
                        LUCIDPANDA {tCommand('shellVersion')} V1.2
                    </div>
                </div>
            </div>
        </Command.Dialog>
    );
}
