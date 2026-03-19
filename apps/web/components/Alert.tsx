'use client';

import React from 'react';
import { AlertCircle, CheckCircle, Info, AlertTriangle, X } from 'lucide-react';

type AlertVariant = 'error' | 'success' | 'warning' | 'info';

interface AlertProps {
    variant: AlertVariant;
    children: React.ReactNode;
    onClose?: () => void;
    className?: string;
}

export function Alert({ variant, children, onClose, className = '' }: AlertProps) {
    const icons = {
        error: <AlertCircle className="w-5 h-5" />,
        success: <CheckCircle className="w-5 h-5" />,
        warning: <AlertTriangle className="w-5 h-5" />,
        info: <Info className="w-5 h-5" />
    };

    const styles = {
        error: 'bg-red-500/10 border-red-500/50 text-red-400',
        success: 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400',
        warning: 'bg-amber-500/10 border-amber-500/50 text-amber-400',
        info: 'bg-blue-500/10 border-blue-500/50 text-blue-400'
    };

    return (
        <div
            className={`
        flex items-start gap-3 p-4 rounded-lg border backdrop-blur-sm
        ${styles[variant]} ${className}
      `}
            role="alert"
        >
            <div className="flex-shrink-0 mt-0.5">{icons[variant]}</div>
            <div className="flex-1 text-sm">{children}</div>
            {onClose && (
                <button
                    onClick={onClose}
                    className="flex-shrink-0 hover:opacity-70 transition-opacity"
                    aria-label="Close alert"
                >
                    <X className="w-4 h-4" />
                </button>
            )}
        </div>
    );
}
