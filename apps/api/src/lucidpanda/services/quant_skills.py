from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import statsmodels.api as sm


def _to_float_list(values: Any) -> Optional[List[float]]:
    if values is None:
        return None
    if isinstance(values, (list, tuple)):
        out: List[float] = []
        for v in values:
            try:
                out.append(float(v))
            except Exception:
                return None
        return out
    try:
        return [float(values)]
    except Exception:
        return None


def compute_expectation_gap(actual: float, forecast: float, historical_std: float) -> Optional[float]:
    """
    Z-score based expectation surprise: (actual - forecast) / historical_std.
    """
    try:
        if historical_std == 0:
            return None
        return (float(actual) - float(forecast)) / float(historical_std)
    except Exception:
        return None


def factor_peel_alpha(
    gold_returns: Iterable[float],
    dxy_returns: Iterable[float],
    us10y_returns: Iterable[float],
) -> Dict[str, Any]:
    gold = _to_float_list(gold_returns)
    dxy = _to_float_list(dxy_returns)
    us10y = _to_float_list(us10y_returns)
    if not gold or not dxy or not us10y:
        return {"error": "gold_returns, dxy_returns, us10y_returns must be numeric arrays"}
    if not (len(gold) == len(dxy) == len(us10y)) or len(gold) < 3:
        return {"error": "input arrays must have the same length and >= 3"}

    y = np.array(gold, dtype=float)
    X = np.column_stack([dxy, us10y]).astype(float)
    X = sm.add_constant(X)
    model = sm.OLS(y, X).fit()

    alpha = float(model.params[0])
    beta_dxy = float(model.params[1])
    beta_us10y = float(model.params[2])
    residuals = [float(r) for r in model.resid.tolist()]

    return {
        "alpha": alpha,
        "beta_dxy": beta_dxy,
        "beta_us10y": beta_us10y,
        "r2": float(model.rsquared),
        "residuals": residuals,
    }


def calculate_alpha_return(
    gold_returns: Iterable[float],
    dxy_returns: Iterable[float],
    us10y_returns: Iterable[float],
) -> Dict[str, Any]:
    """
    Compute alpha return as regression residual on the latest observation.
    """
    result = factor_peel_alpha(gold_returns, dxy_returns, us10y_returns)
    if "error" in result:
        return result
    residuals = result.get("residuals") or []
    alpha_return_latest = residuals[-1] if residuals else None
    return {
        "alpha_return_latest": alpha_return_latest,
        "alpha": result.get("alpha"),
        "beta_dxy": result.get("beta_dxy"),
        "beta_us10y": result.get("beta_us10y"),
        "r2": result.get("r2"),
    }

