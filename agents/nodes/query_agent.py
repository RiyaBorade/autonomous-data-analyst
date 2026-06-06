import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.state import GraphState
from agents.utils import truncate_rows_for_agents

load_dotenv()

# Connect to PostgreSQL using the same DATABASE_URL from .env
engine = create_engine(os.getenv("DATABASE_URL"))

# Initialise Gemini for SQL generation
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

def query_agent_node(state: GraphState) -> GraphState:
    table_name = state["dataset_name"]

    # Build prompt — give Gemini the question and schema
    prompt = f"""
You are an expert SQL analyst. Write a single PostgreSQL SQL query to answer the user's question.

User question: {state['user_question']}

Table to query: {table_name}

Database schema:
{state['schema_context']}

Rules:
- Return ONLY the raw SQL query, no explanation, no markdown, no code fences
- Query ONLY the table "{table_name}" — use this exact table name
- Use only column names from the schema above
- Prefer aggregated queries (GROUP BY, COUNT, AVG, SUM) instead of returning raw rows
- For "show X by Y" or breakdown questions: SELECT y, COUNT(*) AS count FROM {table_name} GROUP BY y ORDER BY count DESC
- For correlation between two numeric columns: SELECT CORR(col1, col2) AS correlation FROM {table_name};
  Do NOT return all row pairs — use CORR() or a small aggregated result
- For comparisons of averages: use GROUP BY with AVG()
- If you must return individual rows, add LIMIT 100 at the end
- Never use SELECT * on the full table without aggregation or LIMIT
- End the query with a semicolon
- For category/segment/group questions: GROUP BY the relevant text column, ORDER BY count DESC
- For time trends: GROUP BY whatever date or year or month column exists in the schema
- For top N questions: add ORDER BY and LIMIT 20
- For questions about multiple metrics: SELECT all relevant columns together
- Always refer to the schema above to find correct column names — never guess column names

"""

    # If there was a previous error, tell Gemini what went wrong so it can fix it
    if state["error"]:
        prompt += f"""
Your previous SQL query failed with this error:
{state['error']}

Previous SQL that failed:
{state['generated_sql']}

Fix the SQL query based on the error above.
"""

    # Call Gemini to generate or fix the SQL
    response = llm.invoke(prompt)

    # Clean up the response — remove any markdown fences if Gemini adds them
    sql = response.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    # Save the generated SQL into state
    state["generated_sql"] = sql

    # Try to execute the SQL against PostgreSQL
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())

            # Format result as a readable string for the next agents
            if not rows:
                state["sql_result"] = "Query returned no rows."
            else:
                result_list = [dict(zip(columns, row)) for row in rows]
                state["sql_result"], _ = truncate_rows_for_agents(result_list)

            # Clear any previous error since execution succeeded
            state["error"] = ""

    except Exception as e:
        # Execution failed — save the error and increment retry counter
        state["error"] = str(e)
        state["retry_count"] = state["retry_count"] + 1
        state["sql_result"] = ""

    return state