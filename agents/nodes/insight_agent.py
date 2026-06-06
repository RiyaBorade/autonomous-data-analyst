import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.state import GraphState
from agents.utils import sample_json_for_prompt

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

def insight_agent_node(state: GraphState) -> GraphState:
    # Build context from everything the previous agents produced
    context_parts = []

    context_parts.append(f"User question: {state['user_question']}")
    context_parts.append(f"SQL query used: {state['generated_sql']}")
    context_parts.append(f"Query result: {sample_json_for_prompt(state['sql_result'])}")

    if state["stats_result"]:
        context_parts.append(f"Statistical analysis: {state['stats_result']}")

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a senior data analyst writing a business insight.

{context}

Write a clear, concise business insight in 3-5 sentences that:
1. Directly answers the user's question
2. Highlights the most important finding in the data
3. Mentions any notable patterns or outliers
4. Uses plain English — no technical jargon

Do not mention SQL, DataFrames, or technical terms.
Write as if explaining to a business manager.
"""

    response = llm.invoke(prompt)

    # Store insight and set as the final answer
    state["insight"] = response.content.strip()
    state["final_answer"] = response.content.strip()

    return state