from typing import Optional, List

from fastmcp import FastMCP

from src.lucidpanda.services.agent_tools import (
    query_macro_expectation as _query_macro_expectation,
    calculate_alpha_return as _calculate_alpha_return,
    compute_expectation_gap as _compute_expectation_gap,
)


mcp = FastMCP("AlphaHub MCP Server")


@mcp.tool
def query_macro_expectation(event_title: str, date: Optional[str] = None):
    """
    获取特定宏观指标的预期值、前值及 Surprise 强度。
    """
    return _query_macro_expectation(event_title=event_title, date_str=date)


@mcp.tool
def calculate_alpha_return(
    gold_returns: List[float],
    dxy_returns: List[float],
    us10y_returns: List[float],
):
    """
    OLS 因子剥离，返回黄金 alpha_return。
    """
    return _calculate_alpha_return(
        gold_returns=gold_returns,
        dxy_returns=dxy_returns,
        us10y_returns=us10y_returns,
    )


@mcp.tool
def compute_expectation_gap(actual: float, forecast: float, historical_std: float):
    """
    计算宏观预期差 Z-Score。
    """
    return {"expectation_gap": _compute_expectation_gap(actual, forecast, historical_std)}


def main() -> None:
    # Stdio-based MCP server
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
