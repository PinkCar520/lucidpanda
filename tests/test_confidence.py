from src.alphasignal.utils.confidence import calc_confidence_score, calc_confidence_level


def test_confidence_score_increases_with_corroboration():
    low = calc_confidence_score(corroboration_count=1, source_credibility_score=0.5, urgency_score=5)
    high = calc_confidence_score(corroboration_count=5, source_credibility_score=0.5, urgency_score=5)
    assert high > low


def test_confidence_score_is_clamped():
    score = calc_confidence_score(corroboration_count=999, source_credibility_score=2, urgency_score=100)
    assert 0 <= score <= 100


def test_confidence_level_mapping():
    assert calc_confidence_level(80) == "HIGH"
    assert calc_confidence_level(60) == "MEDIUM"
    assert calc_confidence_level(40) == "LOW"
