import { useInfiniteQuery } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { authenticatedFetch } from '@/lib/api-client';
import { intelligenceKeys } from '@/lib/query-keys';

/**
 * Hook for fetching strategy matrix data with infinite scrolling
 */
export function useStrategyInfiniteQuery() {
  const { data: session } = useSession();
  const limit = 50; // Larger limit for table view to ensure smooth scrolling
  
  return useInfiniteQuery({
    queryKey: ['intelligence', 'strategy-matrix', 'infinite'],
    queryFn: async ({ pageParam = 0 }) => {
      const res = await authenticatedFetch(
        `/api/v1/web/intelligence/full?limit=${limit}&offset=${pageParam}`, 
        session
      );
      if (!res.ok) throw new Error('Failed to fetch strategy matrix');
      return res.json();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      // API response: { data, total, page, limit, total_pages }
      const currentOffset = lastPage.page > 0 ? (lastPage.page - 1) * limit : 0;
      const nextOffset = currentOffset + (lastPage.data?.length || 0);
      
      if (nextOffset < lastPage.total) {
        return nextOffset;
      }
      return undefined;
    },
    enabled: !!session,
    staleTime: 1000 * 60 * 5, // Strategy data can be cached longer
  });
}
