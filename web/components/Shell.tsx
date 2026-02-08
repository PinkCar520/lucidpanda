'use client';

import React from 'react';
import { 
    Terminal, BarChart3, Activity, 
    Settings, HelpCircle, ChevronRight,
    Command, Menu, X
} from 'lucide-react';
import Link from 'next/link';
import { usePathname, useParams } from 'next/navigation';
import UserMenu from './UserMenu';
import { useTranslations } from 'next-intl';
import ThemeToggle from './ThemeToggle';
import LanguageSwitcher from './LanguageSwitcher';
import CommandMenu from './CommandMenu';

interface ShellProps {
    children: React.ReactNode;
}

export default function Shell({ children }: ShellProps) {
    const pathname = usePathname();
    const { locale } = useParams();
    const t = useTranslations('App');
    const tSettings = useTranslations('Settings');

    const navItems = [
        { id: 'terminal', icon: Terminal, href: `/${locale}`, label: 'Terminal' },
        { id: 'funds', icon: BarChart3, href: `/${locale}/funds`, label: 'AlphaFunds' },
        { id: 'backtest', icon: Activity, href: `/${locale}/backtest`, label: 'Backtest' },
    ];

    const bottomItems = [
        { id: 'settings', icon: Settings, href: `/${locale}/settings/account`, label: tSettings('title') },
    ];

    return (
        <div className="flex h-screen bg-white dark:bg-[#020617] overflow-hidden">
            <CommandMenu />
            
            {/* 1. Narrow Sidebar Toolbar */}
            <aside className="hidden md:flex w-[64px] flex-col items-center py-4 border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 z-50">
                {/* Logo */}
                <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 mb-8 cursor-pointer hover:scale-105 transition-transform">
                    <span className="text-xl font-black">A</span>
                </div>

                {/* Primary Nav */}
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

                {/* Bottom Nav */}
                <div className="flex flex-col gap-4 mt-auto">
                    {bottomItems.map((item) => {
                        const isActive = pathname.startsWith(item.href.split('/settings')[0] + '/settings');
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

            {/* 2. Main Content Area */}
            <main className="flex-1 flex flex-col min-w-0 relative">
                {/* Global Header */}
                <header className="h-[56px] flex items-center justify-between px-4 md:px-8 border-b border-slate-200 dark:border-slate-800/50 bg-white/80 dark:bg-[#020617]/80 backdrop-blur-md z-40">
                    <div className="flex items-center gap-4">
                        {/* Mobile Menu Toggle */}
                        <button className="md:hidden p-2 text-slate-500">
                            <Menu className="w-5 h-5" />
                        </button>
                        
                        {/* Breadcrumbs / Page Title Context */}
                        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest overflow-hidden font-data">
                            <span className="hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer">AlphaSignal</span>
                            <ChevronRight className="w-3 h-3" />
                            <span className="text-slate-900 dark:text-white truncate">
                                {pathname === `/${locale}` ? 'Terminal' : pathname.split('/').pop()?.replace(/-/g, ' ')}
                            </span>
                        </div>
                    </div>

                    {/* Right Utilities */}
                    <div className="flex items-center gap-3 md:gap-6 font-data">
                        <button 
                            onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
                            className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 text-[10px] font-bold text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                        >
                            <Command className="w-3 h-3" />
                            <span>CMD + K</span>
                        </button>
                        
                        <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block" />
                        
                        <div className="flex items-center gap-4">
                            <ThemeToggle t={t} />
                            <LanguageSwitcher />
                            <UserMenu />
                        </div>
                    </div>
                </header>

                {/* Page Content */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    <div className="container mx-auto max-w-7xl min-h-full">
                        {children}
                    </div>
                </div>
            </main>
        </div>
    );
}
