from src.lucidpanda.services import agent_tools


def test_list_tool_summaries_contains_macro():
    summaries = agent_tools.list_tool_summaries()
    names = {item["name"] for item in summaries}
    assert "query_macro_expectation" in names


def test_call_tool_unknown():
    result = agent_tools.call_tool("unknown_tool", {})
    assert "error" in result


def test_query_macro_expectation_requires_title():
    result = agent_tools.call_tool("query_macro_expectation", {"event_title": ""})
    assert result.get("error") == "event_title is required"

