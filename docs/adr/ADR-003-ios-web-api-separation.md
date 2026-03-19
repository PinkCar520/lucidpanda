# ADR-003: iOS 与 Web 独立 API 路由策略

**日期**: 2026-03-19  
**状态**: 已接受  
**决策者**: 项目团队

---

## 背景

iOS 端和 Web 端对同一业务数据的需求不同：
- iOS 需要精简的响应（带宽敏感，本地缓存需求）
- Web 端可以接受更丰富的数据，支持更多实时交互

## 决策

**为 iOS 和 Web 分别维护独立的 API 路由文件**：
- `api/v1/routers/web.py` → Web 前端专用
- `api/v1/routers/mobile.py` → iOS App 专用

共享的业务逻辑放在 `services/` 层，两个路由文件都调用同一套 Service。

## 详细说明

```
mobile.py ─┐
           ├→ services/ (共享业务逻辑)
web.py    ─┘
```

iOS 专有特性：
- 响应字段更精简
- 支持 cursor-based 分页（适合滚动加载）
- 某些字段格式针对 Swift Codable 优化

## 被拒绝的方案

| 方案 | 被拒原因 |
|------|---------|
| 同一套路由 + 版本号区分 | 条件分支过多，维护复杂 |
| GraphQL | 学习成本高，团队经验不足，过度设计 |
| 完全分离后端 | 维护成本翻倍 |

## 后果

**正面影响**:
- 每端 API 可以独立优化，互不干扰
- iOS 更新不会破坏 Web，反之亦然

**负面影响/需要接受的妥协**:
- 新功能需要在两个文件都添加端点
- 需要纪律保证两端共用 Service 而非重复业务逻辑

## AI操作指引

- 开发新功能：确认该功能需要哪些端（Web/iOS/两者都要）
- **禁止**：在 mobile.py 或 web.py 中各自实现一套业务逻辑（必须共用 service）
- 相关文件:
  - `src/lucidpanda/api/v1/routers/web.py`
  - `src/lucidpanda/api/v1/routers/mobile.py`
  - `src/lucidpanda/services/`
