from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlmodel import Session, select

from src.lucidpanda.core.backtest import BacktestEngine
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.infra.database.connection import engine
from src.lucidpanda.models.macro_event import MacroEvent
from src.lucidpanda.services.quant_skills import (
    calculate_alpha_return,
    compute_expectation_gap,
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., dict[str, Any]]


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = (
        value.replace("%", "")
        .replace("$", "")
        .replace("K", "")
        .replace("M", "")
        .replace(",", "")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def get_historical_perf(keywords: str) -> dict[str, Any]:
    """
    查询历史上包含特定关键词的新闻发布后 1h 的胜率与平均收益。
    """
    if not keywords:
        return {"error": "keywords are required"}
    
    db = IntelligenceDB()
    bt = BacktestEngine(db)
    stats = bt.get_confidence_stats(keywords)
    
    if not stats:
        return {
            "keywords": keywords,
            "count": 0,
            "message": "历史上未发现包含该关键词的交易信号。"
        }
    
    return {
        "keywords": keywords,
        "count": stats["count"],
        "win_rate": f"{stats['win_rate']}%",
        "avg_return": f"{stats['avg_return']}%",
        "reliability": "high" if stats["count"] >= 10 else "medium" if stats["count"] >= 5 else "low"
    }


def get_market_positioning(indicator_name: str = "COT_GOLD_NET") -> dict[str, Any]:
    """
    获取市场持仓情绪指标（如 COT 黄金净持仓分位数）。
    """
    db = IntelligenceDB()
    # 备注：IntelligenceDB 组合了 MarketRepo 的方法
    indicator = db.get_latest_indicator(indicator_name)
    
    if not indicator:
        return {"error": f"No data found for indicator: {indicator_name}"}
    
    percentile = indicator.get("percentile")
    value = indicator.get("value")
    
    sentiment = "NEUTRAL"
    if percentile is not None:
        if percentile > 85:
            sentiment = "OVERCROWDED_LONG (Extreme Bullish/Contrarian Bearish)"
        elif percentile < 15:
            sentiment = "OVERCROWDED_SHORT (Extreme Bearish/Contrarian Bullish)"
        elif percentile > 70:
            sentiment = "BULLISH_BIAS"
        elif percentile < 30:
            sentiment = "BEARISH_BIAS"

    return {
        "indicator": indicator_name,
        "value": value,
        "percentile": f"{percentile}%" if percentile is not None else "N/A",
        "sentiment": sentiment,
        "timestamp": indicator.get("timestamp").isoformat() if indicator.get("timestamp") else None,
        "description": indicator.get("description")
    }


def get_entity_influence(entity_name: str) -> dict[str, Any]:
    """
    查询特定实体在知识图谱中的中心度及其关联影响。
    """
    if not entity_name:
        return {"error": "entity_name is required"}
    
    db = IntelligenceDB()
    graph = db.get_entity_graph(entity_name, limit=50)
    
    if not graph or not graph.get("center"):
        return {"error": f"Entity '{entity_name}' not found in knowledge graph."}
    
    edges = graph.get("edges") or []
    # 统计活跃度：关联边的总数
    activity_count = len(edges)
    
    # 分析主要关联对象及其强度
    relations = []
    for e in edges:
        target = e["to_entity"] if e["from_entity"].lower() == entity_name.lower() else e["from_entity"]
        relations.append({
            "target": target,
            "relation": e["relation"],
            "strength": e["strength"],
            "confidence": e["confidence_score"]
        })
    
    # 按强度排序取前 5
    top_relations = sorted(relations, key=lambda x: x["strength"], reverse=True)[:5]
    
    return {
        "entity": entity_name,
        "type": graph["center"].get("entity_type"),
        "activity_score": activity_count,
        "top_relations": top_relations,
        "summary": f"该实体在图谱中有 {activity_count} 条关联，主要与 {', '.join([r['target'] for r in top_relations[:3]])} 存在联系。"
    }


def query_macro_expectation(event_title: str, date_str: str | None = None) -> dict[str, Any]:
    """
    Enhanced macro event matching with cross-lingual aliasing and time-window tolerance.
    """
    if not event_title:
        return {"matches": [], "match_count": 0, "error": "event_title is required"}

    # 1. Cross-lingual mapping for common indicators
    ALIASES = {
        "cpi": ["居民消费价格指数", "消费者物价指数", "通胀"],
        "ppi": ["生产者物价指数"],
        "non-farm": ["非农", "就业人数"],
        "payrolls": ["非农", "就业人数"],
        "unemployment": ["失业率"],
        "gdp": ["国内生产总值"],
        "pmi": ["采购经理指数"],
        "fed": ["联储", "利率决议", "鲍威尔"],
        "interest rate": ["利率"],
        "retail sales": ["零售销售"],
    }
    
    clean_title = event_title.lower()
    search_terms = [event_title]
    for key, vals in ALIASES.items():
        if key in clean_title:
            search_terms.extend(vals)

    target_date: date | None = None
    if date_str:
        try:
            target_date = date.fromisoformat(date_str[:10])
        except Exception:
            pass # Fallback to wider search if date is mangled

    matches: list[dict[str, Any]] = []
    with Session(engine) as session:
        # 2. Multi-term OR search
        from sqlalchemy import or_
        filters = [MacroEvent.title.ilike(f"%{t}%") for t in search_terms]
        statement = select(MacroEvent).where(or_(*filters))
        
        # 3. 48-hour time window tolerance (T-1 to T+1)
        if target_date:
            from datetime import timedelta
            date_min = target_date - timedelta(days=1)
            date_max = target_date + timedelta(days=1)
            statement = statement.where(MacroEvent.release_date.between(date_min, date_max))
            
        statement = statement.order_by(MacroEvent.release_date.desc()).limit(10)
        rows = session.exec(statement).all()

    for row in rows:
        actual = _parse_float(row.actual_value)
        forecast = _parse_float(row.forecast_value)
        previous = _parse_float(row.previous_value)
        # Z-Score logic placeholder: assuming 0.1 as default std if historical data missing
        surprise = (actual - forecast) if actual is not None and forecast is not None else None
        
        matches.append({
            "id": str(row.id),
            "title": row.title,
            "release_date": row.release_date.isoformat(),
            "parsed": {"previous": previous, "forecast": forecast, "actual": actual},
            "surprise": surprise,
            "impact_level": row.impact_level
        })

    return {
        "matches": matches,
        "match_count": len(matches),
        "best_match": matches[0] if matches else None,
    }


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="query_macro_expectation",
        description="获取特定宏观指标的预期值、前值及 Surprise 强度",
        input_schema={
            "type": "object",
            "properties": {
                "event_title": {"type": "string", "description": "宏观事件标题或关键词"},
                "date": {"type": "string", "description": "发布日期 (YYYY-MM-DD)", "nullable": True},
            },
            "required": ["event_title"],
        },
        handler=query_macro_expectation,
    ),
    ToolSpec(
        name="get_historical_perf",
        description="统计历史上包含特定关键词的新闻发布后的胜率与收益率 (EV)",
        input_schema={
            "type": "object",
            "properties": {
                "keywords": {"type": "string", "description": "查询关键词 (如 '地缘政治', '非农')"},
            },
            "required": ["keywords"],
        },
        handler=get_historical_perf,
    ),
    ToolSpec(
        name="get_market_positioning",
        description="获取黄金市场持仓/情绪分位 (如 COT_GOLD_NET)",
        input_schema={
            "type": "object",
            "properties": {
                "indicator_name": {"type": "string", "description": "指标名 (默认: COT_GOLD_NET)"},
            },
        },
        handler=get_market_positioning,
    ),
    ToolSpec(
        name="get_entity_influence",
        description="查询该实体在图谱中的活跃度及主要关联强度",
        input_schema={
            "type": "object",
            "properties": {
                "entity_name": {"type": "string", "description": "实体名称 (如 '特朗普', '美联储')"},
            },
            "required": ["entity_name"],
        },
        handler=get_entity_influence,
    ),
    ToolSpec(
        name="calculate_alpha_return",
        description="利用 OLS 回归剥离美元与利率因子，返回黄金超额收益",
        input_schema={
            "type": "object",
            "properties": {
                "gold_returns": {"type": "array", "items": {"type": "number"}},
                "dxy_returns": {"type": "array", "items": {"type": "number"}},
                "us10y_returns": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["gold_returns", "dxy_returns", "us10y_returns"],
        },
        handler=calculate_alpha_return,
    ),
    ToolSpec(
        name="compute_expectation_gap",
        description="计算宏观预期差 Z-Score: (actual - forecast) / historical_std",
        input_schema={
            "type": "object",
            "properties": {
                "actual": {"type": "number"},
                "forecast": {"type": "number"},
                "historical_std": {"type": "number"},
            },
            "required": ["actual", "forecast", "historical_std"],
        },
        handler=lambda actual, forecast, historical_std: {
            "expectation_gap": compute_expectation_gap(actual, forecast, historical_std)
        },
    ),
]


TOOL_REGISTRY: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}


def list_tool_summaries() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in TOOLS
    ]


def call_tool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"error": f"Unknown tool: {name}"}
    args = args or {}
    try:
        return tool.handler(**args)
    except TypeError as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}
    except Exception as exc:
        return {"error": f"Tool {name} failed: {exc}"}
