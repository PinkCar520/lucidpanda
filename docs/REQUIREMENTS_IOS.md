# AlphaSignal iOS App 需求与系统设计文档 (2026版)

## 1. 项目愿景
AlphaSignal 移动端旨在为专业投资者提供一个具备“液态玻璃 (Liquid Glass)”高度沉浸感的地缘政治情报终端。它不仅是 Web 端的延伸，更是深度集成 Apple Intelligence 的主动式预警工具。

## 2. 核心视觉规范 (Liquid Glass Design System)
不同于传统的半透明设计，2026 年的 Liquid Glass 风格强调物理真实感与动态响应。

### 2.1 材质与光影
*   **基础材质**：采用 `.ultraThinMaterial`，配合 5% 强度的噪点纹理 (Noise Texture) 模拟真实玻璃物理质感。
*   **物理折射 (Refraction)**：UI 组件需监听 CoreMotion（陀螺仪）数据，根据设备倾斜角度微调背景模糊偏移，模拟光线穿过玻璃的折射效果。
*   **边缘高光 (Rim Light)**：卡片边缘应用动态渐变描边，随环境光或设备位移产生流动感。

### 2.2 动态色彩
*   **情绪流背景 (Sentiment Mesh)**：全局背景使用 `MeshGradient` (iOS 18+ API)，色彩随市场紧迫度 (Urgency Score) 实时流动。
    *   *高风险*：暗红与深紫交织。
    *   *稳定*：深蓝与靛青流动。

---

## 3. 技术架构 (Technical Architecture)

### 3.1 核心选型
*   **语言与并发**：Swift 6 (强制开启 Strict Concurrency)，全面采用 Actor 隔离副作用。
*   **UI 框架**：SwiftUI 6.0 (iOS 19+)。
*   **状态管理**：`@Observable` 宏 + MVVM-I (Intent) 架构。
*   **数据持久化**：SwiftData (v3) 负责情报缓存，Keychain 负责安全凭证。
*   **网络通信**：
    *   **REST**: 基于 Actor 的 `APIClient`，支持自动 401 拦截与 Token 刷新。
    *   **Live Stream**: 原生 SSE (Server-Sent Events) 订阅引擎。

### 3.2 模块化策略 (SPM)
项目采用 Monorepo 结构，内部划分为以下独立模块：
*   `AlphaCore`: 基础工具、网络引擎、日志系统。
*   `AlphaDesign`: Liquid Glass UI 组件库。
*   `AlphaData`: SwiftData 模型与 Keychain 管理。
*   `FeatureAuth`: 登录、身份验证、2FA 逻辑。
*   `FeatureIntelligence`: 实时情报流与 AI 摘要。

---

## 4. 功能需求 (Functional Requirements)

### 4.1 身份验证与安全 (Auth & Security)
*   **动态登录终端**：液态玻璃态输入界面，支持 FaceID 快速登录。
*   **安全弹窗系统**：修改密码、绑定手机、邮箱更新均采用 **Radix-style Dialog**（模态弹窗）实现，降低认知负荷。
*   **2FA 模块**：内置身份验证器支持，扫码后自动生成 6 位动态码。

### 4.2 实时战术驾驶舱 (Tactical Cockpit)
*   **实时情报流**：通过 SSE 订阅，新情报以“水滴入液”动画效果置顶。
*   **AI 智能摘要**：长按情报卡片，调用系统级 Apple Intelligence 进行核心观点提取。
*   **交互式图表**：利用 Swift Charts 渲染高性能金价曲线，支持 Haptic Feedback 触感查阅。

### 4.3 AI Intents 集成
*   **Siri 交互**：支持通过 Siri 执行“查看当前黄金风险评分”等 Intent。
*   **实时活动 (Live Activities)**：在锁屏界面展示评分 8+ 的极度紧迫情报。

---

## 5. 开发计划 (Development Roadmap)

### Sprint 1: 架构基建与安全中心 (Week 1-2)
*   [x] 搭建 Monorepo 下的 `mobile/ios` SPM 模块化结构。
*   [x] 实现基于 Actor 的 `APIClient` 与 `KeychainManager`。
*   [x] 开发 **Liquid Glass 设计系统**：封装 `LiquidBackground` 与 `GlassCard`。
*   [x] **交付物**：具备液态视觉效果的登录页，跑通后端登录接口。

### Sprint 2: 实时数据与存储层 (Week 3-4)
*   [x] 实现 `SSEResolver`：支持 AsyncStream 解析后端推送。
*   [x] 配置 `SwiftData` 容器，实现情报的本地二级缓存。
*   [x] 实现 `matchedGeometryEffect` 情报进入动画。
*   [x] **交付物**：可实时更新的战术仪表盘首页。

### Sprint 3: 专业交易分析与图表 (Week 5-6)
*   [x] 开发基于 `Swift Charts` 的专业行情视图。
*   [x] 集成 Apple Intelligence 写作工具 API 进行情报翻译与摘要。
*   [ ] 适配 iPadOS 的多窗体与横屏交易模式。
*   [x] **交付物**：全功能分析详情页。

### Sprint 4: 基金精算与全功能导航 (Week 7-8)
*   [x] 实现 `AlphaFunds` 实时估算模块：包含持仓归因与行业分布。
*   [x] 升级全局 `MainTabView`：实现液态悬浮导航栏。
*   [x] 完善“个人中心”与“安全设置”的移动端适配。
*   [x] **交付物**：全功能 AlphaSignal 移动终端。

### Sprint 5: 系统集成与优化 (Final Sprint)
*   [ ] 完善 App Intents：支持 Siri 询问“当前市场风险状态”。
*   [ ] 整体性能优化与低功耗调优。
*   [ ] **交付物**：App Store 发布版本 (Release Candidate)。

---

## 6. 验收标准 (DoD)
*   **性能**：主线程始终保持 60 FPS (ProMotion 120 FPS)。
*   **安全**：所有敏感数据（Token、Secret）严禁落盘 UserDefaults，必须进入 Keychain。
*   **容错**：SSE 具备指数退避重连机制，API 401 自动引导至登录页。
*   **交互**：所有操作需具备 Taptic Engine 触感反馈同步。
