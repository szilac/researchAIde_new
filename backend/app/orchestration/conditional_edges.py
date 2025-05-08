\
from typing import Dict, Any
# Import GraphState from its new location
from .graph_state import GraphState, MAX_ITERATIONS_REFINE

# Conditional Edge Functions
def should_refine_further(state: GraphState) -> str:
    """
    Determines if the PhD-PostDoc refinement cycle should continue.
    """
    print(f"--- Condition: should_refine_further (Iteration: {state.get('iteration_count')}) ---")
    iteration_count = state.get("iteration_count", 0)
    postdoc_eval = state.get("postdoc_evaluation_output", {})
    
    if postdoc_eval.get("accept_as_is") == True:
        print("--- Condition: Directions accepted by PostDoc/Human. ---")
        return "finalize_output"

    if iteration_count >= MAX_ITERATIONS_REFINE:
        print("--- Condition: Max iterations reached. ---")
        return "finalize_output"
    
    quality_score = postdoc_eval.get("score", 0.0)
    MIN_ACCEPTABLE_SCORE = 0.85 
    if quality_score >= MIN_ACCEPTABLE_SCORE:
        print(f"--- Condition: Quality score ({quality_score}) met threshold. ---")
        return "finalize_output"

    print("--- Condition: Continuing refinement loop. ---")
    return "refine_directions"

def check_for_errors(state: GraphState) -> str:
    """
    Checks if an error message is present in the state.
    Routes to the global error handler if an error is found.
    """
    if state.get("error_message"):
        print(f"--- Condition: Error Detected from {state.get('error_source_node')} -> Routing to Error Handler ---")
        return "error_found"
    return "no_error"

def check_for_conflict(state: GraphState) -> str:
    """
    Checks if a conflict was detected in the previous step.
    """
    if state.get("conflict_detected"):
        print(f"--- Condition: Conflict Detected -> Routing to Conflict Resolver ---")
        return "conflict_found"
    return "no_conflict"
