# database.py — 兼容转发层
# 全项目所有 `from src.lucidpanda.core.database import IntelligenceDB` 保持有效。
# 实现已迁移至 src.lucidpanda/db/ 分域模块。
from src.lucidpanda.db import IntelligenceDB

__all__ = ["IntelligenceDB"]
