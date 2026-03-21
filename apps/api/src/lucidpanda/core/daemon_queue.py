"""
LucidPanda 内存队列模块
========================
基于 asyncio.Queue 的内存队列，用于解耦 collector 和 worker
"""

import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class IntelligenceItem:
    """
    情报项（内存队列中传递）
    
    特性:
    - 包含采集时的市场快照
    - 包含 AI 分析结果
    - 自动填充时间戳
    """
    
    # 基础信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    url: str = ""
    title: str = ""
    content: str = ""
    
    # 分类信息
    category: str = ""
    timestamp: str = ""
    
    # 市场快照（采集时注入）
    gold_price_snapshot: Optional[float] = None
    dxy_snapshot: Optional[float] = None
    us10y_snapshot: Optional[float] = None
    gvz_snapshot: Optional[float] = None
    oil_price_snapshot: Optional[float] = None
    
    # 分析结果（Worker 填充）
    analysis_result: Optional[Dict[str, Any]] = None
    analysis_completed_at: Optional[str] = None
    
    # 元数据
    collected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return asdict(self)
    
    @classmethod
    def from_raw(cls, raw: Dict[str, Any], **kwargs) -> 'IntelligenceItem':
        """
        从原始数据创建情报项
        
        Args:
            raw: 原始采集数据
            **kwargs: 额外字段（如市场快照）
        
        Returns:
            IntelligenceItem 实例
        """
        return cls(
            id=raw.get('id', str(uuid.uuid4())),
            source=raw.get('source', ''),
            url=raw.get('url', ''),
            title=raw.get('title', ''),
            content=raw.get('content', ''),
            category=raw.get('category', ''),
            timestamp=raw.get('timestamp', ''),
            gold_price_snapshot=kwargs.get('gold_price_snapshot'),
            dxy_snapshot=kwargs.get('dxy_snapshot'),
            us10y_snapshot=kwargs.get('us10y_snapshot'),
            gvz_snapshot=kwargs.get('gvz_snapshot'),
            oil_price_snapshot=kwargs.get('oil_price_snapshot'),
        )


class IntelligenceQueue:
    """
    智能情报内存队列
    
    特性:
    - 基于 asyncio.Queue（原生异步支持）
    - 有界队列（防止内存爆炸）
    - 支持优雅关闭
    - 统计监控
    """
    
    def __init__(self, maxsize: int = 100):
        """
        Args:
            maxsize: 队列最大容量（默认 100 条）
        """
        self.queue = asyncio.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self.closed = False
        
        # 统计信息
        self.stats = {
            'enqueued_count': 0,
            'dequeued_count': 0,
            'dropped_count': 0,
            'current_size': 0,
            'peak_size': 0,
        }
    
    async def put(self, item: IntelligenceItem, block: bool = True) -> bool:
        """
        入队
        
        Args:
            item: 情报项
            block: 队列满时是否阻塞
        
        Returns:
            True=成功，False=队列满且 block=False
        """
        if self.closed:
            raise RuntimeError("队列已关闭")
        
        try:
            if block:
                await self.queue.put(item)
            else:
                self.queue.put_nowait(item)
            
            self.stats['enqueued_count'] += 1
            self.stats['current_size'] = self.queue.qsize()
            
            # 更新峰值
            if self.stats['current_size'] > self.stats['peak_size']:
                self.stats['peak_size'] = self.stats['current_size']
            
            return True
            
        except asyncio.QueueFull:
            self.stats['dropped_count'] += 1
            return False
    
    async def get(self, timeout: Optional[float] = None) -> Optional[IntelligenceItem]:
        """
        出队
        
        Args:
            timeout: 超时时间（秒），None=无限等待
        
        Returns:
            情报项，超时返回 None
        """
        try:
            if timeout:
                item = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=timeout
                )
            else:
                item = await self.queue.get()
            
            self.stats['dequeued_count'] += 1
            self.stats['current_size'] = self.queue.qsize()
            self.queue.task_done()
            return item
            
        except asyncio.TimeoutError:
            return None
    
    async def close(self):
        """关闭队列（停止接收新项）"""
        self.closed = True
    
    async def join(self):
        """等待队列清空"""
        await self.queue.join()
    
    def qsize(self) -> int:
        """当前队列大小"""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """队列是否为空"""
        return self.queue.empty()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self.stats,
            'is_closed': self.closed,
            'utilization': self.stats['current_size'] / self.maxsize if self.maxsize > 0 else 0,
        }
    
    def __repr__(self) -> str:
        return f"IntelligenceQueue(size={self.qsize()}/{self.maxsize}, closed={self.closed})"
