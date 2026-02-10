'use client';

import React, { useState } from 'react';
import { 
    Terminal, BarChart3, Activity, 
    Settings, HelpCircle, ChevronRight,
    Command, Menu, X, Globe, Check, User, LogOut, ChevronLeft
} from 'lucide-react';
import { Link, usePathname, useRouter } from '@/i18n/navigation';
import { useParams } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { useSession, signOut } from 'next-auth/react';
import UserMenu from './UserMenu';
import LanguageSwitcher from './LanguageSwitcher';
import CommandMenu from './CommandMenu';
import { locales, localeNames } from '@/i18n/config';
import Image from 'next/image';

interface ShellProps {
    children: React.ReactNode;
}

export default function Shell({ children }: ShellProps) {
    const pathname = usePathname();
    const router = useRouter();
    const currentLocale = useLocale();
    const { data: session } = useSession();
    const t = useTranslations('App');
    const tSettings = useTranslations('Settings');
    const tBreadcrumbs = useTranslations('Breadcrumbs');
    const tAuth = useTranslations('Auth');
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    // Check if we are on an auth page to hide sidebar/header
    const isAuthPage = pathname.includes('/login') || 
                       pathname.includes('/register') || 
                       pathname.includes('/forgot-password') || 
                       pathname.includes('/reset-password');

    const getBreadcrumbLabel = (path: string) => {
        if (path === '/' || path === '') return tBreadcrumbs.has('terminal') ? tBreadcrumbs('terminal') : 'Terminal';
        const lastSegment = path.split('/').filter(Boolean).pop() || '';
        if (!lastSegment) return tBreadcrumbs.has('terminal') ? tBreadcrumbs('terminal') : 'Terminal';
        if (tBreadcrumbs.has(lastSegment)) {
            return tBreadcrumbs(lastSegment);
        }
        return lastSegment.replace(/-/g, ' ');
    };

    const handleLocaleChange = (nextLocale: string) => {
        router.replace(pathname, { locale: nextLocale });
        setIsMobileMenuOpen(false);
    };

    const navItems = [
        { id: 'terminal', icon: Terminal, href: `/`, label: t('sidebar.terminal') },
        { id: 'funds', icon: BarChart3, href: `/funds`, label: t('sidebar.alphaFunds') },
        { id: 'backtest', icon: Activity, href: `/backtest`, label: t('sidebar.backtest') },
    ];

    const bottomItems = [
        { id: 'settings', icon: Settings, href: `/settings/account`, label: tSettings('title') },
    ];

    return (
        <div className="flex h-screen bg-white dark:bg-[#020617] overflow-hidden">
            <CommandMenu />
            
            {/* Mobile Menu Overlay */}
            {!isAuthPage && isMobileMenuOpen && (
                <div 
                    className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-[100] md:hidden"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}

            {/* Mobile Sidebar */}
            {!isAuthPage && (
                <aside className={`fixed inset-y-0 left-0 w-[300px] bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 z-[101] transform transition-transform duration-300 ease-in-out md:hidden flex flex-col ${
                    isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
                }`}>
                    {/* Mobile Sidebar Header */}
                    <div className="p-6 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                                    <span className="text-sm font-black">A</span>
                                </div>
                                <span className="font-bold text-slate-900 dark:text-white uppercase tracking-tighter">Alpha Signal</span>
                            </div>
                            <button 
                                onClick={() => setIsMobileMenuOpen(false)}
                                className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {session?.user && (
                            <Link 
                                href="/settings/profile" 
                                className="flex items-center gap-4 group"
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-lg font-bold shadow-lg shadow-blue-500/20 overflow-hidden shrink-0">
                                    {session.user.avatar_url ? (
                                        <Image src={session.user.avatar_url} alt="Avatar" width={48} height={48} className="w-full h-full object-cover" unoptimized={true} />
                                    ) : (
                                        <span>{session.user.name?.[0]?.toUpperCase() || session.user.email?.[0]?.toUpperCase()}</span>
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="font-bold text-slate-900 dark:text-white truncate group-hover:text-blue-600 transition-colors">
                                        {session.user.name || session.user.email?.split('@')[0]}
                                    </div>
                                    <div className="text-xs text-slate-500 truncate">{session.user.email}</div>
                                </div>
                                <ChevronRight className="w-4 h-4 text-slate-400 group-hover:translate-x-1 transition-transform" />
                            </Link>
                        )}
                    </div>

                    <nav className="flex-1 p-4 flex flex-col gap-2 overflow-y-auto">
                        {navItems.map((item) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link 
                                    key={item.id} 
                                    href={item.href}
                                    onClick={() => setIsMobileMenuOpen(false)}
                                >
                                    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                                        isActive 
                                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' 
                                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900'
                                    }`}>
                                        <item.icon className="w-5 h-5" />
                                        <span className="font-bold text-sm">{item.label}</span>
                                    </div>
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-4 bg-slate-50/50 dark:bg-slate-900/20">
                        <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2 px-4 mb-1">
                                <Globe className="w-3 h-3 text-slate-400" />
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('languageSwitcher.label') || 'LANGUAGE'}</span>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                {locales.map((cur) => (
                                    <button
                                        key={cur}
                                        onClick={() => handleLocaleChange(cur)}
                                        className={`flex items-center justify-center px-3 py-2 text-xs font-bold rounded-lg border transition-all ${
                                            currentLocale === cur
                                            ? 'bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-500/20'
                                            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                                        }`}
                                    >
                                        {localeNames[cur as keyof typeof localeNames]}
                                        {currentLocale === cur && <Check className="ml-2 w-3 h-3" />}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="h-px bg-slate-200 dark:bg-slate-800 mx-2" />

                        {bottomItems.map((item) => {
                            const isActive = pathname.startsWith('/settings');
                            return (
                                <Link 
                                    key={item.id} 
                                    href={item.href}
                                    onClick={() => setIsMobileMenuOpen(false)}
                                >
                                    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                                        isActive 
                                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' 
                                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900'
                                    }`}>
                                        <item.icon className="w-5 h-5" />
                                        <span className="font-bold text-sm">{item.label}</span>
                                    </div>
                                </Link>
                            );
                        })}

                        <button 
                            onClick={() => signOut({ callbackUrl: `/${currentLocale}/login` })}
                            className="flex items-center gap-3 px-4 py-3 rounded-xl text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                        >
                            <LogOut className="w-5 h-5" />
                            <span className="font-bold text-sm">{tAuth('signOut')}</span>
                        </button>
                    </div>
                </aside>
            )}

            {/* Desktop Sidebar */}
            {!isAuthPage && (
                <aside className="hidden md:flex w-[64px] flex-col items-center py-4 border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 z-50">
                    <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 mb-8 cursor-pointer hover:scale-105 transition-transform">
                        <span className="text-xl font-black">A</span>
                    </div>

                    <nav className="flex-1 flex flex-col gap-4">
                        {navItems.map((item) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link key={item.id} href={item.href} title={item.label}>
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 group relative ${
                                        isActive 
                                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' 
                                        : 'text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800'
                                    }`}>
                                        <item.icon className="w-5 h-5" />
                                        {!isActive && (
                                            <div className="absolute left-full ml-2 px-2 py-1 bg-slate-900 text-white text-[10px] font-bold rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 shadow-xl">
                                                {item.label}
                                            </div>
                                        )}
                                    </div>
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="flex flex-col gap-4 mt-auto">
                        {bottomItems.map((item) => {
                            const isActive = pathname.startsWith('/settings');
                            return (
                                <Link key={item.id} href={item.href} title={item.label}>
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 group relative ${
                                        isActive 
                                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' 
                                        : 'text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800'
                                    }`}>
                                        <item.icon className="w-5 h-5" />
                                    </div>
                                </Link>
                            );
                        })}
                    </div>
                </aside>
            )}

            {/* 2. Main Content Area */}
            <main className="flex-1 flex flex-col min-w-0 relative">
                {/* Global Header */}
                {!isAuthPage && (
                    <header className="h-[56px] flex items-center justify-between px-4 md:px-8 border-b border-slate-200/60 dark:border-slate-800/50 bg-white/70 dark:bg-[#020617]/70 backdrop-blur-xl saturate-150 sticky top-0 z-50">
                        <div className="flex items-center gap-2 md:gap-4 overflow-hidden">
                            {/* Mobile Menu Toggle */}
                            <button 
                                onClick={() => setIsMobileMenuOpen(true)}
                                className="md:hidden p-2 text-slate-500 hover:bg-slate-100/50 dark:hover:bg-slate-900/50 rounded-lg transition-colors shrink-0"
                            >
                                <Menu className="w-5 h-5" />
                            </button>
                            
                            {/* Breadcrumbs / Page Title */}
                            <div className="flex items-center gap-2 text-[10px] md:text-[10px] font-bold uppercase tracking-widest overflow-hidden font-data">
                                <Link href="/" className="hidden md:block text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors shrink-0">
                                    {t('shell.breadcrumb.alphaSignal')}
                                </Link>
                                <ChevronRight className="hidden md:block w-3 h-3 text-slate-300 shrink-0" />
                                
                                <span className="text-slate-900 dark:text-white truncate text-xs md:text-[10px]">
                                    {getBreadcrumbLabel(pathname)}
                                </span>
                            </div>
                        </div>

                        {/* Right Utilities */}
                        <div className="flex items-center gap-3 md:gap-6 font-data shrink-0">
                            <button 
                                onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
                                className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100/50 dark:bg-slate-900/50 border border-slate-200/50 dark:border-slate-800 text-[10px] font-bold text-slate-500 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors"
                            >
                                <Command className="w-3 h-3" />
                                <span>{t('shell.commandK')}</span>
                            </button>
                            
                            <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block" />
                            
                            <div className="flex items-center gap-4">
                                <div className="hidden md:block">
                                    <LanguageSwitcher key={currentLocale} />
                                </div>
                                <UserMenu />
                            </div>
                        </div>
                    </header>
                )}

                {/* Page Content */}
                <div className={`flex-1 overflow-y-auto custom-scrollbar ${isAuthPage ? 'flex items-center justify-center bg-slate-50 dark:bg-slate-950' : ''}`}>
                    <div className={`${isAuthPage ? 'container mx-auto max-w-md w-full p-4' : 'w-full min-h-full'}`}>
                        {children}
                    </div>
                </div>
            </main>
        </div>
    );
}