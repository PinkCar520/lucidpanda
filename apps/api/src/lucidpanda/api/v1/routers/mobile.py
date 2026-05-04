import json
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlmodel import Session, col, select, text
from starlette.concurrency import run_in_threadpool

from src.lucidpanda.auth.dependencies import get_current_user, get_current_pro_user
from src.lucidpanda.auth.models import User
from src.lucidpanda.infra.cache import get_cached, set_cached
from src.lucidpanda.infra.database.connection import get_session
from src.lucidpanda.models.intelligence import Intelligence, IntelligenceMobileRead
from src.lucidpanda.models.macro_event import MacroEvent
from src.lucidpanda.services.market_terminal_service import market_terminal_service
from src.lucidpanda.core.logger import logger
from src.lucidpanda.utils import v1_prepare_json, format_iso8601
from src.lucidpanda.utils.entity_normalizer import translate_fund_name
from src.lucidpanda.utils.confidence import calc_confidence_level, calc_confidence_score
from src.lucidpanda.utils.market_calendar import get_market_status
from src.lucidpanda.providers.llm.deepseek import DeepSeekLLM
from src.lucidpanda.prompts.timechain_v1 import TIMECHAIN_SYSTEM_PROMPT, TIMECHAIN_USER_PROMPT_TEMPLATE

router = APIRouter()


@router.get("/intelligence/{item_id}/ai_summary", response_model=dict[str, str])
async def get_mobile_intelligence_ai_summary(
    item_id: int,
    accept_language: str | None = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_session),
):
    """
    Fetch AI summary/actionable advice for a specific intelligence item.
    Supports multi-language content based on Accept-Language header.
    """
    statement = select(Intelligence).where(Intelligence.id == item_id)
    result = db.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")

    # Determine language preference
    lang = "zh"
    if accept_language and ("en" in accept_language.lower() or "us" in accept_language.lower()):
        lang = "en"

    alt_lang = "en" if lang == "zh" else "zh"
    advice_text = "目前没有针对该情报的深度AI分析策略。" if lang == "zh" else "No AI analysis available for this item."

    if isinstance(result.actionable_advice, dict):
        advice_text = (
            result.actionable_advice.get(lang)
            or result.actionable_advice.get(alt_lang)
            or advice_text
        )
    elif isinstance(result.actionable_advice, str) and result.actionable_advice.strip():
        advice_text = result.actionable_advice

    return v1_prepare_json({"ai_summary": advice_text})


@router.get("/dashboard/summary", response_model=dict[str, Any])
async def get_mobile_dashboard_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_session)
):
    """
    Production-grade Aggregated Endpoint for Mobile.
    Reduces RTT by combining watchlist, market status, and top alerts.
    """
    return v1_prepare_json(
        {
            "market_status": get_market_status("CN"),
            "watchlist": [],  # List[FundMobileSummary]
            "critical_alerts": [],  # List[IntelligenceMobileRead]
        }
    )


@router.get("/intelligence", response_model=list[IntelligenceMobileRead])
async def get_mobile_intelligence(
    category: str | None = Query(None, description="Optional category filter (e.g. macro_gold)"),
    limit: int = Query(20, ge=1, le=100, description="Max number of items to return"),
    accept_language: str | None = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_session)
):
    """
    Trimmed intelligence feed for mobile.
    Only returns essential fields to save bandwidth.
    Supports multi-language content selection based on user preference.
    """
    lang = "zh"
    if accept_language and ("en" in accept_language.lower() or "us" in accept_language.lower()):
        lang = "en"

    statement = (
        select(Intelligence)
        .where(Intelligence.status == "COMPLETED")
        .where(col(Intelligence.summary).is_not(None))
    )
    
    if category:
        statement = statement.where(Intelligence.category == category)
        
    statement = statement.order_by(col(Intelligence.timestamp).desc()).limit(limit)
    results = db.exec(statement).all()

    # Transformation logic from rich JSONB to flat mobile string
    mobile_items = []
    for item in results:
        # Priority language selection
        alt_lang = "en" if lang == "zh" else "zh"
        
        summary_text = "无摘要"
        if isinstance(item.summary, dict):
            summary_text = (
                item.summary.get(lang)
                or item.summary.get(alt_lang)
                or next(
                    (
                        v
                        for v in item.summary.values()
                        if isinstance(v, str) and v.strip()
                    ),
                    "无摘要",
                )
            )
        elif isinstance(item.summary, str) and item.summary.strip():
            summary_text = item.summary

        urgency_score = item.urgency_score if isinstance(item.urgency_score, int) else 0
        timestamp = item.timestamp or datetime.now(UTC)

        sentiment_label = "Neutral"
        if isinstance(item.sentiment, dict):
            sentiment_label = (
                item.sentiment.get(lang) or item.sentiment.get(alt_lang) or "Neutral"
            )
        elif isinstance(item.sentiment, str) and item.sentiment.strip():
            sentiment_label = item.sentiment
            
        content_text = ""
        if isinstance(item.content, dict):
            content_text = (
                item.content.get(lang)
                or item.content.get(alt_lang)
                or next(
                    (
                        v
                        for v in item.content.values()
                        if isinstance(v, str) and v.strip()
                    ),
                    "",
                )
            )
        elif isinstance(item.content, str):
            content_text = item.content

        confidence_score = calc_confidence_score(
            item.corroboration_count,
            getattr(item, "source_credibility_score", None),
            item.urgency_score,
            item.timestamp,
        )

        mobile_items.append(
            IntelligenceMobileRead(
                id=item.id,
                timestamp=timestamp,
                author=item.author or "Unknown",
                summary=str(summary_text),
                content=str(content_text),
                image_url=getattr(item, "image_url", None),
                local_image_path=getattr(item, "local_image_path", None),
                urgency_score=urgency_score,
                sentiment_label=sentiment_label,
                gold_price_snapshot=item.gold_price_snapshot,
                dxy_snapshot=item.dxy_snapshot,
                us10y_snapshot=item.us10y_snapshot,
                oil_snapshot=None,  # 如果需要可以添加
                price_15m=item.price_15m,
                price_1h=item.price_1h,
                price_4h=item.price_4h,
                price_12h=item.price_12h,
                price_24h=item.price_24h,
                corroboration_count=item.corroboration_count or 1,
                confidence_score=confidence_score,
                confidence_level=calc_confidence_level(confidence_score),
            )
        )
    return v1_prepare_json(mobile_items)


@router.get("/market/snapshot", response_model=dict[str, Any])
async def get_mobile_market_snapshot():
    """
    Fetch real-time market snapshot for iOS terminal.
    Includes: Gold, DXY, Crude Oil, US10Y Treasury.
    """
    snapshot = await run_in_threadpool(market_terminal_service.get_market_snapshot)
    if not snapshot:
        raise HTTPException(
            status_code=503, detail="Market data temporarily unavailable"
        )
    return v1_prepare_json(snapshot)


@router.get("/market/pulse", response_model=dict[str, Any])
async def get_market_pulse(
    db: Session = Depends(get_session),
):
    """
    宏观市场脉搏 — 为悬浮胶囊提供聚合数据。
    返回：多品种快照 + 近24h高紧急度情报摘要 + 整体市场情绪 + 趋势图 + 宏观事件
    缓存：15s 全局 Redis 缓存（非个人化数据）
    """
    _CACHE_KEY = "api:market:pulse"
    _CACHE_TTL = 15  # 秒

    cached = get_cached(_CACHE_KEY)
    if cached is not None:
        return cached

    # 核心脉搏计算逻辑
    pulse_data = await _calculate_market_pulse(db)
    
    set_cached(_CACHE_KEY, pulse_data, _CACHE_TTL)
    return v1_prepare_json(pulse_data)


@router.get("/market/pulse/timechain", response_model=dict[str, Any])
async def get_market_pulse_timechain(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_pro_user),
    lang: str = Query("zh", pattern="^(zh|en)$"),
):
    """
    市场脉搏 - 事件脉络分析。
    聚合过去 7 天高紧急度情报，通过 AI 生成具有因果关系的演进链条。
    """
    _CACHE_KEY = f"api:market:pulse:timechain:{lang}"
    _CACHE_TTL = 3600

    cached = get_cached(_CACHE_KEY)
    if cached is not None:
        return cached

    now_dt = datetime.now(UTC)
    since_7d = now_dt - timedelta(days=7)

    query = text("""
        SELECT id, timestamp, summary, urgency_score, sentiment_score, author
        FROM intelligence
        WHERE timestamp >= :since AND urgency_score >= 7 AND status = 'COMPLETED'
        ORDER BY timestamp ASC
    """)
    rows = db.execute(query, {"since": since_7d}).mappings().all()

    if not rows:
        return {
            "theme_title": "市场波动较小" if lang == "zh" else "Low Market Volatility",
            "ai_summary": "过去 7 天未监测到具有显著宏观影响的高紧急度事件。" if lang == "zh" else "No high-urgency macro events detected in the last 7 days.",
            "timeline": [],
            "generated_at": format_iso8601(now_dt)
        }

    items_context = ""
    for idx, row in enumerate(rows):
        summary_val = row["summary"]
        text_summary = ""
        if isinstance(summary_val, dict):
            text_summary = summary_val.get(lang) or summary_val.get("zh") or summary_val.get("en")
        else:
            text_summary = str(summary_val)
        
        ts_str = row["timestamp"].strftime("%Y-%m-%d %H:%M") if isinstance(row["timestamp"], datetime) else str(row["timestamp"])
        items_context += f"[{idx+1}] 时间: {ts_str}, 内容: {text_summary}, 紧急度: {row['urgency_score']}\n"

    try:
        llm = DeepSeekLLM()
        prompt = TIMECHAIN_USER_PROMPT_TEMPLATE.format(intelligence_items=items_context)
        full_prompt = f"{TIMECHAIN_SYSTEM_PROMPT}\n\n{prompt}"
        
        result = await llm.generate_json_async(full_prompt)
        
        result["generated_at"] = format_iso8601(now_dt)
        set_cached(_CACHE_KEY, result, _CACHE_TTL)
        return result
    except Exception as e:
        logger.error(f"Timechain AI analysis failed: {e}")
        return {
            "theme_title": "AI 分析暂时不可用" if lang == "zh" else "AI Analysis Unavailable",
            "ai_summary": "系统在尝试串联事件脉络时遇到技术问题，请稍后再试。",
            "timeline": [],
            "error": str(e),
            "generated_at": format_iso8601(now_dt)
        }


@router.get("/market/pulse/stream")
async def market_pulse_stream(
    db: Session = Depends(get_session),
):
    """
    SSE 流：实时推送市场脉搏数据 (用于 iOS 极速跳动)。
    """
    from sse_starlette.sse import EventSourceResponse
    import asyncio

    async def event_generator():
        while True:
            try:
                pulse_data = await _calculate_market_pulse(db)
                yield {
                    "data": json.dumps(v1_prepare_json(pulse_data))
                }
                # 每 10 秒推送一次，平衡性能与实时性
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Market SSE Error: {e}")
                break

    return EventSourceResponse(event_generator())


async def _calculate_market_pulse(db: Session) -> dict[str, Any]:
    """核心脉搏计算逻辑：聚合快照、情报、情绪及事件"""
    def normalize_summary_text(summary_val: Any) -> str:
        if isinstance(summary_val, dict):
            zh = summary_val.get("zh")
            en = summary_val.get("en")
            if isinstance(zh, str) and zh.strip():
                return zh
            if isinstance(en, str) and en.strip():
                return en
            for value in summary_val.values():
                if isinstance(value, str) and value.strip():
                    return value
            return "无摘要"

        if isinstance(summary_val, str):
            text_val = summary_val.strip()
            if text_val.startswith("{"):
                try:
                    parsed = json.loads(text_val)
                    return normalize_summary_text(parsed)
                except Exception:
                    return text_val or "无摘要"
            return text_val or "无摘要"

        if summary_val is None:
            return "无摘要"

        return str(summary_val)

    now_dt = datetime.now(UTC)
    since_24h = now_dt - timedelta(hours=24)

    # 2. 注入市场概况
    snapshot = await run_in_threadpool(market_terminal_service.get_market_snapshot)

    # 2. 近24h高紧急度情报 (urgency_score >= 7)
    top_alerts_raw = (
        db.execute(
            text("""
            SELECT id, timestamp, urgency_score, summary, sentiment_score
            FROM intelligence
            WHERE timestamp >= :since AND urgency_score >= 7 AND status = 'COMPLETED'
            ORDER BY timestamp DESC
            LIMIT 10
            """),
            {"since": since_24h},
        ).mappings().all()
    )
    
    top_alerts = []
    for row in top_alerts_raw:
        summary_text = normalize_summary_text(row["summary"])
        row_timestamp = row["timestamp"]
        if isinstance(row_timestamp, str):
            try:
                row_timestamp = datetime.fromisoformat(row_timestamp.replace("Z", "+00:00"))
            except ValueError:
                row_timestamp = None

        top_alerts.append({
            "id": row["id"],
            "timestamp": format_iso8601(row_timestamp),
            "urgency_score": row["urgency_score"],
            "summary": summary_text,
            "sentiment": "bullish" if row["sentiment_score"] > 0.15 else ("bearish" if row["sentiment_score"] < -0.15 else "neutral")
        })

    # 3. 汇总整体情绪
    sentiment_stats = db.execute(
        text("SELECT AVG(sentiment_score) as avg_score, COUNT(*) as total FROM intelligence WHERE timestamp >= :since AND status = 'COMPLETED'"),
        {"since": since_24h}
    ).mappings().first()
    
    avg_sentiment = sentiment_stats["avg_score"] or 0.0
    alert_count = sentiment_stats["total"] or 0

    # 4. 情绪走势 (Sparkline 支持)
    trend_raw = db.execute(
        text("""
            SELECT date_trunc('hour', timestamp) AS hour, AVG(sentiment_score) AS avg_score
            FROM intelligence
            WHERE timestamp >= :since AND status = 'COMPLETED'
            GROUP BY 1 ORDER BY 1 ASC
        """),
        {"since": since_24h},
    ).mappings().all()

    trend_map = {row["hour"]: round(float(row["avg_score"]), 3) for row in trend_raw}
    sentiment_trend = []
    start_hour = now_dt.replace(minute=0, second=0, microsecond=0) - timedelta(hours=24)
    for i in range(25):
        current_h = start_hour + timedelta(hours=i)
        sentiment_trend.append({
            "hour": format_iso8601(current_h),
            "score": trend_map.get(current_h, 0.0)
        })

    # 4.5 黄金价格走势 (仅返回真实历史数据，不再在 SSE 流中执行 AI 预测)
    history_full = await run_in_threadpool(market_terminal_service.get_gold_history_24h)
    gold_trend = history_full

    # 5. 未来 48h 宏观事件
    until_dt = now_dt + timedelta(hours=48)
    try:
        upcoming_events_raw = db.exec(
            select(MacroEvent)
            .where(col(MacroEvent.release_date) >= now_dt.date())
            .where(col(MacroEvent.release_date) <= until_dt.date())
            .where(col(MacroEvent.impact_level).in_(["high", "medium"]))
            .order_by(col(MacroEvent.release_date).asc(), col(MacroEvent.release_time).asc())
            .limit(5)
        ).all()
    except Exception as e:
        logger.error(f"Failed to fetch macro events: {e}")
        upcoming_events_raw = []

    upcoming_events = [{
        "id": str(event.id),
        "title": event.title,
        "country": event.country,
        "date": event.release_date.isoformat(),
        "time": event.release_time,
        "impact": event.impact_level,
        "forecast": event.forecast_value,
        "previous": event.previous_value,
    } for event in upcoming_events_raw]

    return {
        "market_snapshot": snapshot,
        "top_alerts": top_alerts,
        "upcoming_events": upcoming_events,
        "overall_sentiment": "bullish" if avg_sentiment > 0.15 else ("bearish" if avg_sentiment < -0.15 else "neutral"),
        "overall_sentiment_zh": "看多" if avg_sentiment > 0.15 else ("看空" if avg_sentiment < -0.15 else "中性"),
        "sentiment_score": round(avg_sentiment, 3),
        "sentiment_trend": sentiment_trend,
        "gold_trend": gold_trend,
        "alert_count_24h": alert_count,
        "generated_at": format_iso8601(datetime.now(UTC))
    }


@router.get("/gold/prediction", response_model=dict[str, Any])
async def get_gold_prediction(
    granularity: str = "1h",
    force_refresh: bool = False,
    limit: int = 20,
    db: Session = Depends(get_session),
):
    """
    Structured gold prediction data for high-fidelity chart.
    """
    # 1. Fetch History (International Gold / London Gold) with custom depth
    try:
        history_full = await run_in_threadpool(market_terminal_service.get_gold_history_intl_custom, granularity, force_refresh)
    except Exception as e:
        logger.error(f"Error fetching gold history: {e}")
        history_full = []

    if not history_full:
        # Return a shell response instead of 503 to prevent App crash/error loops
        return v1_prepare_json({
            "history": [],
            "prediction": {
                "issuedAt": format_iso8601(datetime.now(UTC)),
                "mid": [],
                "upper": [],
                "lower": []
            },
            "generatedAt": format_iso8601(datetime.now(UTC))
        })

    # 2. Determine Pivot (IssuedAt)
    # 我们以历史数据的最后一个点作为预测的起点（枢轴点），确保预测紧跟实时行情。
    if not history_full:
        return v1_prepare_json({
            "history": [],
            "prediction": {"issuedAt": format_iso8601(datetime.now(UTC)), "mid": [], "upper": [], "lower": []},
            "generatedAt": format_iso8601(datetime.now(UTC))
        })

    from src.lucidpanda.utils.market_calendar import get_market_status
    market_status = get_market_status("GOLD")

    issued_index = len(history_full) - 1
    history_training = history_full
    issued_at = history_full[issued_index]["timestamp"]
    base_price = history_full[issued_index]["price"] # 确定真实的基准价格

    # 3. Generate AI Mid Forecast with Caching
    CACHE_KEY = f"mobile:gold_forecast:intl:v2:{granularity}"
    if not force_refresh:
        cached_data = get_cached(CACHE_KEY)
        if cached_data and "generatedAt" in cached_data:
            cached_data["market_status"] = market_status
            return v1_prepare_json(cached_data)

    # Fetch snapshot and top alerts for AI context
    snapshot = await run_in_threadpool(market_terminal_service.get_market_snapshot)
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    
    # Calculate Overall Sentiment
    sentiment_stats = db.execute(
        text("SELECT AVG(sentiment_score) as avg_score FROM intelligence WHERE timestamp >= :since AND status = 'COMPLETED'"),
        {"since": since_24h}
    ).mappings().first()
    avg_score = round(sentiment_stats["avg_score"] or 0.0, 3)
    sentiment_label = "看多" if avg_score > 0.15 else ("看空" if avg_score < -0.15 else "中性")
    overall_sentiment = {"score": avg_score, "label": sentiment_label}

    top_alerts_raw = db.execute(
        text("SELECT summary, sentiment_score FROM intelligence WHERE timestamp >= :since AND urgency_score >= 7 AND status = 'COMPLETED' LIMIT 10"),
        {"since": since_24h},
    ).mappings().all()
    
    top_alerts = [{"summary": r["summary"], "sentiment": "bullish" if r["sentiment_score"] > 0.15 else "bearish"} for r in top_alerts_raw]

    # --- 增强：获取未来 24h 宏观事件 ---
    now_dt = datetime.now(UTC)
    tomorrow_dt = now_dt + timedelta(hours=24)
    macro_events_raw = db.execute(
        text("""
            SELECT title, country, release_time, forecast_value, impact_level 
            FROM macro_event 
            WHERE release_date >= :today AND release_date <= :tomorrow 
            AND impact_level IN ('high', 'medium') 
            ORDER BY release_date ASC, release_time ASC
        """),
        {"today": now_dt.date(), "tomorrow": tomorrow_dt.date()},
    ).mappings().all()
    
    macro_events_text = "\n".join([
        f"- {e['release_time']} {e['country']} {e['title']} (预期: {e['forecast_value'] or 'N/A'}, 影响: {e['impact_level']})"
        for e in macro_events_raw
    ]) or "未来24小时无重大预定事件"

    # --- 增强：获取 AI 事件脉络 (Timechain) ---
    timechain_data = get_cached("api:market:pulse:timechain:zh")
    timechain_context = {
        "theme": timechain_data.get("theme_title") if timechain_data else "多因素驱动黄金震荡",
        "summary": timechain_data.get("ai_summary") if timechain_data else "核心逻辑围绕美元走势与地缘政治溢价。"
    }

    # Call AI Forecast
    forecast_points = await _generate_gold_forecast_intl(
        history_training, 
        top_alerts, 
        snapshot, 
        overall_sentiment,
        granularity=granularity,
        macro_events_text=macro_events_text,
        timechain_context=timechain_context,
        market_status=market_status
    )
    
    if not forecast_points:
        # 如果 AI 失败或返回为空，不再生成模拟走势，直接返回空预测
        pass

    # Construct complete prediction object with upper/lower bands
    # For now, use a simple fixed volatility band
    mid_points = []
    upper_points = []
    lower_points = []
    
    for i, p in enumerate(forecast_points):
        ts = p["timestamp"]
        price = p["price"]
        mid_points.append({"timestamp": ts, "price": price})
        
        # Volatility grows with time. For 1D, we use larger spread.
        vol_base = 0.015 if granularity == "1d" else 0.005
        vol_step = 0.005 if granularity == "1d" else 0.002
        vol = vol_base + (vol_step * i) 
        upper_points.append({"timestamp": ts, "price": round(price * (1 + vol), 2)})
        lower_points.append({"timestamp": ts, "price": round(price * (1 - vol), 2)})

    prediction_result = {
        "issuedAt": issued_at,
        "mid": mid_points,
        "upper": upper_points,
        "lower": lower_points
    }
    
    final_response = {
        "history": history_full,
        "prediction": prediction_result,
        "generatedAt": format_iso8601(datetime.now(UTC)),
        "granularity": granularity, # Include granularity for frontend logic
        "market_status": market_status
    }
    
    # Cache the FULL response object, not just prediction_result
    set_cached(CACHE_KEY, final_response, 3600)

    return v1_prepare_json(final_response)


async def _generate_gold_forecast_intl(
    history: list[dict],
    alerts: list[dict],
    snapshot: dict,
    overall_sentiment: dict,
    granularity: str = "1h",
    macro_events_text: str = "",
    timechain_context: dict = None,
    market_status: str = "OPEN"
) -> list[dict]:
    """使用 LLM 综合宏观指标、情报及情绪生成伦敦金 (XAU/USD) 价格预测"""
    if not history:
        return []

    # ... (基础数据准备) ...
    last_point = history[-1]
    last_price = last_point["price"]
    try:
        raw_ts = datetime.fromisoformat(last_point["timestamp"].replace("Z", "+00:00"))
    except Exception:
        raw_ts = datetime.now(UTC)
    
    # 周期对齐逻辑：预测点应从下一个标准时间边界开始
    if granularity in ["15m", "30m", "1h", "4h"]:
        m_interval = {"15m": 15, "30m": 30, "1h": 60, "4h": 240}.get(granularity, 60)
        # 向上取整到最近的间隔
        total_minutes = raw_ts.hour * 60 + raw_ts.minute
        next_boundary_minutes = ((total_minutes // m_interval) + 1) * m_interval
        last_ts = raw_ts.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=next_boundary_minutes)
    else:
        last_ts = raw_ts
    
    recent_prices = [p["price"] for p in history[-6:]]
    trend_desc = "震荡"
    if len(recent_prices) >= 2:
        if recent_prices[-1] > recent_prices[0] * 1.001:
            trend_desc = "上涨"
        elif recent_prices[-1] < recent_prices[0] * 0.999:
            trend_desc = "下跌"
    
    # ... (宏观快照格式化) ...
    macro_context = ""
    if snapshot:
        dxy = snapshot.get("dxy", {})
        oil = snapshot.get("oil", {})
        us10y = snapshot.get("us10y", {})
        macro_context = f"""
        - 美元指数 (DXY): {dxy.get('price')} ({dxy.get('changePercent')}%)
        - WTI原油: {oil.get('price')} ({oil.get('changePercent')}%)
        - 美债 10Y 收益率: {us10y.get('price')}% ({us10y.get('changePercent')}%)
        """

    sentiment_desc = f"{overall_sentiment.get('score', 0)} ({overall_sentiment.get('label', '中性')})"

    intel_briefs = []
    for a in alerts[:10]:
        summary_val = a['summary']
        text_summary = summary_val.get("zh") if isinstance(summary_val, dict) else str(summary_val)
        intel_briefs.append(f"- {text_summary} (情绪: {a['sentiment']})")
    intel_context = "\n".join(intel_briefs) if intel_briefs else "无重大情报"

    # 5. 构建深度分析提示词
    if granularity == "1d":
        unit, count = "天", 5
        interval_min = 1440
    elif granularity == "4h":
        unit, count = "小时", 12 # 预测未来 2 天 (12个4h点)
        interval_min = 240
    elif granularity == "30m":
        unit, count = "分钟", 12 # 预测未来 6 小时 (12个30m点)
        interval_min = 30
    elif granularity == "15m":
        unit, count = "分钟", 16 # 预测未来 4 小时 (16个15m点)
        interval_min = 15
    elif granularity == "1m":
        unit, count = "分钟", 16 # 预测未来 4 小时 (16个15m点作为锚点)
        interval_min = 15
    else:
        unit, count = "小时", 12
        interval_min = 60
    
    timechain_theme = timechain_context.get("theme") if timechain_context else "当前市场主线"
    timechain_summary = timechain_context.get("summary") if timechain_context else "暂无深度总结"

    status_note = ""
    if market_status == "CLOSED":
        status_note = "【特别注意：当前市场已休市】请重点分析周末/休市期间发生的突发情报，预测其对下一次恢复交易时可能产生的跳空(Gap)或趋势反转影响。"
    else:
        status_note = "【当前市场交易中】请根据实时动态预测后续走势。"

    prompt = f"""你是一个顶级的黄金宏观策略分析师。请预测未来伦敦金 (XAU/USD) 的价格演进趋势。
    
    {status_note}
    
    【当前基准】
    价格: {last_price} USD/oz
    近期趋势: {trend_desc} (近6个采样点价格: {recent_prices})
    当前分析粒度: {granularity}
    
    【宏观相关性背景】
    {macro_context}
    
    【市场整体情绪】
    24h 综合情绪分: {sentiment_desc}
    
    【市场深度脉络 (Timechain)】
    主线主题: {timechain_theme}
    核心演进逻辑: {timechain_summary}
    
    【未来 24h 重大预定事件】
    {macro_events_text}
    
    【近期核心情报详情】
    {intel_context}
    
    请输出未来 {count} 个点（每点间隔 {interval_min} 分钟）的预测价格。输出格式为 JSON 数组，每个对象包含:
    - "offset": 1 到 {count} 的整数
    - "predicted_price": 预测的价格 (float)
    
    要求：
    1. 必须综合考虑宏观背景（如美元走强压制金价）和核心情报的“逻辑演进”。
    2. 预测曲线必须体现对“预定事件”时刻的波动预期。
    3. 预测应体现出对近期情报情绪的反应，特别是多个情报指向同一逻辑时。
    4. 波动应符合伦敦金市场的真实特征（小时线波动 0.1%-0.5%，日线波动 0.5%-2%）。
    5. 只输出 JSON 数组，不要包含多余文字。
    """
    
    try:
        llm = DeepSeekLLM()
        forecast_raw = await llm.generate_json_async(prompt)
        
        anchor_points = []
        if isinstance(forecast_raw, list):
            for item in forecast_raw:
                offset = item.get("offset")
                price = item.get("predicted_price")
                if offset and price:
                    # 使用 (int(offset) - 1) 确保第一个预测点落在对齐后的 last_ts 上
                    target_ts = last_ts + timedelta(minutes=(int(offset) - 1) * interval_min)
                    anchor_points.append({
                        "timestamp": target_ts,
                        "price": round(float(price), 2)
                    })
        
        if not anchor_points:
            return []

        # 插值平滑：如果是 1m 粒度，将 15min 锚点插值为 1min 点
        if granularity == "1m":
            forecast_points = []
            current_base_ts = last_ts
            current_base_price = last_price
            
            for anchor in anchor_points:
                target_ts = anchor["timestamp"]
                target_price = anchor["price"]
                
                # 计算总分钟数
                total_mins = int(round((target_ts - current_base_ts).total_seconds() / 60))
                if total_mins > 0:
                    price_step = (target_price - current_base_price) / total_mins
                    for m in range(1, total_mins + 1):
                        step_ts = current_base_ts + timedelta(minutes=m)
                        step_price = current_base_price + (price_step * m)
                        forecast_points.append({
                            "timestamp": format_iso8601(step_ts),
                            "price": round(step_price, 2),
                            "is_forecast": True
                        })
                
                current_base_ts = target_ts
                current_base_price = target_price
            return forecast_points
        else:
            # 其他粒度保持原样格式返回
            return [{
                "timestamp": format_iso8601(p["timestamp"]),
                "price": p["price"],
                "is_forecast": True
            } for p in anchor_points]

    except Exception as e:
        logger.error(f"Gold forecast failed: {e}")
        return []



@router.get("/discover", response_model=dict[str, Any])
async def get_mobile_discover(
    accept_language: str | None = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_session),
):
    """
    Discovery feed for mobile.
    Returns trending fund tags and suggested readings.
    """
    # Determine language preference
    lang = "zh"
    if accept_language and ("en" in accept_language.lower() or "us" in accept_language.lower()):
        lang = "en"

    # 1. Trending Tags (Backend-curated or analytics-driven)
    # In a real app, this might come from a 'trending' table or cache.
    raw_tags = [
        {"title": "博时黄金", "code": "159937"},
        {"title": "华安黄金", "code": "518880"},
        {"title": "易方达黄金", "code": "161128"},
        {"title": "沪深300", "code": "510300"},
        {"title": "纳指100", "code": "513100"},
    ]

    trending_tags = []
    for tag in raw_tags:
        localized_title = translate_fund_name(tag["title"], lang)
        trending_tags.append({"title": localized_title, "code": tag["code"]})

    # 2. Suggested Reading (High-urgency intelligence items)
    statement = (
        select(Intelligence)
        .where(Intelligence.status == "COMPLETED")
        .where(Intelligence.urgency_score >= 8)
        .order_by(col(Intelligence.timestamp).desc())
        .limit(3)
    )
    results = db.exec(statement).all()

    suggested_reading = []
    for item in results:
        # Resolve best summary text
        alt_lang = "en" if lang == "zh" else "zh"
        summary_text = "分析中..." if lang == "zh" else "Analyzing..."

        if isinstance(item.summary, dict):
            summary_text = (
                item.summary.get(lang) or item.summary.get(alt_lang) or summary_text
            )
        elif isinstance(item.summary, str):
            summary_text = item.summary

        # Resolve category (mocking for now based on actual intelligence category)
        category_key = "funds.discover.category.market_analysis"
        if item.category == "macro_gold":
            category_key = "funds.discover.category.economy"

        # Priority to real image, then mock
        image_url = item.image_url or f"https://picsum.photos/seed/{item.id}/400/400"

        suggested_reading.append({
            "id": item.id,
            "category_key": category_key,
            "title": summary_text,
            "timestamp": item.timestamp.isoformat(),
            "imageUrl": image_url,
            "local_image_path": item.local_image_path
        })

    return v1_prepare_json({
        "trending_tags": trending_tags,
        "suggested_reading": suggested_reading
    })
