'use client';

import { useState, useEffect, useRef } from 'react';

/**
 * A hook that returns a className to trigger a highlight animation
 * whenever the provided value changes.
 */
export function useHighlight(value: unknown) {
    const [highlight, setHighlight] = useState(false);
    const isFirstMount = useRef(true);

    useEffect(() => {
        if (isFirstMount.current) {
            isFirstMount.current = false;
            return;
        }

        const timerId = setTimeout(() => {
            setHighlight(true);
        }, 0);
        const timer = setTimeout(() => setHighlight(false), 1500); // Match animation duration

        return () => {
            clearTimeout(timerId);
            clearTimeout(timer);
        };
    }, [value]);

    return highlight ? 'animate-highlight' : '';
}
