from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from models.api import QueryResponse, ContextData
from agents.graph import app_graph
from agents.state import AgentState

app = FastAPI(title="Agentic Pokédex API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/query", response_model=QueryResponse)
async def process_multimodal_query(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    if not any([text, image, audio]):
        raise HTTPException(status_code=400, detail="Must provide text, image, or audio.")

    image_bytes = await image.read() if image else None
    audio_bytes = await audio.read() if audio else None

    initial_state: AgentState = {
        "text_query": text,
        "image_bytes": image_bytes,
        "audio_bytes": audio_bytes,
        "audio_mime_type": audio.content_type if audio else None,
        "modality": None,
        "extracted_entity": None,
        "intent": None,
        "retrieved_context": {},
        "final_response": None,
    }

    result = await app_graph.ainvoke(initial_state)

    ctx = result.get("retrieved_context", {})
    raw_stats = {
        "hp":      ctx.get("hp"),
        "attack":  ctx.get("attack"),
        "defense": ctx.get("defense"),
        "sp_atk":  ctx.get("sp_atk"),
        "sp_def":  ctx.get("sp_def"),
        "speed":   ctx.get("speed"),
    }
    # Only pass stats when every value is present; otherwise Pydantic rejects
    # None inside Dict[str, int].
    stats = raw_stats if all(v is not None for v in raw_stats.values()) else None

    context_used = ContextData(
        pokemon_name=result.get("extracted_entity"),
        pokemon_id=ctx.get("id"),
        flavor_text=ctx.get("flavor_text"),
        stats=stats,
        types=ctx.get("types"),
        sprite_url=ctx.get("sprite_url"),
        graph_relationships=ctx.get("graph_relationships"),
    )

    return QueryResponse(
        response=result.get("final_response", ""),
        context_used=context_used,
        modality_routed=result.get("modality", "text"),
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)