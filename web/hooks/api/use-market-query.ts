import { useQuery } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { marketService } from '@/lib/services/market-service';

/**
 * Hook to fetch market data with deduplication and caching
 */
export function useMarketQuery(symbol: string, range: string, interval: string) {
  const { data: session } = useSession();
  
  return useQuery({
    queryKey: ['market', symbol, range, interval],
    queryFn: () => marketService.getMarketData(symbol, range, interval, session),
    enabled: !!session && !!symbol,
    staleTime: 1000 * 60, // Consider market data fresh for 1 minute
    gcTime: 1000 * 60 * 5, // Keep in cache for 5 minutes
    retry: (failureCount, error: any) => {
      // Don't retry immediately if rate limited
      if (error.message === 'RATE_LIMIT_EXCEEDED') return false;
      return failureCount < 2;
    }
  });
}
