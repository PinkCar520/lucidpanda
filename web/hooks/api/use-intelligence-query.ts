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
  const limit = 50;
  
  return useInfiniteQuery({
    queryKey: intelligenceKeys.infinite(filters),
    queryFn: async ({ pageParam = 0 }) => {
      // Use V1 Web BFF for full JSONB data
      const res = await authenticatedFetch(
        `/api/v1/web/intelligence/full?limit=${limit}&offset=${pageParam}`, 
        session
      );
      if (!res.ok) throw new Error('Failed to fetch intelligence');
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
    staleTime: 1000 * 60 * 2,
  });
}
