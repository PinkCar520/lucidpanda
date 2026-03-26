from typing import Any


def merge_entities(entity_sets:
    Any, max_items: int = 12) -> list[dict]:
    """
    合并 cluster 内多条情报的 entities 列表，按 name+type 去重。
    """
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()
    if not isinstance(entity_sets, list):
        return merged

    for entity_list in entity_sets:
        if not isinstance(entity_list, list):
            continue
        for entity in entity_list:
            if not isinstance(entity, dict):
                continue
            name = str(entity.get("name", "")).strip()
            entity_type = str(entity.get("type", "unknown")).strip() or "unknown"
            impact = str(entity.get("impact", "neutral")).strip() or "neutral"
            if not name:
                continue
            key = (name.lower(), entity_type.lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append({"name": name, "type": entity_type, "impact": impact})
            if len(merged) >= max_items:
                return merged
    return merged

