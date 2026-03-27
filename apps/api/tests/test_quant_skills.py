from src.lucidpanda.services.quant_skills import (
    compute_expectation_gap,
    factor_peel_alpha,
)


def test_compute_expectation_gap():
    gap = compute_expectation_gap(actual=3.0, forecast=2.0, historical_std=0.5)
    assert gap == 2.0


def test_factor_peel_alpha_basic():
    gold = [0.02, 0.01, -0.01, 0.03]
    dxy = [0.01, 0.0, -0.02, 0.015]
    us10y = [0.005, 0.0, -0.01, 0.01]
    res = factor_peel_alpha(gold, dxy, us10y)
    assert "alpha" in res
    assert "beta_dxy" in res
    assert "beta_us10y" in res
    assert "residuals" in res
    assert len(res["residuals"]) == len(gold)

