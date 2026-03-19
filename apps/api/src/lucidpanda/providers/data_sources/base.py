from abc import ABC, abstractmethod


class BaseDataSource(ABC):
    """
    所有情报数据源的抽象基类。
    子类通过注入 IntelligenceDB 实例实现统一的 DB 级去重，
    彻底替代原来各自维护独立文件状态的冲突架构。
    """

    def __init__(self, db=None):
        """
        Args:
            db: IntelligenceDB 实例，用于 DB 级 source_id 去重查询。
                若为 None 则降级为无去重模式（仅用于单元测试）。
        """
        self.db = db

    @abstractmethod
    def fetch(self):
        """
        获取最新情报数据。
        Returns:
            list[dict] | None: 情报列表，每条格式为：
            {
                "id":        str,   # 唯一标识，用作 DB source_id
                "content":   str,
                "url":       str,
                "source":    str,
                "timestamp": str,
            }
        """
        pass
