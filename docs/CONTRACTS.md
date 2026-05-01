# 🤝 Project Data Contracts & Schemas

**Goal:** This document serves as the single source of truth for all three developers (Data, Backend, Frontend). By adhering strictly to these names, schemas, and JSON structures, everyone can work in parallel without blocking each other.

---

## 1. Database Schema Contract (Data ➡️ Backend)

The **Data Engineer** guarantees these exact names will be populated into the databases. The **Backend Engineer** relies on these exact names for Cypher queries and Vector searches.

### 1.1 Neo4j (Knowledge Graph)

**Node Labels & Properties:**
*   `Pokemon`
    *   Properties: `id` (int), `name` (str), `hp` (int), `attack` (int), `defense` (int), `sp_atk` (int), `sp_def` (int), `speed` (int), `sprite_url` (str), `flavor_text` (str), `genus` (str), `height` (int), `weight` (int), `is_legendary` (bool)
*   `Type` (Property: `name` str)
*   `Ability` (Property: `name` str)
*   `EggGroup` (Property: `name` str)
*   `Habitat` (Property: `name` str)
*   `Move` (Property: `name` str)

**Relationship Types:**
*   `(Pokemon)-[:HAS_TYPE {slot: int}]->(Type)`
*   `(Pokemon)-[:EVOLVES_TO]->(Pokemon)`
*   `(Pokemon)-[:HAS_ABILITY {is_hidden: bool}]->(Ability)`
*   `(Pokemon)-[:IN_HABITAT]->(Habitat)`
*   `(Pokemon)-[:IN_EGG_GROUP]->(EggGroup)`
*   `(Pokemon)-[:CAN_LEARN]->(Move)`
*   `(Type)-[:STRONG_AGAINST]->(Type)`
*   `(Type)-[:WEAK_AGAINST]->(Type)`
*   `(Type)-[:RESISTANT_TO]->(Type)`
*   `(Type)-[:IMMUNE_TO]->(Type)`

### 1.2 ChromaDB (Vector Store)

**Collection 1: Semantic Text Search**
*   **Collection Name:** `pokemon_text`
*   **Embedding Function:** Chroma Default (`all-MiniLM-L6-v2`)
*   **Metadata Keys Provided:** `name`, `id`, `types`, `genus`, `is_legendary`

**Collection 2: Image Similarity Search**
*   **Collection Name:** `pokemon_images`
*   **Embedding Function:** OpenCLIP (Model: `ViT-B-32`, Pretrained: `laion2b_s34b_b79k`) *⚠️ Both Ingestion & Backend must use this exact config!*
*   **Metadata Keys Provided:** `name`, `id`, `sprite_url`

---

## 2. API Contract (Backend ➡️ Frontend)

The **Backend Engineer** guarantees this exact JSON structure will be returned. The **Frontend Engineer** can use this mock payload to build the React UI immediately.

### 2.1 The Request (Frontend to Backend)

*   **Endpoint:** `POST /api/v1/query`
*   **Content-Type:** `multipart/form-data`
*   **Fields:**
    *   `text` (Optional String)
    *   `image` (Optional File: `image/png`, `image/jpeg`)
    *   `audio` (Optional File: `audio/ogg`, `audio/mpeg`)

### 2.2 The Response (Backend to Frontend)

**Content-Type:** `application/json`

```json
{
  "response": "Charizard is a Fire/Flying type. It is incredibly strong, but has a massive weakness to Rock and Water types.",
  "modality_routed": "text",
  "context_used": {
    "pokemon_name": "Charizard",
    "sprite_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/6.png",
    "types": [
      "fire",
      "flying"
    ],
    "stats": {
      "hp": 78,
      "attack": 84,
      "defense": 78,
      "sp_atk": 109,
      "sp_def": 85,
      "speed": 100
    },
    "graph_relationships": [
      "Evolves from Charmeleon",
      "Weak against Rock, Water, Electric",
      "Strong against Grass, Bug"
    ]
  }
}
```

### 2.3 Frontend Fallback Rules
*   If `context_used` is `null` (e.g. the user asks a non-Pokémon question), the frontend should hide the "Pokédex Visor" panel and only show the chat response.
*   If `sprite_url` is `null`, display a generic Pokeball placeholder image.
