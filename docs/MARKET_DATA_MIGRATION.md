# 市场数据 API 优化方案

## 当前状态

### 问题诊断
- **数据源**：Yahoo Finance（非官方 API）
- **风险**：
  - ❌ 无 SLA 保证，随时可能中断
  - ❌ 速率限制不明确，可能被 IP 封锁
  - ❌ API 结构可能随时变更
  - ❌ 生产环境不可靠

### 已实施的短期优化 ✅

1. **智能缓存系统**
   - 实时数据缓存 1 分钟
   - 历史数据缓存 5 分钟
   - 降级策略：API 失败时使用 1 小时内的陈旧缓存

2. **健壮性增强**
   - 8 秒请求超时
   - 自动重试机制（最多 2 次）
   - 优雅降级（返回缓存而非直接报错）

3. **监控和调试**
   - 详细的日志记录
   - 缓存命中率追踪
   - 自动清理过期缓存

## 长期解决方案

### 推荐方案对比

| 数据源 | 免费额度 | 延迟 | 可靠性 | 数据质量 | 推荐度 |
|--------|---------|------|--------|----------|--------|
| **Polygon.io** | 5 req/min | 低 | ⭐⭐⭐⭐⭐ | 交易所级 | ⭐⭐⭐⭐⭐ |
| **Alpha Vantage** | 5 req/min | 中 | ⭐⭐⭐⭐ | 高 | ⭐⭐⭐⭐ |
| **Binance API** | 1200 req/min | 极低 | ⭐⭐⭐⭐⭐ | 实时 | ⭐⭐⭐ (仅加密货币) |
| Yahoo Finance | 不明 | 中 | ⭐⭐ | 中 | ⭐⭐ (仅开发) |

---

## 迁移指南

### 方案 1: Polygon.io（推荐）

**优势**：
- ✅ 专业级金融数据 API
- ✅ 免费层：5 请求/分钟，500 请求/天
- ✅ 支持股票、期货、外汇、加密货币
- ✅ WebSocket 实时数据流
- ✅ 99.9% SLA 保证

**实施步骤**：

1. **注册账号**
   ```bash
   # 访问 https://polygon.io/dashboard/signup
   # 免费层无需信用卡
   ```

2. **获取 API Key**
   ```bash
   # 添加到 .env.local
   echo "POLYGON_API_KEY=your_api_key_here" >> web/.env.local
   ```

3. **安装 SDK**
   ```bash
   cd web
   npm install @polygon.io/client-js
   ```

4. **创建适配器**
   ```typescript
   // web/app/api/market/providers/polygon.ts
   import { restClient } from '@polygon.io/client-js';

   export async function fetchPolygonData(symbol: string, range: string) {
     const client = restClient(process.env.POLYGON_API_KEY);
     
     // 黄金期货: GC=F -> GC (Polygon 格式)
     const polygonSymbol = symbol.replace('=F', '');
     
     const data = await client.stocks.aggregates(
       polygonSymbol,
       1,
       'day',
       '2024-01-01',
       '2024-12-31'
     );
     
     return transformToChartFormat(data);
   }
   ```

5. **更新配置**
   ```typescript
   // web/lib/market-config.ts
   export const MARKET_DATA_CONFIG = {
     PROVIDER: 'polygon', // 从 'yahoo' 改为 'polygon'
     // ...
   };
   ```

**成本估算**：
- 免费层：$0/月（5 req/min）
- Starter：$29/月（100 req/min）
- Developer：$99/月（无限制）

---

### 方案 2: Alpha Vantage

**优势**：
- ✅ 简单易用
- ✅ 免费层：5 请求/分钟，500 请求/天
- ✅ 支持股票、外汇、加密货币、商品

**实施步骤**：

1. **注册并获取 API Key**
   ```bash
   # 访问 https://www.alphavantage.co/support/#api-key
   echo "ALPHAVANTAGE_API_KEY=your_key" >> web/.env.local
   ```

2. **创建适配器**
   ```typescript
   // web/app/api/market/providers/alphavantage.ts
   export async function fetchAlphaVantageData(symbol: string) {
     const url = `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=${symbol}&apikey=${process.env.ALPHAVANTAGE_API_KEY}`;
     const response = await fetch(url);
     return response.json();
   }
   ```

**限制**：
- 免费层速率限制较严格
- 历史数据有限

---

### 方案 3: Binance（仅适用于代币化黄金）

**优势**：
- ✅ 完全免费，无速率限制
- ✅ 极低延迟（< 100ms）
- ✅ WebSocket 实时推送

**注意**：
- ⚠️ 只能追踪 PAXG（PAX Gold，代币化黄金）
- ⚠️ 不是真实的黄金期货价格
- ⚠️ 仅适合作为参考指标

**实施步骤**：

1. **无需 API Key**（公开端点）

2. **创建适配器**
   ```typescript
   // web/app/api/market/providers/binance.ts
   export async function fetchBinanceGold() {
     const url = 'https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=1h&limit=100';
     const response = await fetch(url);
     const data = await response.json();
     return transformBinanceData(data);
   }
   ```

---

## 混合策略（推荐）

**最佳实践**：使用多数据源 + 智能降级

```typescript
// web/app/api/market/route.ts
async function fetchMarketData(symbol: string) {
  try {
    // 1. 优先使用 Polygon（付费用户）
    if (MARKET_DATA_CONFIG.POLYGON.enabled) {
      return await fetchPolygonData(symbol);
    }
  } catch (error) {
    console.warn('Polygon failed, trying fallback...');
  }

  try {
    // 2. 降级到 Yahoo Finance
    return await fetchYahooData(symbol);
  } catch (error) {
    console.warn('Yahoo failed, using cache...');
  }

  // 3. 最终降级：返回缓存
  return getCachedData(symbol);
}
```

---

## 监控和告警

### 推荐工具

1. **Sentry**（错误追踪）
   ```bash
   npm install @sentry/nextjs
   ```

2. **Uptime Robot**（API 可用性监控）
   - 免费监控 50 个端点
   - 每 5 分钟检查一次

3. **自定义健康检查**
   ```typescript
   // web/app/api/health/route.ts
   export async function GET() {
     const marketHealth = await checkMarketAPI();
     return NextResponse.json({
       status: marketHealth ? 'healthy' : 'degraded',
       providers: {
         yahoo: marketHealth,
         cache: true
       }
     });
   }
   ```

---

## 成本优化建议

### 当前配置（免费）
- Yahoo Finance: $0
- 缓存: 内存缓存（$0）
- **总成本**: $0/月

### 推荐配置（生产环境）
- Polygon.io Starter: $29/月
- Redis 缓存（Upstash）: $0-10/月
- Sentry 错误追踪: $0（免费层）
- **总成本**: ~$30-40/月

### ROI 分析
- ✅ 99.9% 可用性保证
- ✅ 避免用户流失（因 API 中断）
- ✅ 专业形象
- ✅ 可扩展性

---

## 下一步行动

### 立即可做（已完成 ✅）
- [x] 实施智能缓存
- [x] 添加降级机制
- [x] 增强错误处理

### 短期（1-2 周）
- [ ] 注册 Polygon.io 免费账号
- [ ] 实现 Polygon 适配器
- [ ] A/B 测试两个数据源

### 中期（1 个月）
- [ ] 迁移到 Polygon.io 作为主数据源
- [ ] 实施 Redis 缓存（替代内存缓存）
- [ ] 添加 Sentry 监控

### 长期（3 个月）
- [ ] 评估升级到 Polygon Starter 计划
- [ ] 实现 WebSocket 实时数据流
- [ ] 多数据源智能路由

---

## 技术支持

如有问题，请参考：
- Polygon.io 文档: https://polygon.io/docs
- Alpha Vantage 文档: https://www.alphavantage.co/documentation
- Binance API 文档: https://binance-docs.github.io/apidocs

或联系开发团队。
