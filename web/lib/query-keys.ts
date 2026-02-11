/**
 * TanStack Query Key Factory
 * 
 * This centralized factory ensures consistent cache keys across the application.
 * It follows the pattern: [scope, type, ...params]
 */

export const fundKeys = {
  all: ['funds'] as const,
  
  // Watchlist related keys
  watchlists: () => [...fundKeys.all, 'watchlist'] as const,
  watchlist: (userId?: string) => [...fundKeys.watchlists(), { userId }] as const,
  
  // Valuation/Details related keys
  details: () => [...fundKeys.all, 'detail'] as const,
  detail: (code: string) => [...fundKeys.details(), code] as const,
  valuation: (code: string) => [...fundKeys.detail(code), 'valuation'] as const,
  history: (code: string) => [...fundKeys.detail(code), 'history'] as const,
  
  // Batch operations
  batchValuation: (codes: string[]) => [...fundKeys.all, 'batch-valuation', { codes: codes.sort() }] as const,
};

export const intelligenceKeys = {
  all: ['intelligence'] as const,
  lists: () => [...intelligenceKeys.all, 'list'] as const,
  list: (filters: any) => [...intelligenceKeys.lists(), { filters }] as const,
  infinite: (filters: any) => [...intelligenceKeys.list(filters), 'infinite'] as const,
};

export const backtestKeys = {
  all: ['backtest'] as const,
  results: () => [...backtestKeys.all, 'results'] as const,
  result: (params: any) => [...backtestKeys.results(), { params }] as const,
};
