import json
from typing import Any

# Max rows kept in state and sent to LLM agents (charts / insights)
MAX_SQL_RESULT_ROWS = 100


def truncate_rows_for_agents(rows: list[dict[str, Any]], max_rows: int = MAX_SQL_RESULT_ROWS) -> tuple[str, bool]:
    """Serialize query rows to JSON, capping how many rows downstream agents see."""
    truncated = len(rows) > max_rows
    payload = rows[:max_rows] if truncated else rows
    text = json.dumps(payload, default=str)
    if truncated:
        text = (
            f"[Showing first {max_rows} of {len(rows)} rows — query was truncated for analysis]\n"
            + text
        )
    return text, truncated


def sample_json_for_prompt(sql_result: str, max_rows: int = 50) -> str:
    """Shrink sql_result JSON before sending to Gemini prompts."""
    if not sql_result or sql_result == "Query returned no rows.":
        return sql_result

    payload = sql_result
    if sql_result.startswith("[Showing first"):
        payload = sql_result.split("\n", 1)[1]

    try:
        data = json.loads(payload)
        if isinstance(data, list) and len(data) > max_rows:
            return json.dumps(data[:max_rows], default=str)
        return json.dumps(data, default=str) if isinstance(data, list) else sql_result[:8000]
    except json.JSONDecodeError:
        return sql_result[:8000]
