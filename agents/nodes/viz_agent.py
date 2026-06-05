import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.state import GraphState

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

def viz_agent_node(state: GraphState) -> GraphState:
    # Skip this agent entirely if planner decided no chart is needed
    if not state["needs_chart"]:
        state["chart_json"] = ""
        return state

    # Skip if there is no SQL result to visualize
    if not state["sql_result"] or state["sql_result"] == "Query returned no rows.":
        state["chart_json"] = ""
        return state

    # Build prompt — give Gemini the data and ask for a Plotly chart spec
    prompt = f"""
You are a data visualization expert. Given the data below, create a Plotly chart.

User question: {state['user_question']}

Data (JSON):
{state['sql_result']}

Respond ONLY with a valid JSON object representing a Plotly figure with this exact structure:
{{
  "data": [...],
  "layout": {{
    "title": "chart title here",
    "xaxis": {{"title": "x axis label"}},
    "yaxis": {{"title": "y axis label"}}
  }}
}}

Rules:
- Choose the best chart type: bar for comparisons, line for trends, pie for proportions
- Use the actual column names from the data as axis labels
- Return ONLY the JSON, no explanation, no markdown fences
"""

    response = llm.invoke(prompt)

    # Clean up response and parse JSON
    try:
        text = response.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        # Validate it is proper JSON
        chart_dict = json.loads(text)
        state["chart_json"] = json.dumps(chart_dict)
    except Exception as e:
        # If parsing fails, store empty — frontend will hide the chart panel
        state["chart_json"] = ""

    return state