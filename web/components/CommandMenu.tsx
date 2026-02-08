'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Command } from 'cmdk';
import { 
    Search, Terminal, BarChart3, Activity, 
    User, Settings, Key, Shield, Bell, 
    Moon, Sun, LogOut, Globe, Command as CommandIcon,
    Loader2, TrendingUp, ChevronRight, RefreshCw, Zap
} from 'lucide-react';
import { useRouter, useParams, usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useSession, signOut } from 'next-auth/react';
import { useTheme } from '@/hooks/useTheme';
import { authenticatedFetch } from '@/lib/api-client';

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
    const pathname = usePathname();
    const { data: session } = useSession();
    const { theme, toggleTheme } = useTheme();
    
    const t = useTranslations('Dashboard');
    const tApp = useTranslations('App');
    const tSettings = useTranslations('Settings');
    const tFunds = useTranslations('Funds');

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
                const res = await fetch(`/api/funds/search?q=${encodeURIComponent(search)}&limit=5`);
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
            className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] p-4 bg-slate-950/20 backdrop-blur-sm animate-in fade-in duration-300"
        >
            <div className="w-full max-w-[640px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
                <div className="flex items-center px-4 border-b border-slate-100 dark:border-slate-800">
                    <Search className="w-5 h-5 text-slate-400 mr-3" />
                    <Command.Input
                        autoFocus
                        placeholder="Search for funds, actions or settings..."
                        value={search}
                        onValueChange={setSearch}
                        className="flex-1 h-14 bg-transparent outline-none text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400"
                    />
                    <div className="flex items-center gap-1 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-[10px] font-bold text-slate-400">
                        ESC
                    </div>
                </div>

                <Command.List className="max-h-[400px] overflow-y-auto p-2 custom-scrollbar">
                    <Command.Empty className="py-6 text-center text-sm text-slate-500">
                        {loading ? (
                            <div className="flex items-center justify-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Searching...
                            </div>
                        ) : (
                            'No results found.'
                        )}
                    </Command.Empty>

                    {/* 1. Async Funds Search Results */}
                    {funds.length > 0 && (
                        <Command.Group heading="Market Funds" className="px-2 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                            {funds.map((fund) => (
                                <div key={fund.code} className="flex flex-col gap-1 mb-1">
                                    <Command.Item
                                        onSelect={() => runCommand(() => router.push(`/${locale}/funds?code=${fund.code}`))}
                                        className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30 aria-selected:text-blue-600 dark:aria-selected:text-blue-400"
                                    >
                                        <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600">
                                            <BarChart3 className="w-4 h-4" />
                                        </div>
                                        <div className="flex-1 flex flex-col min-w-0">
                                            <span className="text-sm font-bold truncate">{fund.name}</span>
                                            <span className="text-[10px] font-mono opacity-60">View in AlphaFunds • {fund.code}</span>
                                        </div>
                                        <ChevronRight className="w-4 h-4 opacity-30" />
                                    </Command.Item>
                                    <Command.Item
                                        onSelect={() => runCommand(() => router.push(`/${locale}?code=${fund.code}`))}
                                        className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-indigo-50 dark:aria-selected:bg-indigo-900/30 aria-selected:text-indigo-600 dark:aria-selected:text-indigo-400"
                                    >
                                        <div className="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600">
                                            <Terminal className="w-4 h-4" />
                                        </div>
                                        <div className="flex-1 flex flex-col min-w-0">
                                            <span className="text-sm font-bold truncate">Trade {fund.name}</span>
                                            <span className="text-[10px] font-mono opacity-60">Open in Terminal for Execution</span>
                                        </div>
                                        <Zap className="w-4 h-4 opacity-30" />
                                    </Command.Item>
                                </div>
                            ))}
                        </Command.Group>
                    )}

                    {/* 1.5 Quick Actions */}
                    <Command.Group heading="Quick Actions" className="px-2 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2">
                        <Command.Item
                            onSelect={() => runCommand(() => toggleTheme())}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            {theme === 'light' ? <Moon className="w-4 h-4 text-slate-400" /> : <Sun className="w-4 h-4 text-slate-400" />}
                            <span className="text-sm">Switch to {theme === 'light' ? 'Dark' : 'Light'} Mode</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => window.location.reload())}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <RefreshCw className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">Reload All Data</span>
                        </Command.Item>
                    </Command.Group>

                    {/* 2. Primary Navigation */}
                    <Command.Group heading="Navigation" className="px-2 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2">
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/${locale}`))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <Terminal className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">Terminal Dashboard</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/${locale}/funds`))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <BarChart3 className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">AlphaFunds Valuation</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/${locale}/backtest`))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <Activity className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">Backtest Performance</span>
                        </Command.Item>
                    </Command.Group>

                    {/* 3. Account & Settings */}
                    <Command.Group heading="Account & Settings" className="px-2 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2">
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/${locale}/settings/account`))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <Settings className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">{tSettings('accountOverview')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/${locale}/settings/profile`))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <User className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">{tSettings('profile')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/${locale}/settings/api-keys`))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <Key className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">{tSettings('apiKeys')}</span>
                        </Command.Item>
                        <Command.Item
                            onSelect={() => runCommand(() => router.push(`/${locale}/settings/security`))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/30"
                        >
                            <Shield className="w-4 h-4 text-slate-400" />
                            <span className="text-sm">{tSettings('security')}</span>
                        </Command.Item>
                    </Command.Group>

                    {/* 4. System Actions */}
                    <Command.Group heading="System" className="px-2 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2">
                        <Command.Item
                            onSelect={() => runCommand(() => signOut({ callbackUrl: `/${locale}/login` }))}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 transition-colors aria-selected:bg-red-50 dark:aria-selected:bg-red-900/30"
                        >
                            <LogOut className="w-4 h-4" />
                            <span className="text-sm">Sign Out</span>
                        </Command.Item>
                    </Command.Group>
                </Command.List>

                {/* Footer */}
                <div className="px-4 py-3 bg-slate-50 dark:bg-slate-950/50 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[10px] font-medium text-slate-400 uppercase tracking-widest">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5">
                            <kbd className="px-1 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">↑↓</kbd> Navigate
                        </span>
                        <span className="flex items-center gap-1.5">
                            <kbd className="px-1 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">ENTER</kbd> Select
                        </span>
                    </div>
                    <div className="flex items-center gap-1.5 font-data">
                        AlphaSignal Shell v1.1
                    </div>
                </div>
            </div>
        </Command.Dialog>
    );
}