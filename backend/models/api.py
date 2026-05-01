from typing import Optional, Dict, List, Any

from pydantic import BaseModel


class ContextData(BaseModel):
    pokemon_name: Optional[str] = None
    pokemon_id: Optional[int] = None
    flavor_text: Optional[str] = None
    stats: Optional[Dict[str, int]] = None
    types: Optional[List[str]] = None
    sprite_url: Optional[str] = None
    graph_relationships: Optional[List[str]] = None


class QueryResponse(BaseModel):
    response: str
    context_used: ContextData
    modality_routed: str