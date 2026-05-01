from typing import TypedDict, Optional, Dict, Any


class AgentState(TypedDict):
    text_query: Optional[str]
    image_bytes: Optional[bytes]
    audio_bytes: Optional[bytes]
    modality: Optional[str]
    extracted_entity: Optional[str]
    intent: Optional[str]
    retrieved_context: Dict[str, Any]
    final_response: Optional[str]