'use client';

import React, { useRef, useEffect, useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Intelligence } from '@/lib/db';
import { RefreshCw } from 'lucide-react';
import { useScrollPersistence } from '@/hooks/use-scroll-persistence';

interface VirtualizedStrategyTableProps {
  items: Intelligence[];
  hasNextPage: boolean | undefined;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  locale: string;
  getLocalizedText: (jsonString: any, locale: string) => string;
  tTable: (key: string) => string;
}

/**
 * VirtualizedStrategyTable
 * 
 * A professional, high-performance infinite scrolling table for strategy data.
 * Replaces traditional pagination with a seamless vertical log experience.
 */
export default function VirtualizedStrategyTable({
  items,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  locale,
  getLocalizedText,
  tTable
}: VirtualizedStrategyTableProps) {
  const parentRef = useScrollPersistence('strategy-matrix-table', items.length > 0);

  // Column Flex Config (Matching professional terminal layout)
  const colTime = "flex-[0_0_150px] px-4 py-3";
  const colContext = "flex-1 px-4 py-3 min-w-[300px]";
  const colStrategy = "flex-[0_0_250px] px-4 py-3";
  const colGold = "flex-[0_0_100px] px-4 py-3 text-right font-mono";

  const rowVirtualizer = useVirtualizer({
    count: hasNextPage ? items.length + 1 : items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
    overscan: 10,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();

  // Infinite Scroll Trigger
  useEffect(() => {
    const lastItem = virtualItems[virtualItems.length - 1];
    if (!lastItem) return;

    if (
      lastItem.index >= items.length - 5 && // Early trigger (5 items before end)
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [hasNextPage, fetchNextPage, items.length, isFetchingNextPage, virtualItems]);

  return (
    <div className="flex flex-col h-[600px] border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden bg-white dark:bg-slate-900/20">
      {/* Sticky Header */}
      <div className="flex bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 z-10">
        <div className={colTime}>{tTable('time')}</div>
        <div className={colContext}>{tTable('context')}</div>
        <div className={colStrategy}>{tTable('strategy')}</div>
        <div className={colGold}>{tTable('goldRef')}</div>
      </div>

      {/* Virtualized Body */}
      <div
        ref={parentRef}
        className="flex-1 overflow-y-auto custom-scrollbar"
        style={{ contain: 'strict' }}
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
                className={`flex border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors ${
                    virtualRow.index % 2 === 0 ? 'bg-white dark:bg-transparent' : 'bg-slate-50/30 dark:bg-slate-800/10'
                }`}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {isLoaderRow ? (
                  <div className="flex-1 flex items-center justify-center py-4">
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-400" />
                  </div>
                ) : (
                  <>
                    {/* Time Column */}
                    <div className={`${colTime} text-[11px] font-mono text-slate-400`}>
                        {(() => {
                            const date = new Date(item.timestamp);
                            return `${date.getUTCFullYear()}/${String(date.getUTCMonth() + 1).padStart(2, '0')}/${String(date.getUTCDate()).padStart(2, '0')} ${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}`;
                        })()}
                    </div>
                    
                    {/* Context Column */}
                    <div className={`${colContext} text-xs md:text-sm text-slate-700 dark:text-slate-300`}>
                      {getLocalizedText(item.summary, locale)}
                    </div>
                    
                    {/* Strategy Column */}
                    <div className={`${colStrategy} text-xs font-mono text-blue-600 dark:text-emerald-400`}>
                      {getLocalizedText(item.actionable_advice, locale)}
                    </div>
                    
                    {/* Gold Ref Column */}
                    <div className={`${colGold} text-slate-500`}>
                      ${item.gold_price_snapshot?.toFixed(1) || '-'}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
