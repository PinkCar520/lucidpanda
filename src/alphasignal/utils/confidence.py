from typing import Any


def calc_confidence_score(
    corroboration_count: Any,
    source_credibility_score: Any = None,
    urgency_score: Any = None
) -> float:
    """
    计算统一置信度分值（0~100）。
    组成：
      - 跨信源验证（40%）
      - 历史信源可信度（20%）
      - 事件紧急度（5%）
      - 基础分（35%）
    """
    try:
        count = int(corroboration_count or 1)
    except Exception:
        count = 1
    count = max(1, count)

    try:
        source_score = float(source_credibility_score) if source_credibility_score is not None else 0.5
    except Exception:
        source_score = 0.5
    source_score = max(0.0, min(1.0, source_score))

    try:
        urgency = float(urgency_score or 5)
    except Exception:
        urgency = 5.0
    urgency = max(1.0, min(10.0, urgency))

    corroboration_norm = min(1.0, (count - 1) / 4.0)

    score = (
        35.0
        + 40.0 * corroboration_norm
        + 20.0 * source_score
        + 5.0 * (urgency / 10.0)
    )
    return round(max(0.0, min(100.0, score)), 1)


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
