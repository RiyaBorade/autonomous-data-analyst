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
    # Skip if no chart needed or no data
    if not state["needs_chart"]:
        state["chart_json"] = ""
        return state

    if not state["sql_result"] or state["sql_result"] == "Query returned no rows.":
        state["chart_json"] = ""
        return state

    # Parse the SQL result to understand the data shape
    try:
        data = json.loads(state["sql_result"])
        if not data:
            state["chart_json"] = ""
            return state
        columns = list(data[0].keys())
    except Exception:
        state["chart_json"] = ""
        return state

    prompt = f"""
You are a data visualization expert using Plotly.

User question: {state['user_question']}

Data columns available: {columns}

Data (first 5 rows shown):
{json.dumps(data[:5], default=str)}

Total rows in data: {len(data)}

Choose the best chart type:
- Bar chart: for comparing categories (market segment, hotel type, country)
- Line chart: for trends over time (monthly, yearly data)  
- Scatter chart: for correlations between two numeric variables
- Pie chart: for proportions that sum to 100%

Extract the actual values from the data to build the chart.

Respond ONLY with a valid JSON object like this example for a bar chart:
{{
  "data": [
    {{
      "type": "bar",
      "x": ["Category A", "Category B", "Category C"],
      "y": [100, 200, 150],
      "marker": {{"color": "#1A56DB"}}
    }}
  ],
  "layout": {{
    "title": "Your Chart Title",
    "xaxis": {{"title": "X Axis Label"}},
    "yaxis": {{"title": "Y Axis Label"}},
    "plot_bgcolor": "white",
    "paper_bgcolor": "white"
  }}
}}

For scatter chart use "mode": "markers" instead of bars.
For line chart use "type": "scatter" with "mode": "lines".
For pie chart use "type": "pie" with "labels" and "values" instead of x and y.

IMPORTANT: Use the ACTUAL data values from the data provided above, not placeholder text.
Return ONLY the JSON, no explanation, no markdown fences.
"""

    response = llm.invoke(prompt)

    try:
        text = response.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        chart_dict = json.loads(text)
        state["chart_json"] = json.dumps(chart_dict)
    except Exception:
        state["chart_json"] = ""

    return state