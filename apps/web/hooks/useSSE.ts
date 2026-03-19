/**
 * Custom React Hook for Server-Sent Events (SSE)
 * 
 * This hook manages the SSE connection lifecycle and provides
 * real-time updates from the backend.
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { Intelligence } from '@/lib/db';

interface SSEMessage {
    type: 'connected' | 'intelligence_update' | 'error';
    message?: string;
    data?: Intelligence[];
    count?: number;
    latest_id?: number;
}

interface UseSSEOptions {
    url: string;
    onMessage?: (data: Intelligence[]) => void;
    onError?: (error: Event) => void;
    enabled?: boolean;
}

export function useSSE({ url, onMessage, onError, enabled = true }: UseSSEOptions) {
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (!enabled) return;

        let isMounted = true;

        const connect = () => {
            try {
                console.log('[SSE] Connecting to', url);
                const eventSource = new EventSource(url);
                eventSourceRef.current = eventSource;

                eventSource.onopen = () => {
                    if (isMounted) {
                        console.log('[SSE] Connection established');
                        setIsConnected(true);
                        setError(null);
                    }
                };

                eventSource.onmessage = (event) => {
                    try {
                        const message: SSEMessage = JSON.parse(event.data);

                        if (message.type === 'intelligence_update' && message.data) {
                            console.log(`[SSE] Received ${message.count} new items`);
                            onMessage?.(message.data);
                        } else if (message.type === 'connected') {
                            console.log('[SSE]', message.message);
                        } else if (message.type === 'error') {
                            console.error('[SSE] Server error:', message.message);
                            setError(message.message || 'Unknown error');
                        }
                    } catch (err) {
                        console.error('[SSE] Failed to parse message:', err);
                    }
                };

                eventSource.onerror = (err) => {
                    console.error('[SSE] Connection error:', err);
                    setIsConnected(false);
                    onError?.(err);

                    // Close the connection
                    eventSource.close();

                    // Attempt to reconnect after 5 seconds
                    if (isMounted) {
                        setError('Connection lost. Reconnecting...');
                        reconnectTimeoutRef.current = setTimeout(() => {
                            if (isMounted) {
                                console.log('[SSE] Attempting to reconnect...');
                                connect();
                            }
                        }, 5000);
                    }
                };
            } catch (err) {
                console.error('[SSE] Failed to create EventSource:', err);
                setError('Failed to establish SSE connection');
            }
        };

        connect();

        // Cleanup function
        return () => {
            isMounted = false;

            if (eventSourceRef.current) {
                console.log('[SSE] Closing connection');
                eventSourceRef.current.close();
                eventSourceRef.current = null;
            }

            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }

            setIsConnected(false);
        };
    }, [url, enabled, onMessage, onError]);

    return {
        isConnected,
        error,
        disconnect: () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
                eventSourceRef.current = null;
                setIsConnected(false);
            }
        }
    };
}
