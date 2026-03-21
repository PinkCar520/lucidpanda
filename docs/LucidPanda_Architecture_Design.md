# LucidPanda 项目架构设计文档

> **AI 原生金融量化分析平台 - 系统设计级文档**  
> 版本: v1.0  
> 更新日期: 2026-03-19

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术选型决策](#2-技术选型决策)
- [3. Monorepo 架构设计](#3-monorepo-架构设计)
- [4. 系统分层架构](#4-系统分层架构)
- [5. 数据流设计](#5-数据流设计)
- [6. iOS 集成方案](#6-ios-集成方案)
- [7. AI 辅助开发最佳实践](#7-ai-辅助开发最佳实践)
- [8. 部署与运维](#8-部署与运维)
- [9. 安全与合规](#9-安全与合规)
- [10. 从 OpenClaw 学到的经验](#10-从-openclaw-学到的经验)
- [附录 A: 完整配置文件](#附录-a-完整配置文件)
- [附录 B: 开发工作流](#附录-b-开发工作流)

---

## 1. 项目概述

### 1.1 项目定位

**LucidPanda** 是一个 AI 原生的金融量化分析平台，专注于：
- **当前阶段**: 黄金和基金的新闻量化分析
- **长期愿景**: 构建全能智能助手系统（类 Jarvis）

**核心能力**:
- 新闻实时采集与智能解析
- AI 驱动的情感分析与量化信号生成
- 多端同步体验（iOS + Web）
- 基于 RAG 的智能问答系统

### 1.2 技术栈总览

```
前端:
  - Web: Next.js 14 + React 18 + TypeScript
  - iOS: SwiftUI + Combine

后端:
  - API: Node.js (或 Python FastAPI)
  - Gateway: WebSocket 控制平面

AI 基础:
  - LLM: Claude (Anthropic) / GPT-4 (OpenAI)
  - RAG: Pinecone + LangChain
  - Embedding: text-embedding-3-large

数据存储:
  - 向量数据库: Pinecone / Qdrant
  - 时序数据库: InfluxDB / TimescaleDB
  - 文档数据库: MongoDB
  - 缓存: Redis

基础设施:
  - 容器: Docker + Kubernetes
  - CI/CD: GitHub Actions
  - 监控: Prometheus + Grafana
```

---

## 2. 技术选型决策

### 2.1 Monorepo 工具选择

**✅ 最终决策: pnpm Workspaces（不使用 Nx/Turborepo）**

#### 对比分析

| 维度 | pnpm Workspaces | Nx | Turborepo |
|------|----------------|----|----|
| 配置复杂度 | ⭐ 极简 | ⭐⭐⭐ 中等 | ⭐⭐ 简单 |
| 学习曲线 | ⭐ 低 | ⭐⭐⭐⭐ 高 | ⭐⭐ 中 |
| 构建缓存 | ❌ 无 | ✅ 强大 | ✅ 基础 |
| 依赖图分析 | ❌ 无 | ✅ 强大 | ❌ 无 |
| AI 友好度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 适用规模 | 1-20 包 | 50+ 包 | 10-50 包 |

#### 选择理由（参考 OpenClaw）

1. **项目规模适中**: 预计 10-15 个包，pnpm 原生功能足够
2. **构建速度快**: TypeScript → JavaScript 构建 < 10 秒
3. **AI 辅助开发**: 简单结构更容易被 AI 理解和生成代码
4. **零配置开销**: 无需 nx.json/turbo.json
5. **社区成熟**: pnpm 生态完善，问题容易解决

#### 何时重新考虑 Nx/Turborepo?

触发条件:
- [ ] 包数量超过 30 个
- [ ] 全量构建时间 > 3 分钟
- [ ] 团队规模 > 5 人
- [ ] 需要每个包独立版本管理
- [ ] CI/CD 构建成本过高

### 2.2 包管理器选择

**✅ 现阶段: pnpm**  
**🔮 未来迁移: Bun（观望中）**

#### pnpm 优势
- 节省磁盘空间（硬链接机制）
- 幽灵依赖问题少（严格的 node_modules 结构）
- Monorepo 原生支持
- 性能优秀（比 npm 快 2-3 倍）

#### Bun 现状
- ✅ 速度极快（10x npm）
- ✅ 内置测试/打包工具
- ❌ 生态不够成熟（某些包不兼容）
- ❌ TypeScript 项目支持还在完善

**迁移计划**: 等 Bun 1.2+ 稳定后，逐步迁移

---

## 3. Monorepo 架构设计

### 3.1 目录结构

```
lucidpanda/
├── .ai/                          # AI 辅助开发配置 ⭐
│   ├── cursor-rules.md           # Cursor 规则
│   ├── copilot.yml               # GitHub Copilot 配置
│   └── templates/                # 代码模板
│
├── apps/
│   ├── web/                      # Next.js Web 端
│   │   ├── src/
│   │   ├── public/
│   │   ├── package.json
│   │   └── next.config.js
│   │
│   ├── api/                      # Node.js API 服务
│   │   ├── src/
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── ios/                      # SwiftUI iOS 端 ⭐
│       ├── project.yml           # XcodeGen 配置
│       ├── LucidPanda/
│       │   ├── App/
│       │   ├── Features/
│       │   ├── Shared/
│       │   └── Generated/        # 从 TS 生成的 Swift 类型
│       └── LucidPanda.xcodeproj  # 生成的 Xcode 项目
│
├── packages/
│   ├── gateway/                  # WebSocket 控制平面 ⭐
│   │   ├── src/
│   │   │   ├── server.ts
│   │   │   ├── sessions.ts
│   │   │   └── events.ts
│   │   └── package.json
│   │
│   ├── ai-engine/                # AI 分析引擎
│   │   ├── src/
│   │   │   ├── llm-service.ts
│   │   │   ├── rag-pipeline.ts
│   │   │   └── agent-orchestration.ts
│   │   └── package.json
│   │
│   ├── quant-engine/             # 量化引擎
│   │   ├── src/
│   │   │   ├── indicators.ts
│   │   │   ├── backtesting.ts
│   │   │   └── signals.ts
│   │   └── package.json
│   │
│   ├── shared-types/             # 共享类型定义
│   │   ├── src/
│   │   │   ├── user.types.ts
│   │   │   ├── news.types.ts
│   │   │   └── portfolio.types.ts
│   │   └── package.json
│   │
│   ├── ui-components/            # 共享 UI 组件
│   │   ├── src/
│   │   └── package.json
│   │
│   └── utils/                    # 工具函数
│       ├── src/
│       └── package.json
│
├── extensions/                   # 数据源适配器 ⭐
│   ├── bloomberg/
│   ├── reuters/
│   ├── yahoo-finance/
│   └── alpha-vantage/
│
├── skills/                       # AI Skills (按需加载) ⭐
│   ├── technical-analysis/
│   │   └── SKILL.md
│   ├── news-sentiment/
│   │   └── SKILL.md
│   └── risk-management/
│       └── SKILL.md
│
├── tools/
│   ├── scripts/
│   │   └── generate-swift-types.ts  # TS → Swift 类型生成
│   └── generators/               # 代码生成器
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── package.json                  # 根 package.json
├── pnpm-workspace.yaml           # pnpm 工作区配置
├── tsconfig.json                 # 全局 TypeScript 配置
├── .gitignore
└── README.md
```

### 3.2 核心配置文件

#### pnpm-workspace.yaml

```yaml
packages:
  - 'packages/*'
  - 'apps/*'
  - 'extensions/*'
```

#### package.json (根目录)

```json
{
  "name": "lucidpanda",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "pnpm -r --parallel run dev",
    "build": "pnpm -r run build",
    "test": "vitest",
    "lint": "eslint .",
    "format": "prettier --write .",
    
    "dev:web": "pnpm --filter @lucidpanda/web dev",
    "dev:api": "pnpm --filter @lucidpanda/api dev",
    "dev:gateway": "pnpm --filter @lucidpanda/gateway dev",
    
    "generate:swift-types": "tsx tools/scripts/generate-swift-types.ts",
    "ios:setup": "cd apps/ios && xcodegen generate",
    
    "docker:build": "docker-compose build",
    "docker:up": "docker-compose up -d"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "eslint": "^8.56.0",
    "prettier": "^3.1.0",
    "tsx": "^4.7.0",
    "quicktype": "^23.0.0"
  },
  "engines": {
    "node": ">=20.0.0",
    "pnpm": ">=8.0.0"
  }
}
```

---

## 4. 系统分层架构

### 4.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│              Client Layer (客户端层)                     │
│  ┌──────────────┐              ┌──────────────┐         │
│  │  iOS App     │              │  Web App     │         │
│  │  (SwiftUI)   │              │  (Next.js)   │         │
│  └──────┬───────┘              └──────┬───────┘         │
└─────────┼────────────────────────────┼─────────────────┘
          │                            │
          │    WebSocket / REST API    │
          │                            │
┌─────────┼────────────────────────────┼─────────────────┐
│         ▼                            ▼                  │
│  ┌───────────────────────────────────────────────┐     │
│  │         API Gateway Layer (网关层)             │     │
│  │  ┌─────────────────────────────────────────┐  │     │
│  │  │  Gateway (WebSocket Server)              │  │     │
│  │  │  - 会话管理 - 消息路由 - 工具调度        │  │     │
│  │  └─────────────────────────────────────────┘  │     │
│  └───────────────────────────────────────────────┘     │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                          ▼                               │
│  ┌───────────────────────────────────────────────┐      │
│  │       Core Services Layer (核心服务层)         │      │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐       │      │
│  │  │  News   │  │   AI    │  │  Quant  │       │      │
│  │  │ Ingestion│  │ Analysis│  │ Engine  │       │      │
│  │  └─────────┘  └─────────┘  └─────────┘       │      │
│  └───────────────────────────────────────────────┘      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                          ▼                               │
│  ┌───────────────────────────────────────────────┐      │
│  │      AI Foundation Layer (AI 基础层)           │      │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐       │      │
│  │  │   LLM   │  │   RAG   │  │  Agent  │       │      │
│  │  │ Service │  │ Pipeline│  │Orchestra│       │      │
│  │  └─────────┘  └─────────┘  └─────────┘       │      │
│  └───────────────────────────────────────────────┘      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                          ▼                               │
│  ┌───────────────────────────────────────────────┐      │
│  │          Data Layer (数据层)                   │      │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │      │
│  │  │ Vector │ │  Time  │ │Document│ │ Cache  │ │      │
│  │  │  Store │ │ Series │ │   DB   │ │ (Redis)│ │      │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ │      │
│  └───────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Gateway 控制平面设计（核心创新）

**借鉴 OpenClaw 的 Gateway 模式**

#### 为什么需要 Gateway?

传统架构的问题:
- ❌ iOS 和 Web 各自调用 REST API，状态不同步
- ❌ 实时性差（轮询或 SSE）
- ❌ AI 上下文需要每次重建
- ❌ 多端会话管理复杂

Gateway 模式的优势:
- ✅ 单一 WebSocket 控制平面
- ✅ iOS/Web 共享同一个 AI 实例
- ✅ 会话状态自动维护
- ✅ 实时双向通信

#### Gateway 核心职责

```typescript
// packages/gateway/src/server.ts

interface GatewayServer {
  // 1. 会话管理
  sessions: {
    create(userId: string): Session;
    get(sessionId: string): Session | null;
    list(): Session[];
    destroy(sessionId: string): void;
  };
  
  // 2. 消息路由
  routing: {
    send(to: string, message: Message): void;
    broadcast(message: Message): void;
  };
  
  // 3. 工具调度
  tools: {
    invoke(toolName: string, params: unknown): Promise<ToolResult>;
    register(tool: Tool): void;
  };
  
  // 4. 事件总线
  events: {
    on(event: string, handler: EventHandler): void;
    emit(event: string, data: unknown): void;
  };
}
```

#### Gateway 协议设计

```typescript
// WebSocket 消息格式
type GatewayMessage = 
  | { type: 'session.create'; userId: string }
  | { type: 'session.send'; sessionId: string; message: string }
  | { type: 'tool.invoke'; tool: string; params: unknown }
  | { type: 'event.subscribe'; event: string }
  | { type: 'ping' };

// 响应格式
type GatewayResponse = 
  | { type: 'session.created'; sessionId: string }
  | { type: 'message.received'; content: string; streaming: boolean }
  | { type: 'tool.result'; result: unknown }
  | { type: 'error'; code: string; message: string }
  | { type: 'pong' };
```

---

## 5. 数据流设计

### 5.1 新闻分析流程

```
1. 数据采集
   Bloomberg API / Reuters / RSS Feeds
          ↓
   [News Ingestion Service]
          ↓
2. 消息队列
   Kafka Topic: 'raw_news'
          ↓
3. AI 分析
   [AI Analysis Engine]
   • 实体识别 (NER)
   • 情感分析
   • 事件检测
          ↓
4. 数据存储
   MongoDB (原始数据) + Pinecone (向量化)
          ↓
5. 信号生成
   如果触发条件 → Kafka Topic: 'trading_signals'
          ↓
6. 前端推送
   Gateway WebSocket → iOS/Web
```

### 5.2 用户问答流程 (RAG)

```
1. 用户提问
   iOS/Web → Gateway
          ↓
2. 向量化
   [Embedding Service]
   text-embedding-3-large
          ↓
3. 向量检索
   Pinecone (Top-K=5)
          ↓
4. 重排序
   [Cross-Encoder Reranker]
          ↓
5. Prompt 构建
   System + Context + Question
          ↓
6. LLM 生成
   Claude / GPT-4
          ↓
7. 流式返回
   Gateway → iOS/Web (streaming)
```

### 5.3 量化信号生成流程

```
1. 市场数据推送
   Market Data API → Time Series DB
          ↓
2. 技术指标计算
   [Quant Engine]
   MA, MACD, RSI, Bollinger Bands
          ↓
3. 情绪因子融合
   AI 分析结果 → 情绪因子
          ↓
4. 多因子模型
   [Signal Generator]
   技术指标 + 情绪因子 → 综合信号
          ↓
5. 信号存储与推送
   MongoDB + Gateway → iOS/Web
```

---

## 6. iOS 集成方案

### 6.1 XcodeGen 配置

**参考 OpenClaw 的混合 Monorepo 方案**

```yaml
# apps/ios/project.yml

name: LucidPanda
options:
  bundleIdPrefix: com.lucidpanda
  deploymentTarget:
    iOS: "17.0"

targets:
  LucidPanda:
    type: application
    platform: iOS
    sources:
      - LucidPanda/
    settings:
      PRODUCT_BUNDLE_IDENTIFIER: com.lucidpanda.app
      DEVELOPMENT_TEAM: YOUR_TEAM_ID
      CODE_SIGN_STYLE: Automatic
    dependencies:
      - sdk: SwiftUI.framework
      - sdk: Combine.framework

schemes:
  LucidPanda:
    build:
      targets:
        LucidPanda: all
    run:
      config: Debug
    archive:
      config: Release
```

### 6.2 TypeScript → Swift 类型生成

**使用 quicktype 自动转换**

```typescript
// tools/scripts/generate-swift-types.ts

import { quicktype, InputData, JSONSchemaInput } from 'quicktype-core';
import { writeFileSync } from 'fs';

async function generateSwiftTypes() {
  const schemaInput = new JSONSchemaInput();
  
  // 读取 TypeScript 类型定义
  await schemaInput.addSource({
    name: 'UserDTO',
    schema: JSON.stringify({
      type: 'object',
      properties: {
        id: { type: 'string' },
        email: { type: 'string' },
        name: { type: 'string' },
        portfolios: {
          type: 'array',
          items: { $ref: '#/definitions/Portfolio' }
        }
      }
    })
  });
  
  const inputData = new InputData();
  inputData.addInput(schemaInput);
  
  // 生成 Swift 代码
  const result = await quicktype({
    inputData,
    lang: 'swift',
    rendererOptions: {
      'swift-version': '5',
      'just-types': 'true'
    }
  });
  
  // 写入文件
  writeFileSync(
    'apps/ios/LucidPanda/Generated/Types.swift',
    result.lines.join('\n')
  );
  
  console.log('✅ Swift types generated successfully!');
}

generateSwiftTypes();
```

**生成的 Swift 代码示例:**

```swift
// apps/ios/LucidPanda/Generated/Types.swift
// ⚠️ 自动生成，请勿手动修改

import Foundation

struct UserDTO: Codable {
    let id: String
    let email: String
    let name: String
    let portfolios: [Portfolio]
}

struct Portfolio: Codable {
    let id: String
    let name: String
    let totalValue: Double
    let assets: [Asset]
}

struct Asset: Codable {
    let symbol: String
    let quantity: Double
    let currentPrice: Double
}
```

### 6.3 iOS 与 Gateway 通信

```swift
// apps/ios/LucidPanda/Shared/GatewayClient.swift

import Foundation
import Combine

class GatewayClient: ObservableObject {
    @Published var isConnected = false
    @Published var messages: [Message] = []
    
    private var webSocket: URLSessionWebSocketTask?
    private let baseURL = "ws://localhost:18789"
    
    func connect() {
        let url = URL(string: baseURL)!
        webSocket = URLSession.shared.webSocketTask(with: url)
        webSocket?.resume()
        
        receiveMessage()
        isConnected = true
    }
    
    func send(message: String) {
        let payload: [String: Any] = [
            "type": "session.send",
            "sessionId": getCurrentSessionId(),
            "message": message
        ]
        
        let jsonData = try! JSONSerialization.data(withJSONObject: payload)
        let message = URLSessionWebSocketTask.Message.data(jsonData)
        
        webSocket?.send(message) { error in
            if let error = error {
                print("WebSocket send error: \(error)")
            }
        }
    }
    
    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .data(let data):
                    self?.handleMessage(data: data)
                case .string(let text):
                    self?.handleMessage(text: text)
                @unknown default:
                    break
                }
                self?.receiveMessage()
                
            case .failure(let error):
                print("WebSocket receive error: \(error)")
                self?.isConnected = false
            }
        }
    }
    
    private func handleMessage(data: Data) {
        let decoder = JSONDecoder()
        if let response = try? decoder.decode(GatewayResponse.self, from: data) {
            DispatchQueue.main.async {
                // 处理不同类型的响应
                switch response.type {
                case "message.received":
                    self.messages.append(Message(content: response.content))
                default:
                    break
                }
            }
        }
    }
}
```

---

## 7. AI 辅助开发最佳实践

### 7.1 AI 规则文件

```markdown
<!-- .ai/cursor-rules.md -->

# LucidPanda AI 编码规则

## 项目结构
- `apps/`: 应用入口（web, api, ios）
- `packages/`: 共享库
- `extensions/`: 数据源适配器
- **禁止跨越模块边界引用**

## 代码规范
- 使用 TypeScript strict mode
- 所有 API 类型必须定义在 `@lucidpanda/shared-types`
- React 组件使用函数式 + Hooks
- 后端使用 async/await，禁止回调
- 文件命名: kebab-case (news-service.ts)
- 组件命名: PascalCase (NewsCard.tsx)

## AI 生成代码检查清单
- [ ] 是否有类型定义？
- [ ] 是否违反模块边界？
- [ ] 是否有单元测试？
- [ ] 是否更新了相关文档？
- [ ] 是否使用了废弃的 API？

## 禁止操作
- ❌ 直接修改 node_modules
- ❌ 使用 `any` 类型
- ❌ 在 UI 组件中直接调用 API
- ❌ 硬编码配置信息
- ❌ 提交 console.log 到生产代码

## 命名约定
- 变量: camelCase
- 常量: UPPER_SNAKE_CASE
- 类型/接口: PascalCase
- 文件: kebab-case
- 组件: PascalCase

## Git 提交规范
- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 重构
- test: 测试相关
- chore: 构建/工具链相关

示例: `feat(ai-engine): add sentiment analysis for news`
```

### 7.2 Git Hooks 防止"屎山"

```bash
# .husky/pre-commit
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

echo "🔍 Running pre-commit checks..."

# 1. 格式化代码
pnpm exec lint-staged

# 2. 类型检查
echo "📝 Type checking..."
pnpm run typecheck || exit 1

# 3. 运行测试
echo "🧪 Running tests..."
pnpm run test:affected || exit 1

# 4. 检查导入循环
echo "🔄 Checking for circular dependencies..."
pnpm exec madge --circular --extensions ts,tsx packages apps || exit 1

echo "✅ All checks passed!"
```

```json
// .lintstagedrc.json
{
  "*.{ts,tsx}": [
    "eslint --fix",
    "prettier --write"
  ],
  "*.{json,md}": [
    "prettier --write"
  ]
}
```

### 7.3 Skills 按需加载机制（借鉴 OpenClaw）

```markdown
<!-- skills/technical-analysis/SKILL.md -->

---
name: technical-analysis
description: Technical indicators and chart patterns for financial analysis
triggers:
  - MACD
  - RSI
  - Bollinger
  - moving average
  - support
  - resistance
---

# Technical Analysis Skill

## Moving Averages
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Usage: Trend identification

## Momentum Indicators
- RSI (Relative Strength Index)
  - Range: 0-100
  - Overbought: > 70
  - Oversold: < 30

## Volume Indicators
- On-Balance Volume (OBV)
- Volume Weighted Average Price (VWAP)

...完整文档只在触发时加载...
```

**按需加载逻辑:**

```typescript
// packages/ai-engine/src/skills-loader.ts

interface Skill {
  name: string;
  description: string;
  triggers: string[];
  content: string;
}

class SkillsLoader {
  private skills: Map<string, Skill> = new Map();
  private loadedSkills: Set<string> = new Set();
  
  constructor() {
    // 初始化时只加载元数据
    this.loadSkillMetadata();
  }
  
  private loadSkillMetadata() {
    const skillFiles = glob.sync('skills/**/SKILL.md');
    
    for (const file of skillFiles) {
      const content = readFileSync(file, 'utf-8');
      const { data } = matter(content); // 解析 frontmatter
      
      this.skills.set(data.name, {
        name: data.name,
        description: data.description,
        triggers: data.triggers,
        content: content // 完整内容
      });
    }
  }
  
  shouldLoadSkill(userMessage: string): string[] {
    const skillsToLoad: string[] = [];
    
    for (const [name, skill] of this.skills) {
      // 检查是否匹配触发器
      if (skill.triggers.some(trigger => 
        userMessage.toLowerCase().includes(trigger.toLowerCase())
      )) {
        if (!this.loadedSkills.has(name)) {
          skillsToLoad.push(name);
          this.loadedSkills.add(name);
        }
      }
    }
    
    return skillsToLoad;
  }
  
  getSkillContent(skillName: string): string {
    return this.skills.get(skillName)?.content || '';
  }
}

// 使用示例
const loader = new SkillsLoader();

function buildPrompt(userMessage: string): string {
  let prompt = SYSTEM_PROMPT;
  
  // 按需加载技能
  const skillsToLoad = loader.shouldLoadSkill(userMessage);
  
  for (const skillName of skillsToLoad) {
    prompt += `\n\n${loader.getSkillContent(skillName)}`;
  }
  
  prompt += `\n\nUser: ${userMessage}`;
  
  return prompt;
}
```

**效果:**
- 上下文污染最小化
- Token 使用高效（只加载需要的技能）
- 可扩展性强（300+ 技能不会爆炸）

---

## 8. 部署与运维

### 8.1 Docker 容器化

```dockerfile
# Dockerfile (多阶段构建)

# Stage 1: 构建阶段
FROM node:20-alpine AS builder

WORKDIR /app

# 安装 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# 复制依赖文件
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps ./apps

# 安装依赖
RUN pnpm install --frozen-lockfile

# 构建
RUN pnpm run build

# Stage 2: 生产阶段
FROM node:20-alpine AS runner

WORKDIR /app

# 只复制必要文件
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# 暴露端口
EXPOSE 3000 18789

# 启动命令
CMD ["node", "dist/api/index.js"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  gateway:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "18789:18789"
    environment:
      - NODE_ENV=production
      - GATEWAY_PORT=18789
    depends_on:
      - redis
      - mongodb
      - influxdb

  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=mongodb://mongodb:27017/lucidpanda
      - REDIS_URL=redis://redis:6379
    depends_on:
      - mongodb
      - redis

  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    ports:
      - "80:3000"
    environment:
      - NEXT_PUBLIC_GATEWAY_URL=ws://gateway:18789

  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    volumes:
      - influxdb_data:/var/lib/influxdb2

volumes:
  mongodb_data:
  redis_data:
  influxdb_data:
```

### 8.2 CI/CD 流程

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: pnpm/action-setup@v2
        with:
          version: 8
      
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'pnpm'
      
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      
      - name: Lint
        run: pnpm run lint
      
      - name: Type check
        run: pnpm run typecheck
      
      - name: Test
        run: pnpm run test
      
      - name: Build
        run: pnpm run build

  ios:
    runs-on: macos-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Xcode
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: '15.2'
      
      - name: Generate Swift types
        run: |
          pnpm install
          pnpm run generate:swift-types
      
      - name: Generate Xcode project
        run: |
          cd apps/ios
          brew install xcodegen
          xcodegen generate
      
      - name: Build iOS app
        run: |
          cd apps/ios
          xcodebuild -project LucidPanda.xcodeproj \
                     -scheme LucidPanda \
                     -configuration Debug \
                     build

  deploy:
    needs: [test, ios]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: docker-compose build
      
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker-compose push
      
      - name: Deploy to production
        run: |
          # 部署到 Kubernetes / Cloud Run / 其他平台
          kubectl apply -f k8s/
```

### 8.3 监控与日志

```typescript
// packages/gateway/src/monitoring.ts

import { PrometheusExporter } from '@opentelemetry/exporter-prometheus';
import { MeterProvider } from '@opentelemetry/sdk-metrics';

const exporter = new PrometheusExporter({ port: 9464 });
const meterProvider = new MeterProvider();
meterProvider.addMetricReader(exporter);

const meter = meterProvider.getMeter('lucidpanda-gateway');

// 定义指标
export const metrics = {
  activeConnections: meter.createUpDownCounter('gateway_active_connections'),
  messagesProcessed: meter.createCounter('gateway_messages_processed'),
  errorCount: meter.createCounter('gateway_errors'),
  responseTime: meter.createHistogram('gateway_response_time_ms'),
};

// 使用示例
export function trackConnection(delta: number) {
  metrics.activeConnections.add(delta);
}

export function trackMessage() {
  metrics.messagesProcessed.add(1);
}
```

---

## 9. 安全与合规

### 9.1 数据安全

**传输加密:**
- TLS 1.3 for all HTTP/WebSocket connections
- 证书: Let's Encrypt 自动续期

**存储加密:**
- AES-256 for sensitive data at rest
- 密钥管理: AWS KMS / HashiCorp Vault

**敏感数据脱敏:**
```typescript
// packages/utils/src/security.ts

export function maskEmail(email: string): string {
  const [local, domain] = email.split('@');
  return `${local.slice(0, 2)}***@${domain}`;
}

export function maskPhone(phone: string): string {
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
}
```

### 9.2 访问控制

**认证:**
- JWT (JSON Web Tokens)
- MFA (Multi-Factor Authentication)

**授权:**
- RBAC (Role-Based Access Control)
```typescript
enum Role {
  ADMIN = 'admin',
  USER = 'user',
  ANALYST = 'analyst'
}

enum Permission {
  READ_NEWS = 'read:news',
  WRITE_ANALYSIS = 'write:analysis',
  MANAGE_PORTFOLIO = 'manage:portfolio'
}

const rolePermissions: Record<Role, Permission[]> = {
  [Role.ADMIN]: [Permission.READ_NEWS, Permission.WRITE_ANALYSIS, Permission.MANAGE_PORTFOLIO],
  [Role.ANALYST]: [Permission.READ_NEWS, Permission.WRITE_ANALYSIS],
  [Role.USER]: [Permission.READ_NEWS]
};
```

### 9.3 合规性

- **GDPR**: 欧盟用户数据保护
- **SOC 2**: 安全控制审计
- **金融监管**: 符合当地证券法规

---

## 10. 从 OpenClaw 学到的经验

### 10.1 核心设计原则

✅ **极简主义 > 过度工程**
- 不用 Nx/Turborepo，pnpm workspaces 足够
- 不做过早优化
- AI 友好的简单结构

✅ **本地优先 (Local-first)**
- Gateway 运行在本地 (localhost:18789)
- 数据存储在 ~/.lucidpanda/
- 可选的远程访问（Tailscale）

✅ **单一控制平面 (Gateway)**
- WebSocket 而非 REST API
- 多端共享同一个 AI 实例
- 会话状态自动维护

✅ **按需加载 (Skills)**
- 避免上下文污染
- Token 使用高效
- 可扩展性强

### 10.2 技术栈对比

| 技术选型 | LucidPanda | OpenClaw |
|---------|-----------|----------|
| Monorepo | ✅ pnpm workspaces | ✅ pnpm workspaces |
| 包管理器 | ✅ pnpm | ✅ pnpm |
| 构建工具 | Vite, tsup | tsup, esbuild |
| iOS 集成 | ✅ XcodeGen | ✅ XcodeGen |
| Gateway | ✅ WebSocket | ✅ WebSocket |
| Skills 加载 | ✅ 按需加载 | ✅ 按需加载 |
| 测试框架 | Vitest | Vitest |
| 代码质量 | ESLint + Prettier | oxlint + oxfmt |

### 10.3 避免的陷阱

❌ **不要:**
- 使用 Nx/Turborepo（早期不需要）
- 每个包独立发布（增加复杂度）
- 过度抽象（保持简单）
- 忽略 AI 辅助开发的特殊需求

✅ **要:**
- 保持简单的目录结构
- 使用 AI 规则文件
- 设置 Git Hooks
- 按需加载 Skills
- 重视开发者体验

---

## 附录 A: 完整配置文件

### A.1 pnpm-workspace.yaml

```yaml
packages:
  - 'packages/*'
  - 'apps/*'
  - 'extensions/*'
```

### A.2 tsconfig.json (根目录)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "lib": ["ES2022"],
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "allowJs": true,
    "checkJs": false,
    "outDir": "./dist",
    "rootDir": "./",
    "removeComments": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "paths": {
      "@lucidpanda/*": ["./packages/*/src"]
    }
  },
  "include": ["packages/**/*", "apps/**/*"],
  "exclude": ["node_modules", "dist", "**/*.spec.ts"]
}
```

### A.3 .eslintrc.json

```json
{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint", "import"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:import/typescript",
    "prettier"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/explicit-function-return-type": "warn",
    "import/order": [
      "error",
      {
        "groups": [
          "builtin",
          "external",
          "internal",
          "parent",
          "sibling",
          "index"
        ],
        "newlines-between": "always",
        "alphabetize": { "order": "asc" }
      }
    ]
  }
}
```

### A.4 .prettierrc

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "arrowParens": "avoid"
}
```

---

## 附录 B: 开发工作流

### B.1 初始化项目

```bash
# 1. 创建项目目录
mkdir lucidpanda && cd lucidpanda

# 2. 初始化 pnpm
pnpm init

# 3. 创建工作区配置
cat > pnpm-workspace.yaml << EOF
packages:
  - 'packages/*'
  - 'apps/*'
  - 'extensions/*'
EOF

# 4. 创建目录结构
mkdir -p packages/{gateway,ai-engine,quant-engine,shared-types,utils}
mkdir -p apps/{web,api,ios}
mkdir -p extensions/{bloomberg,reuters}
mkdir -p skills/{technical-analysis,news-sentiment}
mkdir -p tools/{scripts,generators}

# 5. 安装全局依赖
pnpm add -D -w typescript @types/node vitest eslint prettier tsx

# 6. 初始化 Git
git init
echo "node_modules" > .gitignore
echo "dist" >> .gitignore
echo ".env" >> .gitignore
```

### B.2 创建新包

```bash
# 创建新包
mkdir -p packages/my-package/src
cd packages/my-package

# 初始化 package.json
cat > package.json << EOF
{
  "name": "@lucidpanda/my-package",
  "version": "1.0.0",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsup src/index.ts --format cjs,esm --dts",
    "test": "vitest"
  },
  "devDependencies": {
    "tsup": "^8.0.0"
  }
}
EOF

# 创建入口文件
cat > src/index.ts << EOF
export function hello() {
  return 'Hello from my-package';
}
EOF
```

### B.3 日常开发

```bash
# 启动开发模式（所有包并行）
pnpm dev

# 只启动特定包
pnpm --filter @lucidpanda/web dev
pnpm --filter @lucidpanda/gateway dev

# 构建所有包
pnpm build

# 运行测试
pnpm test

# 类型检查
pnpm typecheck

# 代码格式化
pnpm format

# Lint 检查
pnpm lint

# 生成 Swift 类型
pnpm generate:swift-types

# iOS 项目设置
pnpm ios:setup
```

### B.4 Git 工作流

```bash
# 创建功能分支
git checkout -b feat/add-sentiment-analysis

# 提交代码（会自动触发 pre-commit hooks）
git add .
git commit -m "feat(ai-engine): add sentiment analysis for news"

# 推送到远程
git push origin feat/add-sentiment-analysis

# 创建 Pull Request
# CI/CD 会自动运行测试和构建
```

---

## 总结

LucidPanda 的架构设计核心原则：

1. **简单 > 复杂**: pnpm workspaces 而非 Nx/Turborepo
2. **本地优先**: Gateway 控制平面模式
3. **AI 友好**: 简单的项目结构，便于 AI 理解和生成代码
4. **混合 Monorepo**: TypeScript + Swift 在同一仓库
5. **按需加载**: Skills 机制避免上下文污染
6. **类型安全**: 自动生成 TypeScript → Swift 类型

**参考项目**: OpenClaw (310k stars) 提供了经过验证的最佳实践

**下一步**:
- [ ] 搭建基础 Monorepo 结构
- [ ] 实现 Gateway WebSocket 服务器
- [ ] 配置 iOS XcodeGen
- [ ] 设置类型生成脚本
- [ ] 配置 CI/CD 流程

---

**文档维护**: 请随着项目演进持续更新本文档
**反馈**: 欢迎团队成员提出改进建议
