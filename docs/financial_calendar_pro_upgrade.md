# 财经日历（Financial Calendar）专业级升级规划 v3

> 更新时间：2026-03-11 ｜ 当前版本：P1-P3 已完成，P4+ 专业级规划中

---

## 一、现状评估与差距分析

目前的财经日历已实现基础的 P0-P3 功能（实时抓取、自选联动、折叠交互），但距离 **生产级别（Production Grade）** 的金融产品仍存在以下关键差距：

| 维度 | 现状 (P3) | 专业标准 (Pro) | 差距 |
|------|-----------|----------------|------|
| **数据确定性** | 仅日期，无具体时段 | 必须区分 **盘前 (BMO)** / **盘后 (AMC)** | 核心交易决策缺失 |
| **宏观时效** | 文本描述三值（前/预/公） | 结构化对比 + 趋势图表 | 信息密度不足 |
| **交互闭环** | 仅查看，无跳转 | 深度联动 (Deep Linking) 至个股详情 | 漏斗转化断裂 |
| **时间严谨性** | 本地日期逻辑 | 严格 **业务日期 (Business Date)** 与时区对齐 | 跨时区显示易错位 |

---

## 二、V4 专业级升级路线图 (Roadmap)

### P4：数据模型与协议增强（优先级：🔴 高）
- **Schema 扩展**：DTO 增加 `period` (Enum) 和 `macro_details` (JSON)。
- **时区对齐**：统一后端返回 UTC 时间戳，前端根据交易所所在地进行二次转换。

### P5：深度交互与智能推送（优先级：🟠 中）
- **Deep Linking**：日历事件点击直接跳转至 `FundDetailView`。
- **系统订阅**：支持导出 ICS 文件，将重要财报/宏观事件同步至 iOS 系统日历。
- **智能提醒**：重大事件（High Impact）前 15 分钟触发本地推送。

### P6：数据源权威化（优先级：⚪ 低）
- **多源加权**：引入官方公告抓取或付费 API，解决 yfinance 偶尔的日期偏差。

---

## 三、V4 详细需求（Codex 实施规范）

### 1. 后端模型扩展 (Backend)

**文件**：`src/alphasignal/api/v1/routers/calendar.py`

```python
class EventPeriod(str, Enum):
    PRE_MARKET = "pre_market"   # 盘前 (BMO)
    DURING_MARKET = "during"    # 盘中
    AFTER_HOURS = "after_hours" # 盘后 (AMC)
    UNKNOWN = "unknown"

class MacroDetails(BaseModel):
    actual: Optional[float]
    forecast: Optional[float]
    previous: Optional[float]
    unit: Optional[str]

class CalendarEventSchema(BaseModel):
    # ... 现有字段 ...
    period: EventPeriod = EventPeriod.UNKNOWN
    macro_details: Optional[MacroDetails] = None
    is_official_source: bool = False # 标识是否为官方公告抓取
```

### 2. iOS UI/UX 深度升级 (Frontend)

#### A. 增加“盘前/盘后”标签
在 `CalendarEventCard` 和 `FundCompactCard` 的 Badge 中增加时段标识：
- ` earnings (BMO)` -> 蓝色
- ` earnings (AMC)` -> 紫色

#### B. 宏观数据可视化条 (Macro Visual Bar)
针对 CPI、Non-farm 等高影响数据，UI 渲染对比条：
```
[ 前值: 3.1% ] ---- [ 预期: 3.0% ] ---- [● 公布: 2.9% ]
( 颜色根据利好/利空自动判定：公布 < 预期 = 绿色 )
```

#### C. 深度联动路由
修改 `CalendarViewModel`：
```swift
func handleEventTap(_ event: CalendarEvent) {
    if let symbol = event.relatedSymbols.first {
        // 触发全局路由跳转至 FundDetailView(symbol: symbol)
    }
}
```

---

## 四、技术难点与对策

### 1. yfinance 盘前/盘后数据提取
- **问题**：`yfinance` 免费接口不直接提供 `period` 字段。
- **对策**：尝试解析 `ticker.calendar` 返回的列表顺序，或辅助抓取 `earnings_date` 的预估时间点字符串。

### 2. 跨时区“今日事件”一致性
- **场景**：北京时间周一晚上 22:00 查看日历，美股周一（今日）事件必须显示在最前。
- **对策**：UI 层使用 `Calendar.current` 结合 `TimeZone(identifier: "America/New_York")` 进行业务逻辑判定。

---

## 五、验收标准 (V4)

1. **确定性**：自选股财报事件 80% 以上具备“盘前/盘后”标签。
2. **便捷性**：从日历点击个股事件跳转至详情页的成功率 100%。
3. **直观性**：宏观事件不再只是“一大段话”，具备清晰的三值对比 UI。
4. **性能**：日历展开动画保持 60fps，缓存加载耗时 < 100ms。
