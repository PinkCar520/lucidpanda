'use client';

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

interface PaginatorProps {
    currentPage: number;
    totalPages: number;
    totalItems: number;
    itemsPerPage: number;
    onPageChange: (page: number) => void;
    onItemsPerPageChange?: (limit: number) => void;
    className?: string;
}

export default function Paginator({
    currentPage,
    totalPages,
    totalItems,
    itemsPerPage,
    onPageChange,
    onItemsPerPageChange,
    className = ''
}: PaginatorProps) {
    const startItem = (currentPage - 1) * itemsPerPage + 1;
    const endItem = Math.min(currentPage * itemsPerPage, totalItems);

    const handlePageChange = (page: number) => {
        if (page >= 1 && page <= totalPages) {
            onPageChange(page);
        }
    };

    const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        if (onItemsPerPageChange) {
            onItemsPerPageChange(Number(e.target.value));
        }
    };

    // 生成页码按钮
    const getPageNumbers = () => {
        const pages: (number | string)[] = [];
        const maxVisible = 7;

        if (totalPages <= maxVisible) {
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
        } else {
            pages.push(1);
            if (currentPage > 3) pages.push('...');

            const start = Math.max(2, currentPage - 1);
            const end = Math.min(totalPages - 1, currentPage + 1);
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }

            if (currentPage < totalPages - 2) pages.push('...');
            pages.push(totalPages);
        }

        return pages;
    };

    if (totalPages <= 1) return null;

    return (
        <div className={`flex items-center justify-between gap-4 ${className}`}>
            {/* 左侧：显示当前范围和每页条目选择 */}
            <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                <div>
                    显示 <span className="font-medium text-slate-900 dark:text-slate-200">{startItem}</span> 至{' '}
                    <span className="font-medium text-slate-900 dark:text-slate-200">{endItem}</span> 条，共{' '}
                    <span className="font-medium text-slate-900 dark:text-slate-200">{totalItems}</span> 条
                </div>

                {onItemsPerPageChange && (
                    <div className="flex items-center gap-2 border-l border-slate-200 dark:border-slate-800 pl-4 ml-2">
                        <select
                            value={itemsPerPage}
                            onChange={handleLimitChange}
                            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:focus:ring-emerald-500 cursor-pointer hover:border-blue-500 dark:hover:border-slate-600 transition-colors"
                        >
                            <option value={10}>10 条/页</option>
                            <option value={20}>20 条/页</option>
                            <option value={50}>50 条/页</option>
                            <option value={100}>100 条/页</option>
                        </select>
                    </div>
                )}
            </div>

            {/* 右侧：分页按钮 */}
            <div className="flex items-center gap-1">
                {/* 首页 */}
                <button
                    onClick={() => handlePageChange(1)}
                    disabled={currentPage === 1}
                    className="inline-flex items-center justify-center h-8 w-8 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-slate-500 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-blue-600 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="首页"
                >
                    <ChevronsLeft className="h-4 w-4" />
                </button>

                {/* 上一页 */}
                <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="inline-flex items-center justify-center h-8 w-8 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-slate-500 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-blue-600 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="上一页"
                >
                    <ChevronLeft className="h-4 w-4" />
                </button>

                {/* 页码 */}
                {getPageNumbers().map((page, index) => {
                    if (page === '...') {
                        return (
                            <span key={`ellipsis-${index}`} className="px-2 text-slate-400 dark:text-slate-500">
                                ...
                            </span>
                        );
                    }

                    return (
                        <button
                            key={page}
                            onClick={() => handlePageChange(page as number)}
                            className={`inline-flex items-center justify-center h-8 min-w-8 px-3 rounded-md text-sm font-medium transition-colors ${currentPage === page
                                ? 'bg-blue-600 dark:bg-emerald-600 text-white border border-blue-600 dark:border-emerald-600 hover:bg-blue-700 dark:hover:bg-emerald-700 shadow-sm'
                                : 'border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-blue-600 dark:hover:text-white'
                                }`}
                        >
                            {page}
                        </button>
                    );
                })}

                {/* 下一页 */}
                <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="inline-flex items-center justify-center h-8 w-8 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-slate-500 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-blue-600 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="下一页"
                >
                    <ChevronRight className="h-4 w-4" />
                </button>

                {/* 末页 */}
                <button
                    onClick={() => handlePageChange(totalPages)}
                    disabled={currentPage === totalPages}
                    className="inline-flex items-center justify-center h-8 w-8 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-slate-500 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-blue-600 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="末页"
                >
                    <ChevronsRight className="h-4 w-4" />
                </button>
            </div>
        </div>
    );
}
