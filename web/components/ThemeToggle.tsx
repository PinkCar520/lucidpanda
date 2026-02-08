'use client';

import React, { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

interface ThemeToggleProps {
    t: (key: string) => string;
}

import { useTheme } from '@/hooks/useTheme';

interface ThemeToggleProps {
    t: (key: string) => string;
}

export default function ThemeToggle({ t }: ThemeToggleProps) {
    const { theme, toggleTheme } = useTheme();

    return (
        <button
            onClick={toggleTheme}
            className="p-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all shadow-sm border border-slate-200 dark:border-slate-700"
            title={theme === 'light' ? t('switchToDarkMode') : t('switchToLightMode')}
        >
            {theme === 'light' ? (
                <Moon className="w-4 h-4" />
            ) : (
                <Sun className="w-4 h-4" />
            )}
        </button>
    );
}
