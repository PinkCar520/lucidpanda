'use client';

import React, { useState } from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Progress from '@radix-ui/react-progress';
import { 
    User, Settings, ShieldCheck, ShieldAlert, 
    LogOut, Sun, Moon, CreditCard, ChevronRight, 
    Zap, Terminal, BarChart3 
} from 'lucide-react';
import { useSession, signOut } from 'next-auth/react';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function UserMenu() {
    const { data: session } = useSession();
    const t = useTranslations('Settings');
    const tApp = useTranslations('App');
    const { locale } = useParams();
    const [open, setOpen] = useState(false);

    if (!session || !session.user) return null;

    const user = session.user;
    // Mock quota for demo
    const apiQuota = 65; 

    return (
        <DropdownMenu.Root open={open} onOpenChange={setOpen}>
            <DropdownMenu.Trigger asChild>
                <button 
                    onMouseEnter={() => setOpen(true)}
                    className="flex items-center gap-2 p-1 pr-3 rounded-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 hover:border-blue-500/50 transition-all outline-none group"
                >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow-lg shadow-blue-500/20 group-hover:scale-105 transition-transform">
                        {user.avatar_url ? (
                            <img src={user.avatar_url} alt="Avatar" className="w-full h-full rounded-full object-cover" />
                        ) : (
                            user.name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase()
                        )}
                    </div>
                    <span className="text-xs font-bold text-slate-600 dark:text-slate-300 hidden md:block">
                        {user.name || user.email?.split('@')[0]}
                    </span>
                </button>
            </DropdownMenu.Trigger>

            <DropdownMenu.Portal>
                <DropdownMenu.Content 
                    onMouseLeave={() => setOpen(false)}
                    className="z-[100] min-w-[280px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl shadow-black/20 p-2 animate-in fade-in zoom-in-95 duration-200"
                    sideOffset={8}
                    align="end"
                >
                    {/* User Profile Header */}
                    <div className="p-4 flex flex-col gap-1">
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Account Status</span>
                            <Badge text="PRO" color="bg-blue-500" />
                        </div>
                        <div className="font-bold text-slate-900 dark:text-white truncate">{user.email}</div>
                        <div className="text-[10px] text-slate-500 font-mono tracking-tight">UID: {user.id.slice(0, 8)}...</div>
                    </div>

                    <DropdownMenu.Separator className="h-px bg-slate-100 dark:bg-slate-800 my-2" />

                    {/* Security Status */}
                    <div className="px-4 py-2">
                        <div className="flex items-center justify-between mb-3 p-2 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800/50">
                            <div className="flex items-center gap-3">
                                {user.is_two_fa_enabled ? (
                                    <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                                        <ShieldCheck className="w-4 h-4" />
                                    </div>
                                ) : (
                                    <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-500">
                                        <ShieldAlert className="w-4 h-4" />
                                    </div>
                                )}
                                <div>
                                    <div className="text-[11px] font-bold">2FA Security</div>
                                    <div className={`text-[9px] ${user.is_two_fa_enabled ? 'text-emerald-500' : 'text-amber-500'}`}>
                                        {user.is_two_fa_enabled ? 'Active' : 'Unprotected'}
                                    </div>
                                </div>
                            </div>
                            <Link href={`/${locale}/settings/security`}>
                                <button className="p-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                                    <ChevronRight className="w-4 h-4 text-slate-400" />
                                </button>
                            </Link>
                        </div>

                        {/* API Quota */}
                        <div className="flex flex-col gap-2 mb-2">
                            <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                                <span>API Requests</span>
                                <span>{apiQuota}%</span>
                            </div>
                            <Progress.Root className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                <Progress.Indicator 
                                    className="h-full bg-blue-600 transition-all duration-500"
                                    style={{ width: `${apiQuota}%` }}
                                />
                            </Progress.Root>
                        </div>
                    </div>

                    <DropdownMenu.Separator className="h-px bg-slate-100 dark:bg-slate-800 my-2" />

                    {/* Menu Items */}
                    <div className="flex flex-col gap-1 p-1">
                        <DropdownMenu.Item asChild className="outline-none">
                            <Link href={`/${locale}/settings/profile`} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                                <User className="w-4 h-4 text-slate-400" />
                                {t('profile')}
                            </Link>
                        </DropdownMenu.Item>
                        <DropdownMenu.Item asChild className="outline-none">
                            <Link href={`/${locale}/settings/account`} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                                <Settings className="w-4 h-4 text-slate-400" />
                                {t('accountOverview')}
                            </Link>
                        </DropdownMenu.Item>
                        <DropdownMenu.Item asChild className="outline-none">
                            <Link href={`/${locale}/settings/api-keys`} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                                <Zap className="w-4 h-4 text-slate-400" />
                                {t('apiKeys')}
                            </Link>
                        </DropdownMenu.Item>
                    </div>

                    <DropdownMenu.Separator className="h-px bg-slate-100 dark:bg-slate-800 my-2" />

                    <DropdownMenu.Item 
                        onSelect={() => signOut({ callbackUrl: `/${locale}/login` })}
                        className="outline-none"
                    >
                        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                            <LogOut className="w-4 h-4" />
                            {tApp('logout', { email: '' }).split(' (')[0]}
                        </button>
                    </DropdownMenu.Item>
                </DropdownMenu.Content>
            </DropdownMenu.Portal>
        </DropdownMenu.Root>
    );
}

function Badge({ text, color }: { text: string; color: string }) {
    return (
        <span className={`${color} text-white text-[8px] font-black px-1.5 py-0.5 rounded tracking-tighter`}>
            {text}
        </span>
    );
}
