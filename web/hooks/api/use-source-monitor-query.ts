import { useQuery } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { authenticatedFetch } from '@/lib/api-client';
import { sourceMonitorKeys } from '@/lib/query-keys';

export interface SourceDashboardData {
  window_days: number;
  generated_at: string;
  overview: {
    active_sources: number;
    total_signals: number;
    overall_accuracy_pct: number | null;
  };
  leaderboard: Array<{
    source_name: string;
    total_signals: number;
    hits: number;
    accuracy_pct: number | null;
    accuracy_lower_bound: number | null;
    last_seen: string;
  }>;
  trend: Array<{
    day: string;
    source_name: string;
    total_signals: number;
    accuracy_pct: number | null;
  }>;
}

export function useSourceMonitorQuery(days: number = 14, limit: number = 15) {
  const { data: session } = useSession();

  return useQuery({
    queryKey: sourceMonitorKeys.dashboard(days, limit),
    queryFn: async () => {
      const res = await authenticatedFetch(
        `/api/v1/web/sources/dashboard?days=${days}&limit=${limit}`,
        session
      );
      if (!res.ok) throw new Error('Failed to fetch source monitor data');
      return res.json() as Promise<SourceDashboardData>;
    },
    enabled: !!session,
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  });
}
