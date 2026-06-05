from agents.state import GraphState

def route_after_query(state: GraphState) -> str:
    # If there is an error AND we have retried less than 3 times — try again
    if state["error"] and state["retry_count"] < 3:
        return "retry"

    # If we have retried 3 times and still failing — give up
    if state["retry_count"] >= 3:
        return "error_handler"

    # No error — move forward to visualization and stats agents
    return "continue"