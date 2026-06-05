from langgraph.graph import StateGraph, END
from agents.state import GraphState
from agents.nodes.planner import planner_node
from agents.nodes.query_agent import query_agent_node
from agents.nodes.viz_agent import viz_agent_node
from agents.nodes.stats_agent import stats_agent_node
from agents.nodes.insight_agent import insight_agent_node
from agents.graph.edges import route_after_query

def error_handler_node(state: GraphState) -> GraphState:
    state["final_answer"] = f"Sorry, I could not generate a valid SQL query after 3 attempts. Last error: {state['error']}"
    return state

builder = StateGraph(GraphState)

# Register all nodes
builder.add_node("planner",       planner_node)
builder.add_node("query_agent",   query_agent_node)
builder.add_node("viz_agent",     viz_agent_node)
builder.add_node("stats_agent",   stats_agent_node)
builder.add_node("insight_agent", insight_agent_node)
builder.add_node("error_handler", error_handler_node)

# Flow
builder.set_entry_point("planner")
builder.add_edge("planner",       "query_agent")

# After query — self correction or continue
builder.add_conditional_edges(
    "query_agent",
    route_after_query,
    {
        "retry":         "query_agent",
        "error_handler": "error_handler",
        "continue":      "viz_agent"
    }
)

# Linear flow after query succeeds
builder.add_edge("viz_agent",     "stats_agent")
builder.add_edge("stats_agent",   "insight_agent")
builder.add_edge("insight_agent", END)
builder.add_edge("error_handler", END)

graph = builder.compile()