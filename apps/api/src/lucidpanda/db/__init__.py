"""
src.lucidpanda/db/__init__.py
================================
向下兼容外观层：所有对 IntelligenceDB 的调用无需任何修改。

架构：多重继承 Mixin
  IntelligenceDB
    ├── IntelligenceRepo  (情报 CRUD / 去重 / 向量 / 信源可信度)
    ├── MarketRepo        (市场快照 / 指标 / 交易时段)
    └── FundRepo          (基金 / 持仓 / 估值 / 自选单)
"""

from src.lucidpanda.db.intelligence import IntelligenceRepo
from src.lucidpanda.db.market import MarketRepo
from src.lucidpanda.db.fund import FundRepo


class IntelligenceDB(IntelligenceRepo, MarketRepo, FundRepo):
    """
    全功能数据库门面。
    Backward-compatible: 全项目所有 self.db.xxx() 调用均直接有效。
    """
    pass


__all__ = ["IntelligenceDB"]
