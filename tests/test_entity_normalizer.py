from src.alphasignal.db.intelligence import IntelligenceRepo
from src.alphasignal.utils.entity_normalizer import normalize_entity_name


def test_normalize_entity_name_aliases():
    assert normalize_entity_name("特朗普") == "Trump"
    assert normalize_entity_name("donald trump") == "Trump"
    assert normalize_entity_name("美联储") == "Fed"
    assert normalize_entity_name("xau") == "Gold"
    assert normalize_entity_name("美元") == "USD"


def test_normalize_entity_name_fallback():
    assert normalize_entity_name("Custom Asset") == "Custom Asset"
    assert normalize_entity_name("  ") == ""


def test_normalize_relations_accepts_from_to_relation_keys():
    normalized = IntelligenceRepo._normalize_relations([
        {
            "from": "Trump",
            "to": "Gold",
            "relation": "raises_tariff",
            "direction": "forward",
            "strength": 0.8,
        }
    ])

    assert len(normalized) == 1
    assert normalized[0]["subject"] == "Trump"
    assert normalized[0]["object"] == "Gold"
    assert normalized[0]["predicate"] == "raises_tariff"


def test_normalize_relations_direction_compatibility():
    normalized = IntelligenceRepo._normalize_relations([
        {
            "from": "Fed",
            "to": "Gold",
            "relation": "rate_hike",
            "direction": "positive",
            "strength": "0.6",
        },
        {
            "subject": "Oil",
            "predicate": "inflation_up",
            "object": "Gold",
            "direction": "two_way",
            "strength": 2.0,
        },
    ])

    assert len(normalized) == 2
    assert normalized[0]["direction"] == "forward"
    assert normalized[1]["direction"] == "bidirectional"
    assert normalized[1]["strength"] == 1.0
