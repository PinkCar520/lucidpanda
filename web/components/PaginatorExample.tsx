/**
 * 战术策略矩阵分页使用示例
 * 
 * 在您的组件中集成分页器的步骤：
 */

'use client';

import { useState, useEffect } from 'react';
import Paginator from '@/components/Paginator';

export default function TacticalMatrixExample() {
    const [intelligence, setIntelligence] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [totalItems, setTotalItems] = useState(0);
    const [loading, setLoading] = useState(false);

    const ITEMS_PER_PAGE = 20; // 每页显示20条

    // 获取数据
    const fetchIntelligence = async (page: number) => {
        setLoading(true);
        try {
            const offset = (page - 1) * ITEMS_PER_PAGE;
            const response = await fetch(
                `/api/v1/web/intelligence/full?limit=${ITEMS_PER_PAGE}&offset=${offset}`
            );
            const data = await response.json();

            setIntelligence(data.data);
            setTotalPages(data.total_pages);
            setTotalItems(data.total);
            setCurrentPage(data.page);
        } catch (error) {
            console.error('Failed to fetch intelligence:', error);
        } finally {
            setLoading(false);
        }
    };

    // 页面变化时重新获取数据
    useEffect(() => {
        fetchIntelligence(currentPage);
    }, [currentPage]);

    // 处理页码变化
    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        // 可选：滚动到顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    return (
        <div className="space-y-4">
            {/* 战术策略矩阵内容 */}
            <div className="grid gap-4">
                {loading ? (
                    <div className="text-center py-8">加载中...</div>
                ) : (
                    intelligence.map((item: any) => (
                        <div key={item.id} className="border rounded-lg p-4">
                            {/* 您的情报卡片内容 */}
                            <h3>{item.content}</h3>
                            <p>紧急度: {item.urgency_score}</p>
                        </div>
                    ))
                )}
            </div>

            {/* 分页器 */}
            <Paginator
                currentPage={currentPage}
                totalPages={totalPages}
                totalItems={totalItems}
                itemsPerPage={ITEMS_PER_PAGE}
                onPageChange={handlePageChange}
                className="mt-6"
            />
        </div>
    );
}

/**
 * 集成到现有组件的步骤：
 * 
 * 1. 在您的战术策略矩阵组件中添加状态：
 *    const [currentPage, setCurrentPage] = useState(1);
 *    const [paginationMeta, setPaginationMeta] = useState({ total: 0, total_pages: 0 });
 * 
 * 2. 修改数据获取逻辑：
 *    const fetchData = async (page: number) => {
 *      const offset = (page - 1) * ITEMS_PER_PAGE;
 *      const res = await fetch(`/api/v1/web/intelligence/full?limit=${ITEMS_PER_PAGE}&offset=${offset}`);
 *      const data = await res.json();
 *      setPaginationMeta({ total: data.total, total_pages: data.total_pages });
 *    };
 * 
 * 3. 在组件底部添加分页器：
 *    <Paginator
 *      currentPage={currentPage}
 *      totalPages={paginationMeta.total_pages}
 *      totalItems={paginationMeta.total}
 *      itemsPerPage={ITEMS_PER_PAGE}
 *      onPageChange={setCurrentPage}
 *    />
 */
