---
name: deep-researcher
description: Specialized in fetching "ground truth" documentation and source code from GitHub for new technologies (e.g., FastMCP, Pydantic-AI) to avoid model hallucinations. Use when Gemini CLI needs to understand a new or rapidly evolving library's API by reading its official examples or tests.
---

# Deep Researcher

This skill prevents Gemini CLI from using outdated internal knowledge by forcing it to fetch latest source code and documentation directly from official GitHub repositories.

## When to Use

1.  **New Library Integration**: When a library like `FastMCP` or `Pydantic-AI` is relatively new and Gemini CLI's internal data is likely outdated.
2.  **API Signature Verification**: When standard search results are contradictory or vague about a specific function's parameters.
3.  **Complex Logic Extraction**: When looking for "best practice" patterns by reading a library's official `tests/` or `examples/`.

## Workflow

1.  **Consult Tech Reference**: Always read `docs/TECH_REFERENCE.md` first to find the "Ground Truth" URLs for the target technology.
2.  **Fetch Raw Source**: Use `web_fetch` or the bundled `github_fetcher.py` script to get the raw content of the target file.
3.  **Extract API Patterns**: Identify decorators, class signatures, and parameter types from the fetched code.
4.  **Verify with Smoke Test**: Before full integration, write a minimal `tests/demo_...` script to verify the logic.

## Tools & Resources

- **`scripts/github_fetcher.py`**: A helper script to normalize GitHub URLs and fetch raw content.
- **`references/tech_mapping.md`**: A mapping of technologies to their official GitHub locations (synced with `docs/TECH_REFERENCE.md`).

## Best Practices

- **Tests are Truth**: When the README is vague, always prioritize reading the library's unit tests (`tests/`) as they show exactly how the code is executed.
- **Raw is Faster**: Prefer fetching the Raw URL (e.g., `raw.githubusercontent.com/...`) to avoid HTML clutter and save context tokens.
