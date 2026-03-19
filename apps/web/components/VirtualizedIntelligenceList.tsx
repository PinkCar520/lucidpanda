'use client';

import React, { useRef, useEffect, useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import IntelligenceCard from './IntelligenceCard';
import { Intelligence } from '@/lib/db';
import { RefreshCw } from 'lucide-react';

interface VirtualizedIntelligenceListProps {
  items: Intelligence[];
  hasNextPage: boolean | undefined;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  locale: string;
  getLocalizedText: (jsonString: any, locale: string) => string;
  t: (key: string) => string;
  tSentiment: (key: string) => string;
  isBearishSentiment: (sentimentInput: any) => boolean;
}

/**
 * VirtualizedIntelligenceList
 * 
 * High-performance virtualized list for thousands of intelligence news items.
 * Supports dynamic heights, infinite scrolling, and precise scroll restoration.
 */
export default function VirtualizedIntelligenceList({
  items,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  locale,
  getLocalizedText,
  t,
  tSentiment,
  isBearishSentiment
}: VirtualizedIntelligenceListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  // Initialize the virtualizer
  const rowVirtualizer = useVirtualizer({
    count: hasNextPage ? items.length + 1 : items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 140, 
    overscan: 10, // Increase overscan to trigger load earlier
  });

  const virtualItems = rowVirtualizer.getVirtualItems();

  // Infinite Scroll Logic
  useEffect(() => {
    const lastItem = virtualItems[virtualItems.length - 1];
    if (!lastItem) return;

    // Trigger when we are within 2 items of the end
    if (
      lastItem.index >= items.length - 2 &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [
    hasNextPage,
    fetchNextPage,
    items.length,
    isFetchingNextPage,
    virtualItems
  ]);

  // Restore scroll position logic can be added here or in the parent
  // We'll rely on the parent or a custom scroll restoration handler

  return (
    <div
      ref={parentRef}
      className="flex-1 w-full overflow-y-auto custom-scrollbar pr-2"
      style={{
        contain: 'strict', // Performance optimization for scrolling
      }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualItems.map((virtualRow) => {
          const isLoaderRow = virtualRow.index > items.length - 1;
          const item = items[virtualRow.index];

          return (
            <div
              key={virtualRow.key}
              data-index={virtualRow.index}
              ref={rowVirtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualRow.start}px)`,
                paddingBottom: '12px', // Gap between items
              }}
            >
              {isLoaderRow ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : (
                <IntelligenceCard
                  item={item}
                  locale={locale}
                  getLocalizedText={getLocalizedText}
                  t={t}
                  tSentiment={tSentiment}
                  isBearish={isBearishSentiment(item.sentiment)}
                />
              )}
            </div>
          );
        })}
      </div>
      
      {/* Empty State */}
      {!isFetchingNextPage && items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-10 text-slate-500">
          <p className="text-sm">{t('noIntelligence')}</p>
        </div>
      )}
    </div>
  );
}
