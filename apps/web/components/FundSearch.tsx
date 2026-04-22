'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Clock, Plus } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useSession } from 'next-auth/react';
import { authenticatedFetch } from '@/lib/api-client';

interface FundSearchResult {
    code: string;
    name: string;
    type?: string;
    company?: string;
}

interface FundSearchProps {
    onAddFund: (code: string, name: string) => void;
    existingCodes: string[];
    // Removed placeholder prop, will use t('addPlaceholder') directly
}

export default function FundSearch({ onAddFund, existingCodes }: FundSearchProps) {
    const { data: session } = useSession();
    const [query, setQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [searchResults, setSearchResults] = useState<FundSearchResult[]>([]);
    const [searchHistory, setSearchHistory] = useState<FundSearchResult[]>([]); // Store objects: {code, name, ...}
    const [activeIndex, setActiveIndex] = useState(-1);
    const [isLoading, setIsLoading] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const t = useTranslations('Funds');
    const tApp = useTranslations('App'); // Assuming 'App' namespace for general strings

    // Load search history from localStorage
    useEffect(() => {
        if (typeof window !== 'undefined') {
            try {
                // Try to load new format first
                const historyV2 = localStorage.getItem('fund_search_history_v2');
                if (historyV2) {
                    setSearchHistory(JSON.parse(historyV2));
                } else {
                    // Fallback to legacy format (array of strings)
                    const history = localStorage.getItem('fund_search_history');
                    if (history) {
                        const legacy = JSON.parse(history);
                        // Convert to object format
                        setSearchHistory(legacy.map((code: string) => ({ code, name: tApp('lastSearch') })));
                    }
                }
            } catch (e) {
                console.error('Failed to load search history:', e);
            }
        }
    }, [tApp]);

    // Clear search history
    const clearHistory = () => {
        setSearchHistory([]);
        if (typeof window !== 'undefined') {
            localStorage.removeItem('fund_search_history_v2');
        }
    };

    // Save search history to localStorage
    const saveToHistory = (fund: { code: string, name: string, type?: string, company?: string }) => {
        // Remove existing if any
        const filtered = searchHistory.filter(item => item.code !== fund.code);
        // Add to front with all metadata
        const newHistory = [{
            code: fund.code,
            name: fund.name || t('unnamedFund'), // Need to add unnamedFund to en.json if I use it
            type: fund.type,
            company: fund.company
        }, ...filtered].slice(0, 8); // Store up to 8 items

        setSearchHistory(newHistory);
        if (typeof window !== 'undefined') {
            try {
                localStorage.setItem('fund_search_history_v2', JSON.stringify(newHistory));
            } catch (e) {
                console.error('Failed to save search history:', e);
            }
        }
    };

    // Search logic with debouncing and request cancellation
    // Search function definition
    const performSearch = async (searchTerm: string) => {
        if (!searchTerm.trim()) {
            setSearchResults([]);
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        try {
            const response = await authenticatedFetch(
                `/api/v1/web/funds/search?q=${encodeURIComponent(searchTerm)}&limit=20`,
                session
            );
            const data = await response.json();
            if (data.results) {
                setSearchResults(data.results);
            }
        } catch (e) {
            console.error('Search failed:', e);
            setSearchResults([]);
        } finally {
            setIsLoading(false);
        }
    };

    // Manual debounce for input change
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setQuery(val);

        // Clear existing timeout
        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        if (val.trim()) {
            // Set new timeout
            searchTimeoutRef.current = setTimeout(() => {
                performSearch(val);
            }, 360);
        } else {
            setSearchResults([]);
            setIsLoading(false);
        }
    };

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, []);

    // Click outside to close
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (fund: FundSearchResult) => {
        onAddFund(fund.code, fund.name);
        // Save full object to history
        saveToHistory({
            code: fund.code,
            name: fund.name,
            type: fund.type,
            company: fund.company
        });
        setQuery('');
        setIsOpen(false);
        setActiveIndex(-1);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!isOpen) {
            if (e.key === 'Enter' || e.key === 'ArrowDown') {
                setIsOpen(true);
            }
            return;
        }

        const items = query ? searchResults : getRecommendations();

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setActiveIndex(prev => (prev < items.length - 1 ? prev + 1 : prev));
                break;
            case 'ArrowUp':
                e.preventDefault();
                setActiveIndex(prev => (prev > 0 ? prev - 1 : -1));
                break;
            case 'Enter':
                e.preventDefault();
                if (isLoading) {
                    // Do nothing while loading to prevent accidental adds
                    return;
                }

                if (activeIndex >= 0 && items[activeIndex]) {
                    // Select active item
                    handleSelect(items[activeIndex]);
                } else if (items.length > 0) {
                    // Auto-select first item if valid results exist
                    handleSelect(items[0]);
                } else if (query.trim()) {
                    // Only direct add if no results and not loading
                    onAddFund(query.trim(), '');
                    saveToHistory({ code: query.trim(), name: tApp('customAdd') });
                    setQuery('');
                    setIsOpen(false);
                }
                break;
            case 'Escape':
                setIsOpen(false);
                setActiveIndex(-1);
                break;
        }
    };

    // Removed popularFunds state

    const getRecommendations = (): FundSearchResult[] => {
        // Now returns ALL history, no more filtering by 'existingCodes'
        return searchHistory;
    };

    const displayItems = query ? searchResults : getRecommendations();

    return (
        <div className="relative font-sans" ref={dropdownRef}>
            {/* Search Input */}
            <div className="relative group">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-on-surface-variant/50 dark:text-slate-500 group-focus-within:text-primary transition-colors" />
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={handleInputChange}
                    onFocus={() => setIsOpen(true)}
                    onKeyDown={handleKeyDown}
                    placeholder={t('addPlaceholder')}
                    className="w-full bg-surface-container-low dark:bg-slate-900/50 border-none dark:border dark:border-slate-800 rounded-lg py-2.5 pl-9 pr-8 text-sm focus:bg-surface-container-lowest dark:focus:bg-slate-900 focus:ring-1 focus:ring-outline-variant/30 dark:focus:ring-emerald-500/20 outline-none transition-all text-on-surface dark:text-slate-200 placeholder-on-surface-variant/40 dark:placeholder-slate-500"
                />
                {query && (
                    <button
                        onClick={() => {
                            setQuery('');
                            inputRef.current?.focus();
                        }}
                        className="absolute right-2 top-2.5 text-on-surface-variant/40 hover:text-on-surface dark:text-slate-500 dark:hover:text-slate-300 transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Dropdown */}
            {isOpen && (
                <div className="absolute z-50 w-full mt-2 bg-surface/70 dark:bg-slate-900/95 backdrop-blur-xl border border-outline-variant dark:border-slate-800 rounded-xl shadow-2xl max-h-80 overflow-y-auto flex flex-col min-h-[100px] animate-in fade-in slide-in-from-top-2 duration-200">
                    {/* Content Layer */}
                    <div className={`flex-1 flex flex-col transition-opacity duration-200 ${isLoading ? 'opacity-40 pointer-events-none' : 'opacity-100'}`}>
                        {displayItems.length > 0 ? (
                            <>
                                {/* Header */}
                                <div className="px-4 py-3 shrink-0 sticky top-0 z-10 bg-transparent">
                                    <div className="flex items-center gap-2 text-[10px] text-on-surface-variant/60 dark:text-slate-500 font-bold uppercase tracking-[0.1em]">
                                        {query ? (
                                            <>
                                                <Search className="w-3 h-3" />
                                                <span>{t('searchMatches')} ({searchResults.length})</span>
                                            </>
                                        ) : (
                                            <div className="flex items-center justify-between w-full">
                                                <div className="flex items-center gap-2">
                                                    <Clock className="w-3 h-3" />
                                                    <span>{t('recentQueries')}</span>
                                                </div>
                                                {searchHistory.length > 0 && (
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            clearHistory();
                                                        }}
                                                        className="text-[10px] text-primary dark:text-blue-400 hover:opacity-70 normal-case tracking-normal font-bold"
                                                    >
                                                        {t('clearHistory')}
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Results List */}
                                <div className="pb-2">
                                    {displayItems.map((fund, index) => {
                                        const isActive = index === activeIndex;
                                        const isHistory = !query && searchHistory.some(h => h.code === fund.code);
                                        const isAdded = existingCodes.includes(fund.code);

                                        return (
                                            <button
                                                key={fund.code}
                                                onClick={() => !isAdded && handleSelect(fund)}
                                                onMouseEnter={() => setActiveIndex(index)}
                                                disabled={isAdded}
                                                className={`w-full px-4 py-3 text-left transition-all ${isActive
                                                    ? 'bg-primary/5 dark:bg-blue-900/20'
                                                    : 'hover:bg-surface-container-low dark:hover:bg-slate-800/40'
                                                    } ${isAdded ? 'opacity-40 cursor-not-allowed' : ''} border-none`}
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className={`font-bold text-sm ${isActive ? 'text-primary dark:text-blue-400' : 'text-on-surface dark:text-slate-200'} truncate`}>
                                                                {fund.name}
                                                            </span>
                                                            {isHistory && (
                                                                <Clock className="w-3 h-3 text-on-surface-variant/40 dark:text-slate-600 shrink-0" />
                                                            )}
                                                            {isAdded && (
                                                                <span className="text-[9px] px-1.5 py-0.5 bg-surface-dim dark:bg-slate-800 text-on-surface-variant/60 dark:text-slate-500 rounded-sm font-bold uppercase tracking-wider">
                                                                    {t('addedLabel')}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <span className="font-mono text-[10px] text-on-surface-variant/50 dark:text-slate-500 bg-surface-container-low dark:bg-slate-950/40 px-1 rounded">
                                                                {fund.code}
                                                            </span>
                                                            {fund.type && (
                                                                <span className="text-[10px] text-on-surface-variant/40 dark:text-slate-600 font-medium">
                                                                    {fund.type}
                                                                </span>
                                                            )}
                                                            {fund.company && (
                                                                <span className="text-[10px] text-on-surface-variant/40 dark:text-slate-600 truncate max-w-[120px]">
                                                                    • {fund.company}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    {!isAdded && (
                                                        <div className={`mt-0.5 transition-transform duration-300 ${isActive ? 'translate-x-0 opacity-100' : 'translate-x-2 opacity-0'}`}>
                                                            <Plus className="w-4 h-4 text-primary dark:text-blue-400" />
                                                        </div>
                                                    )}
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>

                                {/* Footer Hint */}
                                <div className="px-4 py-2.5 bg-surface-container-low/50 dark:bg-slate-950/40 mt-auto sticky bottom-0 backdrop-blur-md">
                                    <p className="text-[9px] text-on-surface-variant/40 dark:text-slate-500 font-bold uppercase tracking-widest flex items-center gap-3">
                                        <span className="flex items-center gap-1">
                                            <kbd className="px-1 py-0.5 bg-surface-container-lowest dark:bg-slate-800 border border-outline-variant dark:border-slate-700 rounded text-[9px]">↑↓</kbd>
                                            {t('navNavigate')}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <kbd className="px-1 py-0.5 bg-surface-container-lowest dark:bg-slate-800 border border-outline-variant dark:border-slate-700 rounded text-[9px]">ENTER</kbd>
                                            {t('navSelect')}
                                        </span>
                                    </p>
                                </div>
                            </>
                        ) : query && !isLoading ? (
                            <div className="p-10 text-center flex-1 flex flex-col items-center justify-center">
                                <p className="text-sm text-on-surface-variant dark:text-slate-500 mb-4">{t('noResults')}</p>
                                <button
                                    onClick={() => {
                                        onAddFund(query.trim(), '');
                                        saveToHistory({ code: query.trim(), name: tApp('customAdd') });
                                        setQuery('');
                                        setIsOpen(false);
                                    }}
                                    className="px-5 py-2.5 bg-primary dark:bg-blue-600 text-on-primary rounded-lg text-xs font-bold hover:opacity-90 transition-all shadow-lg shadow-primary/20 dark:shadow-blue-500/10"
                                >
                                    {t('addDirectly', { query: query.trim() })}
                                </button>
                            </div>
                        ) : !query && searchHistory.length === 0 ? (
                            <div className="p-10 text-center text-on-surface-variant/20 dark:text-slate-800 flex flex-col items-center justify-center">
                                <Search className="w-10 h-10 mb-3" />
                                <p className="text-sm font-display font-bold text-on-surface-variant/40 dark:text-slate-600">{t('promptSearch')}</p>
                            </div>
                        ) : null}
                    </div>

                    {/* Loading Overlay */}
                    {isLoading && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface/20 dark:bg-slate-950/20 backdrop-blur-[2px] z-20">
                            <div className="animate-spin w-6 h-6 border-2 border-primary dark:border-blue-500 border-t-transparent rounded-full mb-3"></div>
                            {displayItems.length === 0 && <p className="text-[10px] text-primary dark:text-blue-400 font-bold uppercase tracking-widest animate-pulse">{t('scanningPool')}</p>}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
