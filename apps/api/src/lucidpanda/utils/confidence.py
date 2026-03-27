from datetime import UTC, datetime
from typing import Any


def calc_confidence_score(
    corroboration_count: Any,
    source_credibility_score: Any = None,
    urgency_score: Any = None,
    timestamp: Any = None,
) -> float:
    """
    计算统一置信度分值（0~100）。
    组成：
      - 跨信源验证（40%）
      - 历史信源可信度（20%）
      - 事件紧急度（5%）
      - 基础分（35%）
      - 时间衰减（乘法）
    """
    try:
        count = int(corroboration_count or 1)
    except Exception:
        count = 1
    count = max(1, count)

    try:
        source_score = (
            float(source_credibility_score)
            if source_credibility_score is not None
            else 0.5
        )
    except Exception:
        source_score = 0.5
    source_score = max(0.0, min(1.0, source_score))

    try:
        urgency = float(urgency_score or 5)
    except Exception:
        urgency = 5.0
    urgency = max(1.0, min(10.0, urgency))

    corroboration_norm = min(1.0, (count - 1) / 4.0)
    time_decay = _confidence_time_decay(timestamp)

    score = (
        35.0 + 40.0 * corroboration_norm + 20.0 * source_score + 5.0 * (urgency / 10.0)
    ) * time_decay
    return round(max(0.0, min(100.0, score)), 1)


def _confidence_time_decay(timestamp: Any) -> float:
    """
    confidence 的跨时间衰减：
      <=6h   : 1.00
      <=24h  : 0.94
      <=72h  : 0.86
      <=7d   : 0.76
      >7d    : 0.66
    """
    if not timestamp:
        return 1.0
    try:
        ts = timestamp
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - ts.astimezone(UTC)).total_seconds() / 3600.0
        if age_hours <= 6:
            return 1.0
        if age_hours <= 24:
            return 0.94
        if age_hours <= 72:
            return 0.86
        if age_hours <= 24 * 7:
            return 0.76
        return 0.66
    except Exception:
        return 1.0


def calc_confidence_level(score: Any) -> str:
    """将置信度分值映射为可读等级。"""
    try:
        value = float(score)
    except Exception:
        value = 0.0
    if value >= 75:
        return "HIGH"
    if value >= 55:
        return "MEDIUM"
    return "LOW"
