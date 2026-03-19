'use client';

import { useEffect, useRef, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { throttle } from 'lodash';

/**
 * useScrollPersistence
 * 
 * A professional hook to persist and restore scroll positions of specific containers.
 * Uses sessionStorage to ensure persistence across internal navigation but clean up on tab close.
 */
export function useScrollPersistence(key: string, isDataReady: boolean = true) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const storageKey = `scroll-pos:${pathname}:${key}`;

  // 1. Save scroll position (throttled for performance)
  const handleScroll = useCallback(
    throttle(() => {
      if (scrollRef.current) {
        sessionStorage.setItem(storageKey, scrollRef.current.scrollTop.toString());
      }
    }, 150),
    [storageKey]
  );

  // 2. Restore scroll position
  const restoreScroll = useCallback(() => {
    const savedPos = sessionStorage.getItem(storageKey);
    if (savedPos && scrollRef.current && isDataReady) {
      const targetPos = parseInt(savedPos, 10);
      
      // We use requestAnimationFrame to ensure the DOM has updated and layout is calculated
      // We try for a few frames to handle potential micro-tasks/layout shifts
      let frames = 0;
      const attemptRestore = () => {
        if (scrollRef.current && scrollRef.current.scrollTop !== targetPos && frames < 5) {
          scrollRef.current.scrollTop = targetPos;
          frames++;
          requestAnimationFrame(attemptRestore);
        }
      };
      
      requestAnimationFrame(attemptRestore);
    }
  }, [storageKey, isDataReady]);

  // Set up listeners
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => {
      container.removeEventListener('scroll', handleScroll);
      handleScroll.cancel(); // Clean up throttle
    };
  }, [handleScroll]);

  // Trigger restoration when data is ready
  useEffect(() => {
    if (isDataReady) {
      restoreScroll();
    }
  }, [isDataReady, restoreScroll]);

  return scrollRef;
}
