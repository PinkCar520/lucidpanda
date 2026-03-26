from datetime import datetime, timezone
from typing import Any

BULLISH_RELATIONS = {
    "raises_tariff",
    "imposes_tariff",
    "sanctions",
    "geopolitical_risk",
    "conflict_escalation",
    "inflation_up",
    "rate_cut_expectation",
    "risk_off",
    "usd_weakness",
    "yield_down",
}

BEARISH_RELATIONS = {
    "rate_hike",
    "usd_strength",
    "real_yield_up",
    "risk_on",
    "disinflation",
}


def relation_signal(relation: str) -> str:
    rel = (relation or "").strip().lower()
    if rel in BULLISH_RELATIONS:
        return "BULLISH_GOLD"
    if rel in BEARISH_RELATIONS:
        return "BEARISH_GOLD"
    return "NEUTRAL"


def _time_decay_factor(created_at: Any) -> float:
    """
    基于边创建时间的时序衰减：
      <=24h: 1.00
      <=72h: 0.92
      <=7d : 0.82
      >7d : 0.72
    """
    if not created_at:
        return 1.0
    try:
        ts = created_at
        if isinstance(created_at, str):
            text = created_at.replace("Z", "+00:00")
            ts = datetime.fromisoformat(text)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds() / 3600.0
        if age_hours <= 24:
            return 1.0
        if age_hours <= 72:
            return 0.92
        if age_hours <= 24 * 7:
            return 0.82
        return 0.72
    except Exception:
        return 1.0


def infer_event_chains(
    edges: list[dict[str, Any]],
    relation_weights: dict[str, float] | None = None,
    max_items: int = 8
) -> list[dict[str, Any]]:
    """
    从图谱边中生成最小可解释推理链：
      - 1-hop: A -rel-> Gold
      - 2-hop: A -rel1-> B -rel2-> Gold
    """
    if not edges:
        return []

    normalized = []
    for edge in edges:
        from_name = str(edge.get("from_entity") or "").strip()
        to_name = str(edge.get("to_entity") or "").strip()
        relation = str(edge.get("relation") or "").strip()
        if not from_name or not to_name or not relation:
            continue
        normalized.append({
            "from_entity": from_name,
            "to_entity": to_name,
            "relation": relation,
            "strength": float(edge.get("strength") or 0.5),
            "created_at": edge.get("created_at"),
        })

    results: list[dict[str, Any]] = []
    gold_terms = {"gold", "xau", "黄金", "xauusd"}

    def is_gold(name: str) -> bool:
        low = name.lower()
        return any(token in low for token in gold_terms)

    for edge in normalized:
        if not is_gold(edge["to_entity"]):
            continue
        signal = relation_signal(edge["relation"])
        if signal == "NEUTRAL":
            continue
        rel_weight = float((relation_weights or {}).get(edge["relation"].lower(), 1.0))
        decay = _time_decay_factor(edge.get("created_at"))
        confidence = round(max(35.0, min(95.0, (45.0 + edge["strength"] * 35.0) * rel_weight * decay)), 1)
        results.append({
            "hops": 1,
            "chain": [edge],
            "conclusion": signal,
            "explanation": f"{edge['from_entity']} -> {edge['to_entity']} ({edge['relation']})",
            "confidence": confidence,
        })
        if len(results) >= max_items:
            return results

    for first in normalized:
        signal = relation_signal(first["relation"])
        if signal == "NEUTRAL":
            continue
        for second in normalized:
            if first["to_entity"].lower() != second["from_entity"].lower():
                continue
            if not is_gold(second["to_entity"]):
                continue
            w1 = float((relation_weights or {}).get(first["relation"].lower(), 1.0))
            w2 = float((relation_weights or {}).get(second["relation"].lower(), 1.0))
            d1 = _time_decay_factor(first.get("created_at"))
            d2 = _time_decay_factor(second.get("created_at"))
            confidence = round(
                max(38.0, min(92.0, (42.0 + (first["strength"] + second["strength"]) * 22.0) * ((w1 + w2) / 2.0) * ((d1 + d2) / 2.0))),
                1
            )
            results.append({
                "hops": 2,
                "chain": [first, second],
                "conclusion": signal,
                "explanation": (
                    f"{first['from_entity']} -> {first['to_entity']} ({first['relation']}) -> "
                    f"{second['to_entity']} ({second['relation']})"
                ),
                "confidence": confidence,
            })
            if len(results) >= max_items:
                return results

    return results
