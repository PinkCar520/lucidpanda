'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { useParams } from 'next/navigation';
import { User, Shield, Bell, Key, LayoutDashboard, ChevronLeft, Settings } from 'lucide-react';
import LanguageSwitcher from '@/components/LanguageSwitcher';

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations('Settings');
  const tApp = useTranslations('App');
  const pathname = usePathname();
  const { locale } = useParams();

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
    <div className="min-h-screen bg-white dark:bg-[#020617] text-slate-900 dark:text-slate-100 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-blue-600/10 dark:bg-blue-500/10 flex items-center justify-center shrink-0">
                <Settings className="w-8 h-8 text-blue-600 dark:text-blue-500" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight">{t('title')}</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 font-mono uppercase tracking-wider">
                {t('subtitle')}
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
          {/* Sidebar */}
          <aside className="md:col-span-3">
            <nav className="flex flex-col gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-bold transition-all ${
                      isActive
                        ? 'bg-blue-600 dark:bg-emerald-500 text-white shadow-lg'
                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900/50'
                    }`}
                  >
                    <item.icon className="w-4 h-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </aside>

          {/* Main Content */}
          <main className="md:col-span-9 bg-slate-50/50 dark:bg-slate-900/20 rounded-2xl p-6 border border-slate-200 dark:border-slate-800/50 min-h-[500px]">
            {children}
                    </main>
                  </div>
                </div>
              </div>
            );
          }
          