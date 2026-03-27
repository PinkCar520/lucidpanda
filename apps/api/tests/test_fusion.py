from src.lucidpanda.utils.fusion import merge_entities


def test_merge_entities_deduplicates_by_name_and_type():
    entity_sets = [
        [{"name": "Fed", "type": "organization", "impact": "bearish"}],
        [{"name": "fed", "type": "organization", "impact": "neutral"}],
        [{"name": "Trump", "type": "person", "impact": "bullish"}],
    ]
    merged = merge_entities(entity_sets)
    assert len(merged) == 2
    assert merged[0]["name"] == "Fed"
    assert merged[1]["name"] == "Trump"
