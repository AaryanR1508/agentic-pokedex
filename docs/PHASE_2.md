# ⚙️ Phase 2: The Agentic Backend — Implementation Plan

**Owner:** Backend/LLM Engineer  
**Goal:** Build a FastAPI service powered by LangGraph that serves as the "brain" of the application. It receives multi-modal inputs (text, image, audio), routes them to the appropriate retrieval strategy (ChromaDB vector search or Neo4j graph traversal), and synthesizes a final response using Gemini 3 Flash.

> [!IMPORTANT]
> The backend relies entirely on the databases being populated by the Phase 1 ingestion script. Ensure Phase 1 is complete or you have access to mock data before fully testing the retrieval components.

---

## 1. Environment & Tooling Setup

### 1.1 Python Environment

- Use **`uv`** as the package manager. The backend `pyproject.toml` is separate from the ingestion script.
- Target **Python 3.11** (matching the Dockerfile).
- The `Dockerfile` is already provided in the Phase 0 infrastructure plan.

### 1.2 Required Dependencies

Run `uv add` for the following packages:

| Package | Purpose |
|---|---|
| `fastapi` | Web framework for building the API |
| `uvicorn` | ASGI server to run FastAPI |
| `python-multipart` | Required by FastAPI to handle `FormData` (file uploads for images/audio) |
| `langgraph` | Building the stateful, multi-agent routing workflow |
| `langchain-google-genai` | Integration with Gemini 3 Flash (`ChatGoogleGenerativeAI`) |
| `langchain-core` | Core abstractions (messages, prompt templates, output parsers) |
| `neo4j` | Official Neo4j Python driver for executing Cypher queries |
| `chromadb` | ChromaDB client for vector search |
| `chromadb[openclip]` or `open-clip-torch` | OpenCLIP embedding function (MUST match Phase 1 exactly) |
| `pydantic` | Data validation and API response modeling |
| `python-dotenv` | Loading `.env` variables |

### 1.3 Environment Variables

Ensure these are present in the `.env` file and loaded into a Pydantic `Settings` model:

| Variable | Example | Notes |
|---|---|---|
| `GEMINI_API_KEY` | `AIzaSy...` | Required for Langchain Google GenAI |
| `CHROMA_HOST` | `chromadb` | Docker network hostname (use `localhost` if running outside Docker) |
| `NEO4J_URI` | `bolt://neo4j:7687` | Docker network URI (use `bolt://localhost:7687` outside) |
| `NEO4J_USER` | `neo4j` | Database user |
| `NEO4J_PASSWORD` | `password` | Database password |

### 1.4 Folder Structure

```text
backend/
├── pyproject.toml          # Managed by uv
├── main.py                 # FastAPI application and endpoints
├── core/
│   ├── config.py           # Pydantic Settings for env vars
│   └── dependencies.py     # Dependency injection (DB clients, LLM instantiation)
├── agents/
│   ├── graph.py            # LangGraph StateGraph definition and routing logic
│   ├── state.py            # TypedDict defining the LangGraph state
│   └── nodes.py            # The individual action nodes (text, image, audio handlers)
├── retrieval/
│   ├── neo4j_client.py     # Cypher query execution and graph traversal
│   └── chroma_client.py    # Vector search logic (text and images)
└── models/
    └── api.py              # Pydantic models for API requests/responses
```

---

## 2. API Design (`main.py` & `models/api.py`)

### 2.1 The Single Power-House Endpoint

The frontend will communicate with a single endpoint that handles all modalities:

`POST /api/v1/query`

**Request Format:** `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `text` | `string` (Optional) | The user's text query (e.g., "Who is strong against Charizard?") |
| `image` | `file` (Optional) | Uploaded image file (`image/png`, `image/jpeg`) |
| `audio` | `file` (Optional) | Uploaded audio file (`audio/ogg`, `audio/mpeg`) |

> [!NOTE]
> The endpoint must accept at least one of these fields. If multiple are provided (e.g., an image *and* text), decide on a precedence order or handle multimodal fusion. For the MVP, prioritize **Audio > Image > Text**.

**FastAPI Implementation:**

```python
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from typing import Optional

app = FastAPI(title="Agentic Pokédex API")

@app.post("/api/v1/query", response_model=QueryResponse)
async def process_multimodal_query(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    if not any([text, image, audio]):
        raise HTTPException(status_code=400, detail="Must provide text, image, or audio.")
        
    # Read files into bytes if present
    image_bytes = await image.read() if image else None
    audio_bytes = await audio.read() if audio else None
    
    # Invoke LangGraph workflow
    # result = await graph.ainvoke(...)
    
    return result
```

### 2.2 Response Model

The response must provide both the LLM's natural language answer AND the structured context used, so the frontend can render rich UI cards (the "Pokédex Visor").

```python
class ContextData(BaseModel):
    pokemon_name: Optional[str] = None
    stats: Optional[Dict[str, int]] = None
    types: Optional[List[str]] = None
    sprite_url: Optional[str] = None
    graph_relationships: Optional[List[str]] = None # e.g., ["Evolves to Charizard", "Weak against Water"]

class QueryResponse(BaseModel):
    response: str  # The natural language answer from Gemini
    context_used: ContextData  # Structured data for the UI
    modality_routed: str # "text", "image", or "audio" (for debugging/UI feedback)
```

---

## 3. LangGraph Workflow (`agents/`)

LangGraph will orchestrate the flow. We need a stateful graph that routes the request based on the input modality.

### 3.1 State Definition (`state.py`)

```python
from typing import TypedDict, Optional, Dict, Any

class AgentState(TypedDict):
    # Inputs
    text_query: Optional[str]
    image_bytes: Optional[bytes]
    audio_bytes: Optional[bytes]
    
    # Routing decision
    modality: Optional[str] 
    
    # Extracted data from retrieval
    extracted_entity: Optional[str] # e.g., the identified Pokemon name
    retrieved_context: Dict[str, Any] # The raw data pulled from Neo4j/Chroma
    
    # Output
    final_response: Optional[str]
```

### 3.2 Workflow Nodes (`nodes.py`)

1.  **`router_node`**: Examines the state and determines the path.
    *   If `audio_bytes`: Route to `audio_handler_node`.
    *   If `image_bytes`: Route to `image_handler_node`.
    *   If `text_query`: Route to `text_handler_node`.
2.  **`audio_handler_node`**:
    *   **Action:** Pass the raw `.ogg` bytes directly to Gemini 1.5 Flash (multimodal prompt: "Identify the Pokémon in this audio clip. Reply with ONLY its name.").
    *   **Action:** Take the resulting name, query Neo4j for its stats/types/lore, and populate `retrieved_context`.
3.  **`image_handler_node`**:
    *   **Action:** Embed the `image_bytes` using OpenCLIP.
    *   **Action:** Query ChromaDB `pokemon_images` collection for the nearest vector.
    *   **Action:** Extract the `name` metadata from the top result.
    *   **Action:** Query Neo4j for stats/types/lore using that name, populate `retrieved_context`.
4.  **`text_handler_node`**:
    *   **Action:** Use an LLM call to extract entities/intent from the text (e.g., "Who is strong against Charizard?" -> Intent: Type Effectiveness, Entity: Charizard).
    *   **Action:** Based on intent, execute the appropriate Cypher query in Neo4j (graph traversal) OR semantic search in ChromaDB `pokemon_text`. Populate `retrieved_context`.
5.  **`generator_node`**:
    *   **Action:** Takes the original query (or inferred intent) and the `retrieved_context`.
    *   **Action:** Prompts Gemini 1.5 Flash: *"You are an expert Pokédex AI. Answer the user's query using ONLY the provided context. Context: {retrieved_context}"*
    *   **Action:** Populates `final_response`.

### 3.3 Graph Construction (`graph.py`)

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("audio_handler", audio_handler_node)
workflow.add_node("image_handler", image_handler_node)
workflow.add_node("text_handler", text_handler_node)
workflow.add_node("generator", generator_node)

workflow.set_entry_point("router")

# Conditional edges from router
workflow.add_conditional_edges(
    "router",
    lambda state: state["modality"],
    {
        "audio": "audio_handler",
        "image": "image_handler",
        "text": "text_handler"
    }
)

# All handlers go to the generator
workflow.add_edge("audio_handler", "generator")
workflow.add_edge("image_handler", "generator")
workflow.add_edge("text_handler", "generator")

workflow.add_edge("generator", END)

app_graph = workflow.compile()
```

---

## 4. Retrieval Layer (`retrieval/`)

This is where the actual database interaction happens. It isolates LangGraph from the DB clients.

### 4.1 Neo4j Client (`neo4j_client.py`)

Implement a class to manage the Neo4j driver and execute specific Cypher queries.

**Key Cypher Queries needed:**

1.  **Get Pokémon Details (Basic Lookup):**
    ```cypher
    MATCH (p:Pokemon {name: $name})
    OPTIONAL MATCH (p)-[:HAS_TYPE]->(t:Type)
    OPTIONAL MATCH (p)-[:EVOLVES_TO]->(evo:Pokemon)
    RETURN p.name as name, p.hp as hp, p.attack as attack, 
           p.sprite_url as sprite_url, collect(DISTINCT t.name) as types,
           collect(DISTINCT evo.name) as evolutions
    ```

2.  **Type Effectiveness Traversal (The "Who is strong against X?" query):**
    ```cypher
    MATCH (p:Pokemon {name: $name})-[:HAS_TYPE]->(t:Type)
    MATCH (attacking_type:Type)-[:STRONG_AGAINST]->(t)
    RETURN DISTINCT attacking_type.name as strong_against
    ```
    *Note: This utilizes the graph structure established in Phase 1 to answer complex relational questions without LLM hallucinations.*

### 4.2 ChromaDB Client (`chroma_client.py`)

Implement a class to interact with the two Chroma collections.

1.  **Image Similarity Search:**
    *   Initialize the `OpenCLIPEmbeddingFunction` (must be identical to Phase 1: `ViT-B-32`).
    *   Load the `pokemon_images` collection.
    *   Method: `search_image(image_bytes: bytes) -> str` (Returns the Pokemon name from the top result's metadata).

2.  **Semantic Text Search:**
    *   Load the `pokemon_text` collection.
    *   Method: `search_text(query: str) -> str` (Returns the top matching flavor text document).

---

## 5. LLM Integration (Gemini 3 Flash)

Use `ChatGoogleGenerativeAI` from Langchain. Gemini 3 Flash is chosen for its speed and multimodal capabilities.

### 5.1 Native Audio Support

Gemini natively supports audio inputs. In the `audio_handler_node`, construct a message with the raw audio bytes:

```python
from langchain_core.messages import HumanMessage

message = HumanMessage(
    content=[
        {"type": "text", "text": "Identify the Pokémon whose cry is in this audio. Respond with JUST the name."},
        {"type": "media", "mime_type": "audio/ogg", "data": audio_bytes_base64}
    ]
)
response = llm.invoke([message])
pokemon_name = response.content.strip().lower()
```

### 5.2 The Generator Prompt

The final step (`generator_node`) needs a strict prompt to ensure it bases its answer *only* on the retrieved context and formats it well.

```python
from langchain_core.prompts import ChatPromptTemplate

template = """You are the Rotom Pokédex, a helpful, energetic AI assistant.
Answer the user's query using ONLY the provided database context.
If the context doesn't contain the answer, say you don't have that data in your current databanks.

User Query: {query}
Modality Routed: {modality}
Identified Entity: {entity}

Retrieved Context from DBs:
{context}

Response:"""
prompt = ChatPromptTemplate.from_template(template)
```

---

## 6. Error Handling & Edge Cases

*   **API Validation:** Handle cases where uploaded files are not valid images/audio. Use FastAPI's `HTTPException`.
*   **Missing Modalities:** If the user sends an empty request, return a 400 Bad Request.
*   **Database Connectivity:** If Neo4j or Chroma are down, the service should catch the connection error and return a 503 Service Unavailable with a clear message, rather than crashing the LangGraph execution.
*   **Entity Not Found:** If OpenCLIP identifies a sprite as "pikachu", but "pikachu" doesn't exist in Neo4j (due to ingestion failure), handle the empty Neo4j result gracefully in the `generator_node`.
*   **Gemini Rate Limits:** Implement basic retry logic (e.g., `tenacity`) around LLM calls to handle transient API errors or quota limits.

---

## 7. Deliverables Checklist

- [ ] `backend/` directory structured correctly with `pyproject.toml`
- [ ] FastAPI `main.py` created with the `POST /api/v1/query` endpoint
- [ ] Pydantic models defined for structured request/response
- [ ] LangGraph state, nodes, and conditional routing logic implemented
- [ ] Neo4j client built with Cypher queries for basic lookup and type effectiveness
- [ ] ChromaDB client built with OpenCLIP integration for image search
- [ ] Gemini 3 Flash integrated for both Audio identification and final answer generation
- [ ] Endpoint successfully tested with a text query (Graph Traversal)
- [ ] Endpoint successfully tested with an image upload (Vector Similarity)
- [ ] Endpoint successfully tested with an audio upload (Native Multimodal LLM)
- [ ] Response payload correctly includes both the natural language string and the `context_used` JSON object for the frontend.
