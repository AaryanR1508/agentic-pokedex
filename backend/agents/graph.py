from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents import nodes


workflow = StateGraph(AgentState)

workflow.add_node("router", nodes.router_node)
workflow.add_node("audio_handler", nodes.audio_handler_node)
workflow.add_node("image_handler", nodes.image_handler_node)
workflow.add_node("text_handler", nodes.text_handler_node)
workflow.add_node("generator", nodes.generator_node)

workflow.set_entry_point("router")


def route_modality(state: AgentState) -> str:
    modality = state.get("modality", "text")
    return modality


workflow.add_conditional_edges(
    "router",
    route_modality,
    {
        "audio": "audio_handler",
        "image": "image_handler",
        "text": "text_handler"
    }
)

workflow.add_edge("audio_handler", "generator")
workflow.add_edge("image_handler", "generator")
workflow.add_edge("text_handler", "generator")

workflow.add_edge("generator", END)

app_graph = workflow.compile()