import { useInfiniteQuery } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { authenticatedFetch } from '@/lib/api-client';
import { intelligenceKeys } from '@/lib/query-keys';

/**
 * Hook for fetching intelligence news with infinite scrolling
 * Handles thousands of items efficiently with TanStack Query's pagination
 */
export function useIntelligenceInfiniteQuery(filters: any = {}) {
  const { data: session } = useSession();
  
  return useInfiniteQuery({
    queryKey: intelligenceKeys.infinite(filters),
    queryFn: async ({ pageParam = 1 }) => {
      const res = await authenticatedFetch(
        `/api/intelligence?page=${pageParam}&limit=20`, 
        session
      );
      if (!res.ok) throw new Error('Failed to fetch intelligence');
      return res.json();
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      // Assuming API returns pagination info
      if (lastPage.pagination && lastPage.pagination.page < lastPage.pagination.totalPages) {
        return lastPage.pagination.page + 1;
      }
      return undefined;
    },
    enabled: !!session,
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}
