'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, X, TrendingUp, Clock, Plus } from 'lucide-react';
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
        <div className="relative" ref={dropdownRef}>
            {/* Search Input */}
            <div className="relative">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={handleInputChange}
                    onFocus={() => setIsOpen(true)}
                    onKeyDown={handleKeyDown}
                    placeholder={t('addPlaceholder')}
                    className="w-full bg-white border border-slate-200 rounded-md py-2 pl-9 pr-8 text-sm focus:border-blue-600 outline-none transition-colors text-slate-900 placeholder-slate-400"
                />
                {query && (
                    <button
                        onClick={() => {
                            setQuery('');
                            inputRef.current?.focus();
                        }}
                        className="absolute right-2 top-2.5 text-slate-400 hover:text-slate-600"
                    >
                        <X className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Dropdown */}
            {isOpen && (
                <div className="absolute z-50 w-full mt-2 bg-white border border-slate-200 rounded-md shadow-2xl max-h-80 overflow-y-auto flex flex-col min-h-[100px]">
                    {/* Content Layer */}
                    <div className={`flex-1 flex flex-col transition-opacity duration-200 ${isLoading ? 'opacity-40 pointer-events-none' : 'opacity-100'}`}>
                        {displayItems.length > 0 ? (
                            <>
                                {/* Header */}
                                <div className="px-3 py-2 border-b border-slate-100 shrink-0 bg-white sticky top-0 z-10">
                                    <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wider">
                                        {query ? (
                                            <>
                                                <Search className="w-3 3" />
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
                                                        className="text-[10px] text-blue-600 hover:text-blue-700 normal-case tracking-normal"
                                                    >
                                                        {t('clearHistory')}
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Results List */}
                                <div className="py-1">
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
                                                className={`w-full px-3 py-2 text-left transition-colors ${isActive
                                                    ? 'bg-blue-50 border-l-2 border-blue-600'
                                                    : 'hover:bg-slate-50 border-l-2 border-transparent'
                                                    } ${isAdded ? 'opacity-50 cursor-not-allowed' : ''}`}
                                            >
                                                <div className="flex items-start justify-between gap-2">
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-bold text-sm text-slate-800 truncate">
                                                                {fund.name}
                                                            </span>
                                                            {isHistory && (
                                                                <Clock className="w-3 h-3 text-slate-500 shrink-0" />
                                                            )}
                                                            {isAdded && (
                                                                <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-400 rounded-full font-mono border border-slate-200">
                                                                    {t('addedLabel')}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2 mt-0.5">
                                                            <span className="font-mono text-xs text-slate-500">
                                                                {fund.code}
                                                            </span>
                                                            {fund.type && (
                                                                <>
                                                                    <span className="text-slate-700">•</span>
                                                                    <span className="text-xs text-slate-600">
                                                                        {fund.type}
                                                                    </span>
                                                                </>
                                                            )}
                                                            {fund.company && (
                                                                <>
                                                                    <span className="text-slate-700">•</span>
                                                                    <span className="text-xs text-slate-600 truncate">
                                                                        {fund.company}
                                                                    </span>
                                                                </>
                                                            )}
                                                        </div>
                                                    </div>
                                                    {!isAdded && (
                                                        <Plus className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                                                    )}
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>

                                {/* Footer Hint */}
                                <div className="px-3 py-2 border-t border-slate-100 bg-slate-50 mt-auto sticky bottom-0">
                                    <p className="text-xs text-slate-500">
                                        <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] text-slate-400">↑</kbd>
                                        <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] ml-1 text-slate-400">↓</kbd>
                                        {' '}{t('navNavigate')} {' '}
                                        <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] text-slate-400">Enter</kbd>
                                        {' '}{t('navSelect')} {' '}
                                        <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] text-slate-400">Esc</kbd>
                                        {' '}{t('navClose')}
                                    </p>
                                </div>
                            </>
                        ) : query && !isLoading ? (
                            <div className="p-8 text-center flex-1 flex flex-col items-center justify-center">
                                <p className="text-sm text-slate-500 mb-3">{t('noResults')}</p>
                                <button
                                    onClick={() => {
                                        onAddFund(query.trim(), '');
                                        saveToHistory({ code: query.trim(), name: tApp('customAdd') });
                                        setQuery('');
                                        setIsOpen(false);
                                    }}
                                    className="px-4 py-2 bg-blue-50 text-blue-600 rounded-md text-xs font-medium hover:bg-blue-100 transition-colors border border-blue-100"
                                >
                                    {t('addDirectly', { query: query.trim() })}
                                </button>
                            </div>
                        ) : !query && searchHistory.length === 0 ? (
                            <div className="p-8 text-center text-slate-400">
                                <Search className="w-8 h-8 mx-auto mb-2 opacity-20" />
                                <p className="text-sm text-slate-400">{t('promptSearch')}</p>
                            </div>
                        ) : null}
                    </div>

                    {/* Loading Overlay - Prevents Flickering by overlaying instead of replacing */}
                    {isLoading && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/10 backdrop-blur-[1px] z-20">
                            <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mb-2"></div>
                            {displayItems.length === 0 && <p className="text-xs text-slate-500 animate-pulse">{t('scanningPool')}</p>}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
