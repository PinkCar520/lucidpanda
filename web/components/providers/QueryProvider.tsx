'use client';

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { persistQueryClient } from '@tanstack/react-query-persist-client';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';

/**
 * Global Query Provider
 * 
 * Configures the QueryClient with professional defaults and persistence.
 */
export default function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => {
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          // In a financial dashboard, data becomes stale relatively quickly
          // but we want a smooth transition when switching between pages.
          staleTime: 1000 * 30, // 30 seconds
          gcTime: 1000 * 60 * 60 * 24, // Keep in cache for 24 hours
          
          // Retry logic: 3 retries with exponential backoff
          retry: 2,
          retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
          
          // Refetch on focus is useful for real-time market data
          refetchOnWindowFocus: true,
          
          // Smooth loading experience: show old data while fetching new one
          placeholderData: (previousData: any) => previousData,
        },
      },
    });

    // Configure persistence (Syncs cache with localStorage)
    if (typeof window !== 'undefined') {
      const persister = createSyncStoragePersister({
        storage: window.localStorage,
        key: 'ALPHASIGNAL_QUERY_CACHE',
      });

      persistQueryClient({
        queryClient: client,
        persister,
        maxAge: 1000 * 60 * 60 * 24, // 24 hours
      });
    }

    return client;
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
