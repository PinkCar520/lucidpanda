import React from 'react';

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  action?: React.ReactNode;
  contentClassName?: string;
}

export function Card({ className = '', title, action, children, contentClassName, ...props }: CardProps) {
  const baseClasses = "rounded-xl overflow-hidden shadow-sm border transition-all duration-300 hover:shadow-md";
  const themeClasses = "bg-white border-slate-200 dark:bg-slate-900/40 dark:border-slate-800/50 dark:backdrop-blur-md";
  const combinedClasses = `${baseClasses} ${themeClasses} ${className}`.trim();

  return (
    <div
      className={combinedClasses}
      {...props}
    >
      {(title || action) && (
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-3 md:gap-0 bg-slate-50/50 dark:bg-slate-900/50">
          {title && <div className="font-semibold text-slate-800 dark:text-slate-200 tracking-tight">{title}</div>}
          {action && <div className="w-full md:w-auto flex justify-end">{action}</div>}
        </div>
      )}
      <div className={contentClassName || "p-5"}>
        {children}
      </div>
    </div>
  );
}
