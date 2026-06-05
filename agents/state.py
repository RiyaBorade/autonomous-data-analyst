from typing import TypedDict

class GraphState(TypedDict):
    user_question: str       # The question the user asked
    dataset_name: str        # PostgreSQL table name to query
    schema_context: str      # Output from schema_tool — given to every agent
    generated_sql: str       # SQL written by the query agent
    sql_result: str          # Result of executing the SQL
    error: str               # Error message if SQL fails
    retry_count: int         # How many times query agent has retried
    needs_chart: bool        # Planner sets this — does answer need a chart?
    needs_stats: bool        # Planner sets this — does answer need stats?
    chart_json: str          # Plotly chart as JSON string
    stats_result: str        # Statistical analysis output
    insight: str             # Plain English business insight
    final_answer: str        # Complete final answer shown to user