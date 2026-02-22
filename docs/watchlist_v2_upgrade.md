# 基金自选列表 v2.0 升级文档

## 📋 功能概述

本次升级为基金自选列表添加了完整的分组管理、多端同步、实时推送功能。

### 新增功能

- ✅ **分组管理**: 创建、编辑、删除分组，移动基金到分组
- ✅ **多维度排序**: 自定义排序、涨幅榜、跌幅榜、名称 A-Z
- ✅ **批量操作**: 批量删除、编辑模式
- ✅ **删除撤销**: 删除后 5 秒内可撤销
- ✅ **本地缓存**: SwiftData 离线缓存
- ✅ **同步引擎**: 离线队列、增量同步、冲突解决
- ✅ **实时推送**: SSE 实时同步多端变更

---

## 🗄️ 数据库迁移

### 1. 执行迁移脚本

```bash
# 1. 备份数据库
pg_dump -U postgres alphasignal > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 执行迁移
psql -U postgres alphasignal -f scripts/migrations/001_watchlist_upgrade.sql

# 3. 验证数据
psql -U postgres alphasignal -c "SELECT COUNT(*) FROM fund_watchlist;"
psql -U postgres alphasignal -c "SELECT COUNT(*) FROM watchlist_groups;"
```

### 2. 新增数据表

#### `watchlist_groups` - 分组表
```sql
CREATE TABLE watchlist_groups (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(50),
    icon VARCHAR(50) DEFAULT 'folder',
    color VARCHAR(20) DEFAULT '#007AFF',
    sort_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

#### `watchlist_sync_log` - 同步日志表
```sql
CREATE TABLE watchlist_sync_log (
    id UUID PRIMARY KEY,
    user_id UUID,
    operation_type VARCHAR(20),  -- ADD, REMOVE, UPDATE, REORDER, MOVE_GROUP
    fund_code VARCHAR(20),
    old_value JSONB,
    new_value JSONB,
    device_id VARCHAR(50),
    client_timestamp TIMESTAMPTZ,
    server_timestamp TIMESTAMPTZ,
    is_synced BOOLEAN
);
```

#### `fund_watchlist` - 升级后的自选表
```sql
CREATE TABLE fund_watchlist (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    fund_code VARCHAR(20),
    fund_name VARCHAR(100),
    group_id UUID REFERENCES watchlist_groups(id),
    sort_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, fund_code)
);
```

---

## 🔌 API 接口

### 基础路径：`/api/v1/web`

#### 分组管理

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/watchlist/groups` | 获取分组列表 |
| `POST` | `/watchlist/groups` | 创建分组 |
| `PUT` | `/watchlist/groups/{id}` | 更新分组 |
| `DELETE` | `/watchlist/groups/{id}` | 删除分组 |

#### 自选列表

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/watchlist` | 获取自选列表（含分组） |
| `GET` | `/watchlist?group_id=xxx` | 按分组筛选 |
| `POST` | `/watchlist/batch-add` | 批量添加 |
| `POST` | `/watchlist/batch-remove` | 批量删除 |
| `POST` | `/watchlist/reorder` | 批量排序 |
| `PUT` | `/watchlist/{code}/group` | 移动分组 |

#### 同步接口

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/watchlist/sync?since=2026-02-22T10:00:00Z` | 增量同步 |
| `POST` | `/watchlist/sync` | 上报操作队列 |

#### 实时推送

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/watchlist/stream` | SSE 实时推送 |

---

## 📱 iOS 端实现

### 文件结构

```
mobile/ios/
├── Packages/
│   ├── AlphaData/
│   │   └── Sources/AlphaData/Models/
│   │       └── WatchlistModels.swift       # 数据模型
│   └── AlphaDesign/
│       └── Sources/AlphaDesign/Extensions/
│           └── Color+Hex.swift             # 颜色工具
└── alphaSignal/
    ├── Data/Cache/
    │   └── WatchlistCache.swift            # 本地缓存
    ├── Core/Sync/
    │   └── WatchlistSyncEngine.swift       # 同步引擎
    └── Features/Funds/
        ├── FundViewModel.swift             # ViewModel
        └── FundDashboardView.swift         # UI 视图
```

### 核心类

#### `WatchlistCacheManager`
- 本地缓存管理（SwiftData）
- 待同步操作队列
- 离线数据持久化

#### `WatchlistSyncEngine`
- SSE 实时连接
- 增量同步
- 冲突解决

#### `FundViewModel`
- 自选列表 CRUD
- 分组管理
- 排序、筛选
- 编辑模式

---

## 🎨 UI 功能

### 1. 分组筛选器
- 横向滚动 Chip
- 点击切换分组
- 显示分组图标和颜色

### 2. 编辑模式
- 左上角"编辑/取消"按钮
- 多选复选框
- 批量删除工具栏

### 3. 排序菜单
- 自定义排序
- 涨幅榜
- 跌幅榜
- 名称 A-Z

### 4. 删除功能
- 左滑删除
- 长按菜单删除
- 删除确认对话框
- 撤销 Toast（5 秒）

### 5. 移动分组
- 左滑"移动"按钮
- 长按菜单"移动分组"
- 分组选择器
- 新建分组弹窗

### 6. 添加基金
- 右上角"+"按钮
- 搜索添加
- 空状态引导

---

## 🔄 同步流程

### 在线场景

```
用户操作 → 乐观更新 UI → 调用 API → 刷新列表
```

### 离线场景

```
用户操作 → 乐观更新 UI → 写入待同步队列 → 网络恢复 → 批量上报
```

### 多端同步

```
Web 添加 → 写入 DB → SSE 推送 → iOS 拉取 → 合并数据
```

---

## ⚠️ 注意事项

### 数据迁移
- 迁移前务必备份数据库
- 检查 `users` 表的关联字段
- 迁移后验证数据完整性

### 兼容性
- 保留旧版 API (`/api/v1/web/watchlist`)
- 新版 API 使用 `/api/v1/web/watchlist/*` (v2 路由)
- iOS 端逐步迁移到 v2 API

### 性能优化
- 增量同步减少数据传输
- 本地缓存降低网络请求
- SSE 长连接替代轮询

---

## 🧪 测试清单

### 后端
- [ ] 创建分组
- [ ] 删除分组（基金迁移）
- [ ] 批量添加/删除
- [ ] 移动分组
- [ ] 增量同步
- [ ] SSE 推送

### iOS
- [ ] 添加基金
- [ ] 删除基金
- [ ] 撤销删除
- [ ] 批量删除
- [ ] 创建分组
- [ ] 移动分组
- [ ] 排序切换
- [ ] 离线操作
- [ ] 同步冲突

---

## 📚 相关文档

- [API 设计文档](../../docs/api/watchlist_v2.md)
- [数据库设计](../../docs/database/watchlist_schema.md)
- [同步协议](../../docs/sync/protocol.md)

---

## 🚀 后续计划

1. **Web 端同步升级** - 同步 iOS 端的分组、排序功能
2. **拖拽排序** - 实现自定义拖拽排序
3. **智能推荐** - 基于持仓推荐基金
4. **分享功能** - 分享自选列表

---

**更新日期**: 2026-02-22  
**版本**: v2.0.0
