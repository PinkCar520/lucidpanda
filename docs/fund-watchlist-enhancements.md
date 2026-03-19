# 基金关注列表功能增强

## 新增功能

### 1. 关注列表实时排序 📊

#### 功能描述
关注列表现在会根据**当日实时涨跌幅**自动排序，涨幅最高的基金排在最前面。

#### 实现细节

**排序规则**:
- 按 `estimated_growth`（估值涨跌幅）**降序排列**
- 涨幅高的基金排在前面
- 跌幅大的基金排在后面
- 没有涨跌幅数据的基金排在最后

**数据来源**:
- 每次获取基金估值时，自动更新该基金的 `estimated_growth`
- 利用客户端缓存机制，避免重复请求
- 组件加载时预加载所有关注列表基金的数据

**UI 展示**:
```
永赢科技智选混合C          +2.35%  ← 涨幅最高
南方中证半导体C            -0.87%  ← 跌幅
基金名称                   (无数据) ← 未加载
```

#### 技术实现

1. **扩展数据结构**:
```typescript
interface WatchlistItem {
    code: string;
    name: string;
    estimated_growth?: number; // 新增：用于排序
}
```

2. **排序逻辑**:
```typescript
watchlist
    .slice() // 创建副本，避免直接修改 state
    .sort((a, b) => {
        // 无数据的排在最后
        if (a.estimated_growth === undefined && b.estimated_growth === undefined) return 0;
        if (a.estimated_growth === undefined) return 1;
        if (b.estimated_growth === undefined) return -1;
        // 降序排列
        return b.estimated_growth - a.estimated_growth;
    })
```

3. **数据更新**:
```typescript
// 获取估值数据后，自动更新关注列表
setWatchlist(prev => prev.map(item =>
    item.code === code ? { ...item, estimated_growth: data.estimated_growth } : item
));
```

4. **预加载机制**:
```typescript
// 组件加载 1 秒后，后台预加载所有基金数据
useEffect(() => {
    const preloadWatchlist = async () => {
        for (const item of watchlist) {
            await fetchValuation(item.code);
            await new Promise(resolve => setTimeout(resolve, 200)); // 避免并发过多
        }
    };
    const timer = setTimeout(preloadWatchlist, 1000);
    return () => clearTimeout(timer);
}, []);
```

#### 用户体验

- ✅ **自动排序**: 无需手动操作，列表自动按涨跌幅排序
- ✅ **实时更新**: 每次刷新数据后，排序自动更新
- ✅ **视觉清晰**: 涨跌幅用颜色区分（红涨绿跌，符合 A 股习惯）
- ✅ **智能预加载**: 后台自动加载数据，不影响当前操作

---

### 2. 刷新按钮动画优化 🔄

#### 功能描述
点击刷新按钮后，按钮会显示**旋转动画**，让用户清楚地感知到刷新操作正在进行。

#### 实现细节

**动画效果**:
- 点击刷新按钮后，图标开始旋转
- 旋转动画持续至少 **600ms**
- 即使数据加载很快，也会保持最小动画时长
- 动画结束后自动停止

**状态管理**:
```typescript
const [refreshing, setRefreshing] = useState(false);
```

**刷新逻辑**:
```typescript
const handleManualRefresh = async () => {
    if (selectedFund && !refreshing) {
        setRefreshing(true); // 开始动画
        
        // 清除缓存并重新获取数据
        setValuationCache(prev => {
            const newCache = new Map(prev);
            newCache.delete(selectedFund);
            return newCache;
        });
        
        await fetchValuation(selectedFund);
        
        // 保持至少 600ms 的动画，提供更好的视觉反馈
        setTimeout(() => {
            setRefreshing(false); // 结束动画
        }, 600);
    }
};
```

**UI 实现**:
```tsx
<button
    onClick={handleManualRefresh}
    disabled={loading || refreshing}
    className="p-2 hover:bg-white/10 rounded-full transition-colors disabled:opacity-50"
>
    <RefreshCw className={`w-4 h-4 text-slate-400 transition-transform ${refreshing ? 'animate-spin' : ''}`} />
</button>
```

#### 用户体验改进

**优化前**:
- ❌ 点击刷新按钮后，如果数据加载很快，用户可能感觉不到任何变化
- ❌ 不确定是否真的刷新了

**优化后**:
- ✅ 点击后立即看到旋转动画
- ✅ 动画持续至少 600ms，确保用户有明确的视觉反馈
- ✅ 按钮在刷新期间禁用，防止重复点击
- ✅ 动画流畅，提升操作体验

#### 技术亮点

1. **最小动画时长**: 即使 API 响应很快（如命中缓存），也保持 600ms 动画
2. **防抖处理**: 刷新期间禁用按钮，避免重复请求
3. **平滑过渡**: 使用 `transition-transform` 实现流畅的动画效果
4. **独立状态**: `refreshing` 状态独立于 `loading`，互不干扰

---

## 整体优化效果

### 性能指标

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 关注列表排序 | ❌ 无排序 | ✅ 自动按涨跌幅排序 |
| 涨跌幅显示 | ❌ 不显示 | ✅ 实时显示 |
| 刷新反馈 | ❌ 无明显反馈 | ✅ 600ms 旋转动画 |
| 数据预加载 | ❌ 手动切换才加载 | ✅ 后台自动预加载 |

### 用户价值

1. **快速决策**: 一眼看出哪些基金涨幅最高
2. **操作确认**: 刷新动画提供明确的操作反馈
3. **无感体验**: 预加载机制让切换更流畅
4. **视觉友好**: 颜色编码（红涨绿跌）符合 A 股习惯

---

## 使用示例

### 场景 1: 查看关注列表
1. 打开基金页面
2. 关注列表自动按涨跌幅排序
3. 涨幅最高的基金排在最前面
4. 每个基金旁边显示实时涨跌幅

### 场景 2: 手动刷新数据
1. 点击右上角的刷新按钮
2. 按钮开始旋转（至少 600ms）
3. 数据更新完成
4. 动画停止，显示最新数据

### 场景 3: 添加新基金
1. 在输入框输入基金代码
2. 按 Enter 添加到关注列表
3. 后台自动获取该基金的估值数据
4. 列表自动重新排序

---

## 技术细节

### 文件修改
- **文件**: `web/app/[locale]/funds/page.tsx`
- **修改内容**:
  1. 扩展 `WatchlistItem` 接口
  2. 添加 `refreshing` 状态
  3. 实现排序逻辑
  4. 添加预加载机制
  5. 优化刷新按钮动画

### 代码统计
- 新增代码: ~80 行
- 修改代码: ~30 行
- 删除代码: ~10 行

### 兼容性
- ✅ 向后兼容：旧数据（无 `estimated_growth`）会排在最后
- ✅ 性能优化：使用 `slice()` 避免直接修改 state
- ✅ 错误处理：预加载失败不影响主流程

---

## 后续优化建议

1. **排序选项**: 添加手动排序选项（按名称、按代码、按涨跌幅）
2. **涨跌幅趋势**: 显示涨跌幅变化趋势（↑↓箭头）
3. **批量刷新**: 添加"刷新全部"按钮，一键更新所有基金
4. **持久化排序**: 记住用户的排序偏好
5. **动画配置**: 允许用户关闭动画（无障碍考虑）
