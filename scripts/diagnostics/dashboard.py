import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from src.alphasignal.config import settings

# 页面配置
st.set_page_config(
    page_title="海湖庄园菠萝指数 (Pineapple Index)",
    page_icon="🍍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 样式 CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .bullish { color: #00ff00; font-weight: bold; }
    .bearish { color: #ff0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --------------------------
# 数据加载函数
# --------------------------
@st.cache_data(ttl=300)  # 缓存 5 分钟
def load_market_data(period="1mo", interval="1h"):
    """加载黄金行情数据 (GC=F)"""
    ticker = yf.Ticker("GC=F")
    df = ticker.history(period=period, interval=interval)
    return df

def load_intelligence():
    """从数据库加载情报记录"""
    conn = sqlite3.connect(settings.DB_PATH)
    query = "SELECT * FROM intelligence ORDER BY timestamp DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # 转换时间戳并统一为 UTC
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # 假设数据库存的是 UTC (SQLite DEFAULT CURRENT_TIMESTAMP 是 UTC)
    if df['timestamp'].dt.tz is None:
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
    else:
        df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
        
    return df

# --------------------------
# 主界面逻辑
# --------------------------

st.title("🍍 海湖庄园菠萝指数 (AlphaSignal Dashboard)")
st.caption(f"当前 AI 模型: {settings.GEMINI_MODEL} | 数据库: {settings.DB_PATH}")

# 1. 顶部指标栏
col1, col2, col3, col4 = st.columns(4)
market_data = load_market_data(period="5d", interval="15m")
# 统一时区为 UTC
market_data.index = market_data.index.tz_convert('UTC')

current_price = market_data['Close'].iloc[-1]
price_change = current_price - market_data['Close'].iloc[-2]

with col1:
    st.metric("黄金实时价格 (GC=F)", f"${current_price:.2f}", f"{price_change:.2f}")

# 加载情报数据
intel_df = load_intelligence()
total_alerts = len(intel_df)
high_urgency = len(intel_df[intel_df['urgency_score'] >= 8])

with col2:
    st.metric("总情报数", total_alerts)
with col3:
    st.metric("红色警报 (Urgency >= 8)", high_urgency, delta_color="inverse")

# 2. 核心图表区域
st.subheader("📊 特朗普言论 vs 黄金走势回测")

# 图表控件
chart_col1, chart_col2 = st.columns([1, 3])
with chart_col1:
    time_range = st.selectbox("时间范围", ["7d", "1mo", "3mo", "ytd"], index=1)
    chart_interval = st.selectbox("K线周期", ["15m", "30m", "1h", "1d"], index=2)

# 处理图表数据
df_chart = load_market_data(period=time_range, interval=chart_interval)
df_chart.index = df_chart.index.tz_convert('UTC') # 关键修复：统一为 UTC

# 创建 Plotly 图表
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, subplot_titles=('Price & Sentiment Events', 'Volume'), 
                    row_width=[0.2, 0.7])

# K线图
fig.add_trace(go.Candlestick(
    x=df_chart.index,
    open=df_chart['Open'],
    high=df_chart['High'],
    low=df_chart['Low'],
    close=df_chart['Close'],
    name='Gold'
), row=1, col=1)

# 标记情报事件 (菠萝)
# 将情报映射到最近的时间点
if not intel_df.empty:
    for idx, row in intel_df.iterrows():
        # 判断颜色
        sentiment = row['sentiment']
        color = "gray"
        symbol = "triangle-up"
        
        # 简单的情绪关键词判断 (实际项目中可以用 urgency_score 辅助)
        if any(w in str(sentiment) for w in ["鹰", "利空", "下跌", "风险", "Bearish"]):
            color = "red"
            symbol = "triangle-down"
        elif any(w in str(sentiment) for w in ["鸽", "利多", "上涨", "Bullish"]):
            color = "green"
            symbol = "triangle-up"
        
        # 找到最接近的时间点价格
        # 注意：这里做了一个简单的近似，将事件标记在发生时间的价格上
        event_time = row['timestamp']
        if event_time > df_chart.index[0] and event_time < df_chart.index[-1]:
             # 在图表上添加标记
             fig.add_annotation(
                x=event_time,
                y=row['gold_price_snapshot'] if row['gold_price_snapshot'] else current_price,
                text="🍍",
                showarrow=True,
                arrowhead=1,
                arrowcolor=color,
                hovertext=f"<b>{row['summary']}</b><br>Score: {row['urgency_score']}<br>{row['sentiment']}"
            )

# 成交量
fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], showlegend=False), row=2, col=1)

fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig, width='stretch')

# 3. 底部详细数据表
st.subheader("📝 情报详细记录")
st.dataframe(
    intel_df[['timestamp', 'urgency_score', 'sentiment', 'summary', 'gold_price_snapshot', 'url']],
    width='stretch',
    column_config={
        "url": st.column_config.LinkColumn("原文链接")
    }
)
