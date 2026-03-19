'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
    id: string;
    type: ToastType;
    message: string;
    duration?: number;
}

interface ToastContextType {
    toasts: Toast[];
    showToast: (type: ToastType, message: string, duration?: number) => void;
    removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);

    const showToast = useCallback((type: ToastType, message: string, duration = 5000) => {
        const id = Math.random().toString(36).substring(7);
        const toast: Toast = { id, type, message, duration };

        setToasts((prev) => [...prev, toast]);

        if (duration > 0) {
            setTimeout(() => {
                removeToast(id);
            }, duration);
        }
    }, [removeToast]);

    return (
        <ToastContext.Provider value={{ toasts, showToast, removeToast }}>
            {children}
            <ToastContainer toasts={toasts} onRemove={removeToast} />
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
}

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
    return (
        <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
            {toasts.map((toast) => (
                <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
            ))}
        </div>
    );
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
    const icons = {
        success: <CheckCircle className="w-5 h-5" />,
        error: <AlertCircle className="w-5 h-5" />,
        warning: <AlertTriangle className="w-5 h-5" />,
        info: <Info className="w-5 h-5" />
    };

    const styles = {
        success: 'bg-emerald-500/90 text-white border-emerald-600',
        error: 'bg-red-500/90 text-white border-red-600',
        warning: 'bg-amber-500/90 text-white border-amber-600',
        info: 'bg-blue-500/90 text-white border-blue-600'
    };

    return (
        <div
            className={`
        flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-sm
        shadow-lg animate-in slide-in-from-right-full duration-300
        pointer-events-auto min-w-[300px] max-w-[500px]
        ${styles[toast.type]}
      `}
        >
            <div className="flex-shrink-0">{icons[toast.type]}</div>
            <p className="flex-1 text-sm font-medium">{toast.message}</p>
            <button
                onClick={() => onRemove(toast.id)}
                className="flex-shrink-0 hover:opacity-70 transition-opacity"
                aria-label="Close"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
}

// Helper functions for easier usage
export const toast = {
    success: (message: string, duration?: number) => {
        // This will be replaced by the actual context function
        console.log('[Toast] Success:', message);
    },
    error: (message: string, duration?: number) => {
        console.error('[Toast] Error:', message);
    },
    warning: (message: string, duration?: number) => {
        console.warn('[Toast] Warning:', message);
    },
    info: (message: string, duration?: number) => {
        console.info('[Toast] Info:', message);
    }
};

export default function Toast({ message, type, onClose }: { message: string, type: 'success' | 'error' | 'info' | 'warning', onClose: () => void }) {
    const icons = {
        success: <CheckCircle className="w-5 h-5" />,
        error: <AlertCircle className="w-5 h-5" />,
        warning: <AlertTriangle className="w-5 h-5" />,
        info: <Info className="w-5 h-5" />
    };

    const styles = {
        success: 'bg-emerald-500/90 text-white border-emerald-600',
        error: 'bg-red-500/90 text-white border-red-600',
        warning: 'bg-amber-500/90 text-white border-amber-600',
        info: 'bg-blue-500/90 text-white border-blue-600'
    };

    return (
        <div className="fixed top-4 right-4 z-[9999] animate-in slide-in-from-right-full">
            <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-sm shadow-lg min-w-[300px] ${styles[type]}`}>
                <div className="flex-shrink-0">{icons[type]}</div>
                <p className="flex-1 text-sm font-medium">{message}</p>
                <button onClick={onClose} className="flex-shrink-0 hover:opacity-70">
                    <X className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}
