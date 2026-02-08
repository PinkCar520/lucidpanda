'use client';

import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { useTransition, useState, useRef, useEffect } from 'react';
import { Globe, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { locales, localeNames } from '@/i18n/config';

export default function LanguageSwitcher() {
    const locale = useLocale();
    const router = useRouter();
    const pathname = usePathname();
    const [isPending, startTransition] = useTransition();
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const handleLocaleChange = (nextLocale: string) => {
        setIsOpen(false);
        startTransition(() => {
            router.replace(pathname, { locale: nextLocale });
        });
    };

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const currentName = localeNames[locale as keyof typeof localeNames];
    const tApp = useTranslations('App'); // Assuming 'App' namespace is appropriate for global UI elements

    return (
        <div className="relative" ref={containerRef}>
            {/* Trigger Button - Adaptive Light/Dark Mode */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                title={tApp('shell.languageSwitcher.toggle')}
                className={`flex items-center gap-2 bg-white dark:bg-[#0f172a] hover:bg-slate-50 dark:hover:bg-[#1e293b] border border-slate-200 dark:border-slate-800 rounded-full px-4 py-2 transition-all duration-200 group shadow-sm ${isOpen ? 'ring-2 ring-blue-500/20 border-blue-500/50' : ''}`}
            >
                <Globe className="w-4 h-4 text-blue-600 dark:text-blue-500 group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors" />
                <span className="text-xs font-bold text-slate-700 dark:text-slate-200 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">{currentName}</span>
                {isOpen ? (
                    <ChevronUp className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                ) : (
                    <ChevronDown className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                )}
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="absolute top-full right-0 mt-2 w-40 bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 origin-top-right z-[150]">
                    <div className="p-1 flex flex-col gap-1">
                        {locales.map((cur) => (
                            <button
                                key={cur}
                                onClick={() => handleLocaleChange(cur)}
                                disabled={isPending}
                                className={`flex items-center justify-between w-full px-3 py-2 text-xs font-bold rounded-lg transition-colors ${locale === cur
                                    ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400'
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
                                    }`}
                            >
                                <span className="flex items-center gap-2">
                                    {/* Optional: Add flag icons later if needed */}
                                    {localeNames[cur as keyof typeof localeNames]}
                                </span>
                                {locale === cur && <Check className="w-3 h-3" />}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
