'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { useParams } from 'next/navigation';
import { User, Shield, Bell, Key, LayoutDashboard, Settings, ChevronRight } from 'lucide-react';

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations('Settings');
  const pathname = usePathname();

  const navItems = [
    {
      label: t('accountOverview'),
      href: `/settings/account`,
      icon: LayoutDashboard,
    },
    {
      label: t('profile'),
      href: `/settings/profile`,
      icon: User,
    },
    {
      label: t('security'),
      href: `/settings/security`,
      icon: Shield,
    },
    {
      label: t('notifications'),
      href: `/settings/notifications`,
      icon: Bell,
    },
    {
      label: t('apiKeys'),
      href: `/settings/api-keys`,
      icon: Key,
    },
  ];

  return (
    <div className="flex flex-col bg-white dark:bg-[#020617] text-slate-900 dark:text-slate-100 min-h-screen">
      {/* 1. Page Header - Optimized for Mobile/Desktop */}
      <div className="bg-white dark:bg-[#020617] border-b border-slate-100 dark:border-slate-800/50 sticky top-0 md:relative z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 md:py-8">
          <div className="flex items-center gap-3 md:gap-4">
            <div className="w-10 h-10 md:w-12 md:h-12 rounded-xl md:rounded-2xl bg-blue-600/10 dark:bg-blue-500/10 flex items-center justify-center shrink-0">
                <Settings className="w-6 h-6 md:w-8 md:h-8 text-blue-600 dark:text-blue-500" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-black tracking-tight">{t('title')}</h1>
              <p className="text-[10px] md:text-sm text-slate-500 dark:text-slate-400 font-mono uppercase tracking-wider">
                {t('subtitle')}
              </p>
            </div>
          </div>
        </div>

        {/* 2. Mobile Sub-Navigation (Horizontal Scroll) */}
        <div className="md:hidden border-t border-slate-100 dark:border-slate-800 overflow-x-auto no-scrollbar bg-white/80 dark:bg-[#020617]/80 backdrop-blur-xl">
          <nav className="flex px-4 py-2 min-w-max gap-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  <item.icon className="w-3 h-3" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      <div className="max-w-7xl mx-auto w-full px-4 md:px-8 py-6 md:py-8 flex flex-col md:flex-row gap-8">
        {/* 3. Desktop Sidebar */}
        <aside className="hidden md:block w-64 shrink-0">
          <div className="sticky top-8">
            <nav className="flex flex-col gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center justify-between px-4 py-3 rounded-xl text-sm font-bold transition-all group ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20 translate-x-1'
                        : 'text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-900/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <item.icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200'}`} />
                      {item.label}
                    </div>
                    {isActive && <ChevronRight className="w-4 h-4 opacity-50" />}
                  </Link>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* 4. Main Content Area */}
        <main className="flex-1 min-w-0">
          <div className="bg-slate-50/50 dark:bg-slate-900/20 rounded-2xl md:rounded-3xl border border-slate-200 dark:border-slate-800/50 p-4 md:p-8 lg:p-10">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}