from datetime import UTC, datetime, timedelta

from src.lucidpanda.utils.graph_reasoning import infer_event_chains


def test_infer_event_chains_direct_relation():
    edges = [
        {
            "from_entity": "US Tariff",
            "to_entity": "Gold",
            "relation": "raises_tariff",
            "strength": 0.9,
        }
    ]
    result = infer_event_chains(edges)
    assert len(result) >= 1
    assert result[0]["conclusion"] == "BULLISH_GOLD"


def test_infer_event_chains_two_hop_relation():
    edges = [
        {
            "from_entity": "Fed",
            "to_entity": "USD",
            "relation": "usd_strength",
            "strength": 0.7,
        },
        {
            "from_entity": "USD",
            "to_entity": "Gold",
            "relation": "rate_hike",
            "strength": 0.8,
        },
    ]
    result = infer_event_chains(edges)
    assert any(item["hops"] == 2 for item in result)


def test_infer_event_chains_applies_relation_weights():
    edges = [
        {
            "from_entity": "US Tariff",
            "to_entity": "Gold",
            "relation": "raises_tariff",
            "strength": 0.9,
        }
    ]
    low = infer_event_chains(edges, relation_weights={"raises_tariff": 0.6})
    high = infer_event_chains(edges, relation_weights={"raises_tariff": 1.2})
    assert high[0]["confidence"] > low[0]["confidence"]


def test_infer_event_chains_applies_time_decay():
    now = datetime.now(UTC)
    recent_edges = [
        {
            "from_entity": "US Tariff",
            "to_entity": "Gold",
            "relation": "raises_tariff",
            "strength": 0.9,
            "created_at": now.isoformat(),
        }
    ]
    old_edges = [
        {
            "from_entity": "US Tariff",
            "to_entity": "Gold",
            "relation": "raises_tariff",
            "strength": 0.9,
            "created_at": (now - timedelta(days=15)).isoformat(),
        }
    ]
    recent = infer_event_chains(recent_edges)
    old = infer_event_chains(old_edges)
    assert recent[0]["confidence"] > old[0]["confidence"]


def test_infer_event_chains_handles_usd_weakness_as_bullish():
    edges = [
        {
            "from_entity": "DXY",
            "to_entity": "Gold",
            "relation": "usd_weakness",
            "strength": 0.7,
        }
    ]
    result = infer_event_chains(edges)
    assert result[0]["conclusion"] == "BULLISH_GOLD"
