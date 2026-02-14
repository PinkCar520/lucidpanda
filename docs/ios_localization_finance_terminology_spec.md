# iOS Internationalization and Financial Terminology Spec

## 1. Objective
- Standardize iOS product language to institutional finance wording.
- Implement full i18n for iOS UI text (`zh-CN`, `en-US` first, extensible).
- Align iOS and Web naming for backtest, intelligence, and fund analytics.

## 2. Scope
- iOS app UI strings in:
  - `/Users/caomeifengli/workspace/AlphaSignal/mobile/ios/alphaSignal/alphaSignal/MainTabView.swift`
  - `/Users/caomeifengli/workspace/AlphaSignal/mobile/ios/alphaSignal/alphaSignal/Features/Dashboard/*.swift`
  - `/Users/caomeifengli/workspace/AlphaSignal/mobile/ios/alphaSignal/alphaSignal/Features/Backtest/*.swift`
  - `/Users/caomeifengli/workspace/AlphaSignal/mobile/ios/alphaSignal/alphaSignal/Features/Funds/*.swift`
- Navigation labels, page titles, CTA buttons, empty/error states, metric labels.

## 3. Non-goals
- No backend API field rename.
- No quantitative model logic change.
- No visual redesign.

## 4. Financial Terminology Rules
- Use finance domain terms, avoid engineering slang and marketing slang.
- One concept, one canonical term (same Chinese and English everywhere).
- Metric labels must be auditable: sample size, return, risk-adjusted win rate, etc.
- Direction wording:
  - `bearish` => "看跌策略" / "Bearish Strategy"
  - `bullish` => "看涨策略" / "Bullish Strategy"

## 5. Canonical Glossary

| Domain | Canonical zh-CN | Canonical en-US | Replace |
|---|---|---|---|
| Dashboard | 市场情报总览 | Market Intelligence Overview | 战术驾驶舱 |
| Signal | 策略信号 | Strategy Signal | 信号（无上下文） |
| Connection | 实时数据状态 | Real-time Data Status | 信号同步 |
| Backtest | 策略历史回测 | Strategy Backtest | 策略仿真回测 |
| Backtest Action | 运行回测 | Run Backtest | 开始回测重算 |
| Window | 回测窗口 | Backtest Window | 预测窗口 |
| Score Filter | 最低信号强度 | Minimum Signal Score | 最低紧迫评分 |
| Win Rate | 风险调整胜率 | Risk-adjusted Win Rate | 修正胜率 |
| Count | 样本数 | Sample Size | 样本量 |
| Evidence | 交易样本明细 | Trade Sample Details | 回测证据 |
| Fund Home | 基金组合 | Fund Watchlist | 我的 ALPHA 基金 |
| Fund Discovery | 基金检索 | Fund Discovery | 资产探索 |

## 6. i18n Key Naming Standard
- Pattern: `module.section.item`
- Modules:
  - `app`, `dashboard`, `backtest`, `funds`, `common`, `error`
- Examples:
  - `app.tab.intelligence`
  - `backtest.metric.risk_adjusted_win_rate`
  - `funds.empty.watchlist_title`

## 7. Initial Key Set (Phase 1)

### 7.1 App / Navigation
| key | zh-CN | en-US |
|---|---|---|
| `app.tab.intelligence` | 市场情报 | Intelligence |
| `app.tab.funds` | 基金组合 | Funds |
| `app.tab.backtest` | 策略回测 | Backtest |
| `app.tab.search` | 搜索 | Search |
| `app.search.fund_prompt` | 搜索基金代码或名称 | Search fund code or name |

### 7.2 Dashboard
| key | zh-CN | en-US |
|---|---|---|
| `dashboard.title` | 市场情报总览 | Market Intelligence Overview |
| `dashboard.realtime_status` | 实时数据状态: %@ | Real-time Data Status: %@ |
| `dashboard.loading_feed` | 正在加载市场情报数据... | Loading market intelligence feed... |
| `dashboard.empty.no_match` | 未找到匹配的市场情报 | No matching intelligence found |
| `dashboard.search.placeholder` | 搜索市场情报关键词... | Search intelligence keywords... |
| `dashboard.filter.all` | 全部 | All |
| `dashboard.filter.score8` | 评分 8+ | Score 8+ |
| `dashboard.filter.bearish` | 看跌策略 | Bearish Strategy |

### 7.3 Backtest
| key | zh-CN | en-US |
|---|---|---|
| `backtest.title` | 策略历史回测 | Strategy Backtest |
| `backtest.subtitle` | 基于历史样本的策略绩效评估 | Strategy performance analytics based on historical samples |
| `backtest.metric.min_score` | 最低信号强度: %d | Minimum Signal Score: %d |
| `backtest.metric.window` | 回测窗口 | Backtest Window |
| `backtest.metric.sentiment` | 策略方向 | Strategy Direction |
| `backtest.direction.bearish` | 看跌策略 | Bearish Strategy |
| `backtest.direction.bullish` | 看涨策略 | Bullish Strategy |
| `backtest.action.run` | 运行回测 | Run Backtest |
| `backtest.metric.sample_size` | 样本数 | Sample Size |
| `backtest.metric.risk_adjusted_win_rate` | 风险调整胜率 | Risk-adjusted Win Rate |
| `backtest.metric.avg_return` | 平均收益率 | Average Return |
| `backtest.section.session_distribution` | 市场时段胜率分布 | Session Win Rate Distribution |
| `backtest.section.session_breakdown` | 市场时段可靠性细分 | Session Reliability Breakdown |
| `backtest.section.environment` | 宏观环境分层分析 | Macro Regime Analysis |
| `backtest.section.distribution` | 收益率分布 | Return Distribution |
| `backtest.section.evidence` | 交易样本明细 | Trade Sample Details |
| `backtest.state.insufficient_sample` | 样本不足 | Insufficient sample |
| `backtest.state.no_data` | 当前筛选条件下无有效样本 | No eligible samples under current filters |
| `backtest.state.no_data_hint` | 建议降低最低信号强度或切换策略方向 | Lower score threshold or switch strategy direction |
| `backtest.detail.title` | 回测样本详情 | Backtest Sample Detail |
| `backtest.detail.view_full_intelligence` | 查看完整情报分析 | View Full Intelligence |
| `backtest.common.close` | 关闭 | Close |

### 7.4 Funds
| key | zh-CN | en-US |
|---|---|---|
| `funds.title` | 基金组合 | Fund Watchlist |
| `funds.subtitle` | 持仓穿透与估值分析 | Holdings-through and valuation analytics |
| `funds.empty.title` | 自选基金为空 | Watchlist is empty |
| `funds.empty.hint` | 前往“搜索”添加基金 | Go to Search to add funds |
| `funds.search.title` | 基金检索 | Fund Search |
| `funds.search.not_found` | 未找到匹配基金 | No matching funds found |
| `funds.detail.report` | 估值分析报告 | Valuation Analysis Report |
| `funds.detail.sector_weight` | 行业权重分布 | Sector Allocation |
| `funds.detail.holdings_lookthrough` | 持仓穿透分析 | Holdings Look-through |
| `funds.detail.reconciliation` | 历史估值对账 | Historical Valuation Reconciliation |

### 7.5 Common / Error
| key | zh-CN | en-US |
|---|---|---|
| `common.close` | 关闭 | Close |
| `common.loading` | 加载中... | Loading... |
| `error.network.generic` | 数据加载失败，请稍后重试 | Failed to load data. Please try again later |

## 8. Implementation Plan
1. Create iOS localization resources (`Localizable.xcstrings`).
2. Replace hardcoded strings in `MainTabView`, `Dashboard`, `Backtest`, `Funds`.
3. Add string format placeholders for dynamic values (`%@`, `%d`).
4. Add UI review checklist:
   - no truncation
   - placeholder interpolation correct
   - terminology consistency
5. Add PR gate: no new hardcoded user-facing strings.

## 9. Acceptance Criteria
- No hardcoded user-facing Chinese/English in scoped files.
- Backtest vocabulary matches glossary.
- Language switch between `zh-CN` and `en-US` is complete and stable.
- Same concept uses same key and wording across modules.
