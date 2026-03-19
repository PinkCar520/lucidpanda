# SSE (Server-Sent Events) 升级指南

## 架构概述

SSE 方案将 LucidPanda 从"定时轮询"升级为"实时推送"，实现秒级的新闻更新体验。

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Python Backend │ ──写入─→ │  SQLite Database │ ←──监听─ │  SSE Server     │
│  (run.py)       │         │  (LucidPanda.db)│         │  (sse_server.py)│
└─────────────────┘         └──────────────────┘         └────────┬────────┘
                                                                   │
                                                                   │ SSE Stream
                                                                   ↓
                                                          ┌─────────────────┐
                                                          │  Next.js Frontend│
                                                          │  (useSSE hook)   │
                                                          └─────────────────┘
```

## 后端改动清单

### 1. 安装依赖

```bash
cd /Users/caomeifengli/workspace/LucidPanda
pip install fastapi uvicorn
```

### 2. 启动 SSE 服务器

```bash
# 方式 1: 直接运行
python sse_server.py

# 方式 2: 使用 uvicorn (生产环境推荐)
uvicorn sse_server:app --host 0.0.0.0 --port 8001 --reload
```

SSE 服务器会在 `http://localhost:8001` 启动。

### 3. 配置 Next.js 代理（开发环境）

在 `web/next.config.ts` 中添加代理配置，将 `/api/sse/*` 请求转发到 SSE 服务器：

```typescript
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/sse/:path*',
        destination: 'http://localhost:8001/api/:path*',
      },
    ];
  },
};
```

### 4. 生产环境部署（Nginx）

```nginx
# Nginx 配置示例
location /api/intelligence/stream {
    proxy_pass http://localhost:8001;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding off;
}
```

## 前端改动清单

### 1. 在 `page.tsx` 中使用 SSE Hook

```tsx
import { useSSE } from '@/hooks/useSSE';

// 在组件内部
const { isConnected, error } = useSSE({
  url: '/api/sse/intelligence/stream',
  enabled: true, // 可以根据用户设置开关
  onMessage: (newItems) => {
    // 将新数据 prepend 到现有列表
    setIntelligence(prev => [...newItems, ...prev]);
    
    // 可选：显示通知
    if (newItems.length > 0) {
      toast.success(`${newItems.length} new intelligence items`);
    }
  },
  onError: (err) => {
    console.error('SSE connection error:', err);
  }
});

// 在 UI 中显示连接状态
{isConnected && <Badge variant="success">● LIVE</Badge>}
{error && <Badge variant="error">⚠ {error}</Badge>}
```

### 2. 移除旧的轮询逻辑

删除或注释掉 `useEffect` 中的 `setInterval` 轮询代码。

## 优势对比

| 特性 | 轮询 (Polling) | SSE (Server-Sent Events) |
|------|----------------|--------------------------|
| 延迟 | 30-60 秒 | **< 2 秒** |
| 服务器负载 | 高（每个客户端每 30s 一次请求） | **低（长连接，按需推送）** |
| 带宽消耗 | 高（重复拉取相同数据） | **极低（仅推送新数据）** |
| 实时性 | 差 | **优秀** |
| 复杂度 | 简单 | 中等 |

## 注意事项

1. **浏览器兼容性**：SSE 在所有现代浏览器中都支持（IE 除外）
2. **连接数限制**：浏览器对同一域名的 SSE 连接有限制（通常 6 个），但对于单页应用足够
3. **自动重连**：`useSSE` hook 已实现自动重连机制
4. **Nginx 配置**：生产环境务必禁用 buffering，否则 SSE 无法工作

## 测试步骤

1. 启动 SSE 服务器：`python sse_server.py`
2. 启动 Next.js：`npm run dev`
3. 打开浏览器控制台，应该看到 `[SSE] Connection established`
4. 运行 Python 后端写入新数据：`python run.py`
5. 前端应在 2 秒内收到新数据并更新列表

## 回退方案

如果 SSE 出现问题，可以随时切换回轮询模式：

```tsx
const { isConnected } = useSSE({ 
  url: '/api/sse/intelligence/stream',
  enabled: false  // 禁用 SSE
});

// 恢复轮询
useEffect(() => {
  const interval = setInterval(fetchData, 30000);
  return () => clearInterval(interval);
}, []);
```
