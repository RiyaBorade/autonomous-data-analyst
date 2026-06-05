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

def planner_node(state: GraphState) -> GraphState:
    prompt = f"""
You are a data analyst planner. Given a user question and a database schema,
decide what is needed to answer it.

User question: {state['user_question']}

Schema:
{state['schema_context']}

Respond ONLY with valid JSON in exactly this format, nothing else:
{{
  "needs_chart": true or false,
  "needs_stats": true or false,
  "reasoning": "one sentence explanation"
}}

needs_chart = true if the answer would be clearer as a bar/line/pie chart.
needs_stats = true if the answer needs averages, correlations, or comparisons.
"""
    response = llm.invoke(prompt)

    try:
        text = response.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        decision = json.loads(text)
    except Exception:
        decision = {"needs_chart": True, "needs_stats": True}

    state["needs_chart"] = decision.get("needs_chart", True)
    state["needs_stats"] = decision.get("needs_stats", True)

    return state