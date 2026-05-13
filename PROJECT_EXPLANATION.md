# Agentic Pokédex: Comprehensive Project Overview

This document provides a deep dive into the **Agentic Pokédex** project. It is designed to serve as a complete end-to-end explanation of the architecture, data flows, and implementation details across the entire system.

## 1. Project Introduction
The **Agentic Pokédex** is a state-of-the-art Multi-Modal Graph RAG (Retrieval-Augmented Generation) application centered around Generation 1 Pokémon. Unlike standard text-based RAG, this system can seamlessly process **text**, **images**, and **audio** to identify Pokémon, traverse complex relationships (such as type effectiveness and evolution chains), and present the data dynamically to the user.

It leverages:
- **React (Vite) + TailwindCSS** for a premium Frontend UI.
- **FastAPI + LangGraph** for the intelligent Backend routing and orchestration.
- **Gemini 3 Flash** as the core LLM for inference and multi-modal synthesis.
- **Neo4j** as the Knowledge Graph for structured relationship traversal.
- **ChromaDB** as the Vector Store for semantic text and visual similarity searches.

---

## 2. Phase 1: Data Ingestion Pipeline (`ingestion/`)
The ingestion phase ensures that the databases are seeded before the backend server runs. It is executed via standalone Python scripts managed by `uv`.

### 2.1 Fetching Data
The `populate.py` orchestrator hits the **PokéAPI** to fetch all 151 Generation 1 Pokémon. It pulls down core statistics, flavor text (lore), abilities, and evolution chains. It also calculates complex type effectiveness (what types are strong/weak against others) and downloads official sprite images.

### 2.2 Seeding Neo4j (Knowledge Graph)
Neo4j acts as the structured memory for the agent. It stores nodes for `Pokemon`, `Type`, `Ability`, `Move`, `Habitat`, and `EggGroup`.
It maps critical relationships such as:
- `(Pokemon)-[:HAS_TYPE]->(Type)`
- `(Pokemon)-[:EVOLVES_TO]->(Pokemon)`
- `(Type)-[:STRONG_AGAINST]->(Type)`

This is essential for the AI to deterministically answer questions like, *"What is super effective against Charizard?"* without hallucinating.

### 2.3 Seeding ChromaDB (Vector Store)
ChromaDB handles fuzzy searches using embeddings. It contains two distinct collections:
1. **`pokemon_text`**: Embeds Pokédex lore (flavor text) using standard text embedding models (`all-MiniLM-L6-v2`).
2. **`pokemon_images`**: Uses **OpenCLIP** (`ViT-B-32`) to embed the raw pixels of the downloaded Pokémon sprites. This powers the visual similarity search.

---

## 3. Phase 2: The Agentic Backend (`backend/`)
The Backend is the "brain" of the operation. Written in FastAPI, it exposes a single powerhouse endpoint: `POST /api/v1/query`.

### 3.1 LangGraph Orchestration
The backend uses **LangGraph** to create a stateful routing workflow based on the modality of the user's input:

- **Router Node**: Inspects the incoming payload (text, image file, or audio file) and routes it.
- **Audio Handler**: Passes the raw audio `.ogg` file natively to Gemini 1.5 Flash to identify the Pokémon by its cry. It extracts the name and queries Neo4j for its stats.
- **Image Handler**: Takes an uploaded image, embeds it using **OpenCLIP**, and queries the ChromaDB `pokemon_images` collection to find the most visually similar sprite. It uses the matched name to query Neo4j.
- **Text Handler**: Uses an LLM to extract the user's intent. Based on the intent, it executes a Cypher query on Neo4j (e.g., for type effectiveness) or a semantic search on ChromaDB.
- **Generator Node**: Takes the retrieved context from the previous nodes and the original query, prompting Gemini 3 Flash to synthesize a final natural language response.

### 3.2 Standardized Data Contracts
The backend always responds with a strict JSON format containing both the natural language `response` and a `context_used` object (containing `stats`, `types`, `sprite_url`, etc.). This strictly defined contract allows the frontend to predictably render visual data.

---

## 4. Phase 3: The Frontend UI (`frontend/`)
The Frontend is a visually rich, responsive Single Page Application (SPA) built with React and TailwindCSS. It utilizes a split-pane layout to balance conversational AI with data visualization.

### 4.1 Chat Interface (Left Pane)
- A highly interactive messaging window where users can type text, upload images (via a camera button), and record audio natively in the browser using the `MediaRecorder` API.
- AI responses are rendered using `react-markdown`.

### 4.2 Pokédex Visor (Right Pane)
- A dynamic, glassmorphism-styled data card. 
- It acts as the visual counterpart to the LLM's response. Whenever the backend returns the `context_used` payload, the Visor updates to display the identified Pokémon's sprite, its radar chart of stats (HP, Attack, Speed, etc.), its types, and its evolutionary/type relationships.
- If the query is conversational and lacks specific Pokémon context, the Visor gracefully hides itself.

---

## 5. End-to-End User Flow Example

1. **User Action**: The user clicks the microphone button on the frontend and says, *"Show me the stats for the electric mouse."* 
2. **Frontend**: Captures the audio blob and sends it as `multipart/form-data` to `/api/v1/query`.
3. **Backend Router**: LangGraph routes the payload to the Audio Handler.
4. **LLM Identification**: Gemini processes the audio and identifies "Pikachu".
5. **Database Retrieval**: The backend runs a Cypher query on Neo4j for Pikachu, pulling its stats, sprite URL, and types.
6. **Synthesis**: Gemini generates a text response: *"Pikachu is an Electric-type Pokémon known for its speed..."*
7. **Frontend Update**: 
   - The chat interface displays the text response.
   - The Pokédex Visor lights up, displaying Pikachu's sprite, an Electric-type badge, and a graph of its stats.

## Conclusion
The Agentic Pokédex demonstrates how multi-modal inputs, graph databases, and vector stores can be orchestrated by an LLM-powered router to create a deeply knowledgeable, highly interactive application that surpasses the limitations of standard text-only RAG.
