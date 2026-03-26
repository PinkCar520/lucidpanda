from typing import Any, cast
from fastmcp import FastMCP
from src.lucidpanda.services.agent_tools import AgentTools

mcp = FastMCP("AlphaHub MCP Server")
tools = AgentTools()


@mcp.tool
def query_macro_expectation(event_title: str, date: str | None = None) -> dict[str, Any]:
    """
    获取特定宏观指标的预期值、前值及 Surprise 强度。
    """
    return cast(dict[str, Any], tools.query_macro_expectation(event_title=event_title, date_str=date))


@mcp.tool
def calculate_alpha_return(
    gold_returns: list[float],
    dxy_returns: list[float],
    us10y_returns: list[float],
) -> dict[str, Any]:
    """
    OLS 因子剥离，返回黄金 alpha_return。
    """
    return cast(dict[str, Any], tools.calculate_alpha_return(
        gold_returns=gold_returns,
        dxy_returns=dxy_returns,
        us10y_returns=us10y_returns,
    ))


@mcp.tool
def compute_expectation_gap(actual: float, forecast: float, historical_std: float) -> dict[str, float | None]:
    """
    计算宏观预期差 Z-Score。
    """
    return {"expectation_gap": tools.compute_expectation_gap(actual, forecast, historical_std)}


def main() -> None:
    # Stdio-based MCP server
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
