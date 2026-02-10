import React from 'react';

interface BadgeProps {
  variant?: 'neutral' | 'bullish' | 'bearish' | 'gold' | 'outline' | 'warning';
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = 'neutral', children, className = '' }: BadgeProps) {
  const variants = {
    neutral: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
    bullish: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/20 dark:text-rose-400 dark:border-rose-500/20", // Red Up
    bearish: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-400 dark:border-emerald-500/20", // Green Down
    gold: "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-500/20 dark:text-yellow-400 dark:border-yellow-500/20",
    outline: "bg-transparent border-slate-200 dark:border-slate-700 dark:text-slate-400",
    warning: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-400 dark:border-amber-500/20",
  };

  const baseClasses = "px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border transition-colors";
  const combinedClasses = `${baseClasses} ${variants[variant]} ${className}`.trim();

  return (
    <span className={combinedClasses}>
      {children}
    </span>
  );
}
