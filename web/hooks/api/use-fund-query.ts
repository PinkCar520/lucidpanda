import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { fundService, WatchlistItem } from '@/lib/services/fund-service';
import { fundKeys } from '@/lib/query-keys';

/**
 * Hook to fetch and manage watchlist
 */
export function useWatchlistQuery() {
  const { data: session } = useSession();
  
  return useQuery({
    queryKey: fundKeys.watchlist(session?.user?.id),
    queryFn: () => fundService.getWatchlist(session),
    enabled: !!session,
    staleTime: 1000 * 60 * 5, // Watchlist names don't change often
  });
}

/**
 * Hook to fetch batch valuation for all funds in watchlist
 */
export function useBatchValuationQuery(codes: string[]) {
  const { data: session } = useSession();
  
  return useQuery({
    queryKey: fundKeys.batchValuation(codes),
    queryFn: () => fundService.getBatchValuation(codes, session),
    enabled: !!session && codes.length > 0,
    refetchInterval: 1000 * 60, // Refresh every minute for market data
  });
}

/**
 * Hook to fetch detailed valuation for a specific fund
 */
export function useFundValuationQuery(code: string) {
  const { data: session } = useSession();
  
  return useQuery({
    queryKey: fundKeys.valuation(code),
    queryFn: () => fundService.getFundValuation(code, session),
    enabled: !!session && !!code,
    refetchInterval: 1000 * 60,
  });
}

/**
 * Hook to fetch history for a specific fund
 */
export function useFundHistoryQuery(code: string) {
  const { data: session } = useSession();
  
  return useQuery({
    queryKey: fundKeys.history(code),
    queryFn: () => fundService.getFundHistory(code, session),
    enabled: !!session && !!code,
    staleTime: 1000 * 60 * 60, // History is static for the day
  });
}

/**
 * Mutation hooks for watchlist operations
 */
export function useWatchlistMutations() {
  const { data: session } = useSession();
  const queryClient = useQueryClient();
  
  const addMutation = useMutation({
    mutationFn: ({ code, name }: { code: string; name: string }) => 
      fundService.addToWatchlist(code, name, session),
    onSuccess: () => {
      // Invalidate watchlist to trigger refetch
      queryClient.invalidateQueries({ queryKey: fundKeys.watchlists() });
    },
  });
  
  const removeMutation = useMutation({
    mutationFn: (code: string) => fundService.removeFromWatchlist(code, session),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fundKeys.watchlists() });
    },
  });
  
  return {
    addFund: addMutation,
    removeFund: removeMutation,
  };
}
