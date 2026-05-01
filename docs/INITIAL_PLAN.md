# ⚡ Project: Agentic Pokédex (Multi-Modal Graph RAG)

**Domain:** Gaming/Nostalgia (Generation 1 Pokémon)
**Tech Stack:** React (JS/Vite), FastAPI (`uv`), ChromaDB, Neo4j, LangGraph, Gemini 3 Flash.

## 📂 Repository Structure
Create this exact folder structure before doing anything else:
```text
agentic-pokedex/
├── docker-compose.yml
├── .env                  # (NEVER COMMIT THIS)
├── ingestion/            # Standalone python scripts to fetch PokeAPI -> Chroma/Neo4j
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml    # Managed by uv
│   └── main.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/              # React code
```

## 🐳 Phase 0: Infrastructure (Docker Compose)
We are using `alpine` for Node and `slim` for Python to keep image sizes microscopic and build times under 60 seconds. 

### `docker-compose.yml`
```yaml
services:
  frontend:
    build: 
      context: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - rag_network

  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - CHROMA_HOST=chromadb
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
    depends_on:
      - chromadb
      - neo4j
    networks:
      - rag_network

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000" # Mapped to 8001 on host to avoid FastAPI clash
    volumes:
      - chroma_data:/chroma/chroma
    networks:
      - rag_network

  neo4j:
    image: neo4j:5.12.0
    ports:
      - "7474:7474" # HTTP GUI
      - "7687:7687" # Bolt port
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j_data:/data
    networks:
      - rag_network

networks:
  rag_network:
    driver: bridge

volumes:
  chroma_data:
  neo4j_data:
```

### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

# Install system dependencies required for uv and ML building
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Install uv (The Rust-based blazing fast package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Sync dependencies instantly
RUN uv sync

COPY . .

# Expose port and run Uvicorn
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### `frontend/Dockerfile`
```dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files and install natively
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Expose Vite's default port
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

---

## 🧠 Phase 1: Data Ingestion
*Delegate this to your data person immediately.* 
Do not put this inside your FastAPI server. Write a script (`ingestion/populate.py`) that runs *once* locally to seed your databases.

1.  **Pull from PokeAPI:** Loop `1` to `151`.
    *   Grab the JSON: `[https://pokeapi.co/api/v2/pokemon/](https://pokeapi.co/api/v2/pokemon/){id}`
    *   Grab species lore: `[https://pokeapi.co/api/v2/pokemon-species/](https://pokeapi.co/api/v2/pokemon-species/){id}`
2.  **Seed Neo4j (Knowledge Graph):**
    *   Create `(p:Pokemon {name: "bulbasaur"})`
    *   Create `(t:Type {name: "grass"})`
    *   Link them: `(p)-[:HAS_TYPE]->(t)`
3.  **Seed ChromaDB (Vector Search):**
    *   **Text Collection:** Embed the Pokédex flavor text.
    *   **Image Collection:** Use Chroma's `OpenCLIP` embedding function. Pass the `sprites.front_default` URL to download the image, embed it, and store it with metadata `{"name": "bulbasaur"}`.

---

## ⚙️ Phase 2: The Agentic Backend
*Delegate this to your backend/LLM person.*
Use `uv add fastapi uvicorn langgraph langchain-google-genai neo4j chromadb python-multipart` to set up your environment.

Your `main.py` needs a single power-house endpoint:
```python
@app.post("/query")
async def process_multimodal_query(
    text: str = Form(None),
    image: UploadFile = File(None),
    audio: UploadFile = File(None)
):
    # LangGraph Router Logic:
    if image:
        # 1. Embed image with OpenCLIP
        # 2. Query Chroma Image Collection for nearest sprite
        # 3. Extract Pokemon Name -> Query Neo4j Graph for stats -> Pass to LLM
        pass
    
    elif audio:
        # 1. Pass .ogg directly to Gemini 1.5 Flash to identify the creature
        # 2. Use the returned name to hit the Graph DB -> Generate response
        pass
        
    elif text:
        # 1. Convert text to embeddings
        # 2. Check semantic similarity in Chroma
        # 3. Extract entities to traverse Neo4j relationships -> Generate response
        pass

    return {"response": llm_generated_text, "context_used": graph_and_vector_data}
```

---

## 💻 Phase 3: The Frontend
*Delegate to your UI person.* Keep it dead simple. 
Run `npm create vite@latest . -- --template react` inside the `frontend` folder.

1.  **Chat Pane (Left):** Standard message mapping. Needs buttons for text input, file upload (`input type="file" accept="image/*"`), and audio upload (`accept="audio/ogg,audio/mp3"`).
2.  **Pokédex Visor (Right):** A dynamic card that updates based on the JSON payload returned from your backend's `context_used` field. Show the sprite, the Graph relationships (Types, Evolutions), and the retrieved stats.

---

## 🎤 Phase 4: The 10-Minute Pitch Strategy
When you demo this tomorrow, hit these exact beats:

1.  **The Hook (1 min):** "Standard RAG is blind. It reads text but fails at complex relationships and visual/audio inputs. We built an Agentic Multi-Modal Graph RAG."
2.  **Architecture Slide (2 mins):** Show the flow: React UI ➡️ FastAPI ➡️ LangGraph Router ➡️ (ChromaDB for semantic/visual search OR Neo4j for relational traversal) ➡️ Gemini 1.5 Flash.
3.  **Literature Survey (2 mins):** Cite **"GraphRAG: Unlocking LLM Discovery on Narrative Private Data" (Edge et al., 2024)**. Explain how your Neo4j implementation mirrors their findings: Graph RAG solves the "connecting the dots" problem that vector databases fail at.
4.  **Live Demo (4 mins):**
    *   *Query 1 (Graph):* "Who is strong against Charizard?" (Watch the graph traverse Types).
    *   *Query 2 (Image):* Upload an image of Pikachu. (Watch OpenCLIP match the vector, extract the name, and pull the lore).
5.  **Challenges (1 min):** Be honest. Mention Docker networking hurdles, OpenCLIP latency, or parsing nested JSON from the PokéAPI. 

Run `docker-compose up --build -d` and let the containers spin. Time to code.