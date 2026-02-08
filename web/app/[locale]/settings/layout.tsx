'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { usePathname, useParams } from 'next/navigation';
import { User, Shield, Bell, Key, LayoutDashboard, ChevronLeft } from 'lucide-react';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import ThemeToggle from '@/components/ThemeToggle';

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
      href: `/${locale}/settings/account`,
      icon: LayoutDashboard,
    },
    {
      label: t('profile'),
      href: `/${locale}/settings/profile`,
      icon: User,
    },
    {
      label: t('security'),
      href: `/${locale}/settings/security`,
      icon: Shield,
    },
    {
      label: t('notifications'),
      href: `/${locale}/settings/notifications`,
      icon: Bell,
    },
    {
      label: t('apiKeys'),
      href: `/${locale}/settings/api-keys`,
      icon: Key,
    },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-[#020617] text-slate-900 dark:text-slate-100 transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link
              href={`/${locale}`}
              className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-slate-500"
            >
              <ChevronLeft className="w-5 h-5" />
            </Link>
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
          