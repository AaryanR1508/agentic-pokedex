# ⚡ Phase 1: Data Ingestion Pipeline — Implementation Plan

**Owner:** Data Engineer / Data Person  
**Goal:** Build a standalone, one-shot ingestion script that fetches all 151 Gen 1 Pokémon from the PokéAPI and seeds two databases — **Neo4j** (Knowledge Graph) and **ChromaDB** (Vector Store) — so that the backend (Phase 2) has fully populated, query-ready data stores on first boot.

> [!IMPORTANT]
> This script is **not** part of the FastAPI server. It lives in the `ingestion/` directory and is designed to be run **once** (or re-run idempotently) to populate the databases before the application goes live.

---

## 1. Environment & Tooling Setup

### 1.1 Python Environment

- Use **`uv`** as the package manager (Rust-based, fast installs).
- Create a dedicated `pyproject.toml` inside `ingestion/` (this is separate from the backend's `pyproject.toml`).
- Target **Python 3.11** to match the backend Dockerfile.

### 1.2 Required Dependencies

The following packages must be added via `uv add`:

| Package | Purpose |
|---|---|
| `httpx` | Async HTTP client for PokéAPI requests (preferred over `requests` for async support) |
| `neo4j` | Official Neo4j Python driver for Bolt protocol connections |
| `chromadb` | ChromaDB client for vector store operations |
| `chromadb[openclip]` or `open-clip-torch` | OpenCLIP embedding function for image embeddings |
| `Pillow` | Image downloading and processing before embedding |
| `python-dotenv` | Loading `.env` variables (API keys, DB URIs) |
| `rich` | Pretty console output, progress bars, and logging during ingestion |
| `tenacity` | Retry logic with exponential backoff for API calls |

### 1.3 Environment Variables

The script must read from the project root `.env` file. Required variables:

| Variable | Example Value | Notes |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | When running locally outside Docker |
| `NEO4J_USER` | `neo4j` | Default Neo4j user |
| `NEO4J_PASSWORD` | `password` | As defined in `docker-compose.yml` |
| `CHROMA_HOST` | `localhost` | ChromaDB host (mapped to port 8001 on host) |
| `CHROMA_PORT` | `8001` | Host-mapped port from docker-compose |

### 1.4 Folder Structure

```text
ingestion/
├── pyproject.toml          # uv-managed dependencies for ingestion
├── .python-version         # Pin to 3.11
├── populate.py             # Main entry point — orchestrates the full pipeline
├── fetch.py                # All PokéAPI data fetching logic
├── seed_neo4j.py           # Neo4j graph seeding logic
├── seed_chroma.py          # ChromaDB vector store seeding logic
├── models.py               # Pydantic models for parsed Pokémon data
├── config.py               # Environment variable loading and validation
└── README.md               # Instructions on how to run the ingestion
```

> [!TIP]
> Splitting into modules (`fetch.py`, `seed_neo4j.py`, `seed_chroma.py`) instead of one monolithic script makes it much easier to test individual stages and re-run only the part that failed.

---

## 2. Feature: PokéAPI Data Fetching (`fetch.py`)

### 2.1 Endpoints to Hit

For each Pokémon ID from **1 to 151**, two API calls must be made:

1. **Pokémon Data Endpoint:**  
   `GET https://pokeapi.co/api/v2/pokemon/{id}`  
   Returns: name, types, stats, abilities, sprites, height, weight, moves, etc.

2. **Species / Lore Endpoint:**  
   `GET https://pokeapi.co/api/v2/pokemon-species/{id}`  
   Returns: flavor text entries, genera, evolution chain URL, habitat, color, generation, egg groups, growth rate, etc.

This means **302 total API calls** minimum (151 × 2).

### 2.2 Data to Extract Per Pokémon

From the **`/pokemon/{id}`** response, extract:

| Field | JSON Path | Notes |
|---|---|---|
| `id` | `.id` | National Pokédex number (1–151) |
| `name` | `.name` | Lowercase canonical name (e.g., `"bulbasaur"`) |
| `types` | `.types[].type.name` | List of type strings, e.g., `["grass", "poison"]` |
| `stats` | `.stats[]` | Array of `{stat.name, base_stat}` — HP, Attack, Defense, Sp. Atk, Sp. Def, Speed |
| `abilities` | `.abilities[].ability.name` | List of ability names |
| `height` | `.height` | In decimetres |
| `weight` | `.weight` | In hectograms |
| `sprite_url` | `.sprites.front_default` | URL to the official front-facing sprite PNG |
| `sprite_shiny_url` | `.sprites.front_shiny` | URL to the shiny variant (optional, nice-to-have for frontend) |
| `moves` | `.moves[].move.name` | Full list of learnable moves — store only the names |
| `base_experience` | `.base_experience` | Base XP yield |

From the **`/pokemon-species/{id}`** response, extract:

| Field | JSON Path | Notes |
|---|---|---|
| `flavor_text` | `.flavor_text_entries[]` | Filter for `language.name == "en"` and pick the **latest version's** entry. Clean up `\n`, `\f`, and other control characters. |
| `genus` | `.genera[]` | Filter for English — e.g., `"Seed Pokémon"` |
| `evolution_chain_url` | `.evolution_chain.url` | URL to the evolution chain resource — must be fetched separately (see §2.3) |
| `habitat` | `.habitat.name` | Can be `null` for some Pokémon |
| `color` | `.color.name` | The Pokémon's color category |
| `is_legendary` | `.is_legendary` | Boolean |
| `is_mythical` | `.is_mythical` | Boolean |
| `egg_groups` | `.egg_groups[].name` | List of egg group names |
| `growth_rate` | `.growth_rate.name` | e.g., `"medium-slow"` |

### 2.3 Evolution Chain Resolution

The species endpoint gives an `evolution_chain.url` (e.g., `https://pokeapi.co/api/v2/evolution-chain/1/`). This must be fetched **separately** to build the `EVOLVES_TO` relationships for Neo4j.

The evolution chain JSON is **recursive/nested**:

```
chain.species.name → chain.evolves_to[0].species.name → chain.evolves_to[0].evolves_to[0].species.name
```

You need to **recursively walk** this tree and produce flat pairs like:
- `("bulbasaur", "ivysaur")`
- `("ivysaur", "venusaur")`

> [!WARNING]
> Many Pokémon share the same evolution chain URL. For example, Bulbasaur, Ivysaur, and Venusaur all point to chain ID 1. **Cache** already-fetched chain URLs to avoid redundant API calls. There are approximately **78 unique chains** for Gen 1 — not 151.

**Branching evolutions** exist in Gen 1:
- Eevee → Vaporeon / Jolteon / Flareon (chain branches into 3)
- These must all be captured as separate `EVOLVES_TO` edges.

### 2.4 Sprite Image Downloading

For every Pokémon, download the `sprites.front_default` PNG to a local temp directory or keep it in memory as bytes. This image will be passed to ChromaDB's OpenCLIP embedding function.

- Some sprites may be `null` (unlikely for Gen 1, but handle it).
- Download images concurrently but respect rate limits.
- Store the raw bytes or a file path — ChromaDB's `OpenCLIPEmbeddingFunction` can accept image file paths or PIL Image objects.

### 2.5 Rate Limiting & Resilience

PokéAPI is free and does not require authentication, but it does have fair-use rate limits.

- **Implement async fetching** using `httpx.AsyncClient` with a concurrency semaphore (limit to **~10 concurrent requests**).
- **Retry with exponential backoff** using `tenacity` — retry on HTTP 429 (rate limit) and 5xx errors, up to 5 attempts.
- **Cache responses** locally as JSON files in an `ingestion/.cache/` directory so that if the script crashes halfway, it can resume from cache rather than re-fetching everything.
- **Progress tracking** — use `rich.progress` to display a live progress bar showing `[42/151] Fetching Pikachu...`.

### 2.6 Pydantic Data Model (`models.py`)

Define a `PokemonData` Pydantic model that holds all extracted fields in a clean, validated structure. This model is the single source of truth passed to both the Neo4j and ChromaDB seeding functions.

```
PokemonData:
  - id: int
  - name: str
  - types: list[str]
  - stats: dict[str, int]  (e.g., {"hp": 45, "attack": 49, ...})
  - abilities: list[str]
  - height: int
  - weight: int
  - sprite_url: str | None
  - sprite_bytes: bytes | None
  - moves: list[str]
  - base_experience: int | None
  - flavor_text: str
  - genus: str
  - evolution_chain: list[tuple[str, str]]  (pairs of evolves_from → evolves_to)
  - habitat: str | None
  - color: str
  - is_legendary: bool
  - is_mythical: bool
  - egg_groups: list[str]
  - growth_rate: str
```

---

## 3. Feature: Neo4j Knowledge Graph Seeding (`seed_neo4j.py`)

### 3.1 Graph Data Model

The Neo4j graph should contain the following **node labels** and **relationship types**:

#### Nodes

| Label | Properties | Example |
|---|---|---|
| `Pokemon` | `name`, `id`, `height`, `weight`, `base_experience`, `flavor_text`, `genus`, `color`, `is_legendary`, `is_mythical`, `growth_rate`, `hp`, `attack`, `defense`, `sp_atk`, `sp_def`, `speed`, `sprite_url` | `(:Pokemon {name: "charizard", id: 6, hp: 78, attack: 84, ...})` |
| `Type` | `name` | `(:Type {name: "fire"})` |
| `Ability` | `name` | `(:Ability {name: "blaze"})` |
| `EggGroup` | `name` | `(:EggGroup {name: "monster"})` |
| `Habitat` | `name` | `(:Habitat {name: "mountain"})` |
| `Move` | `name` | `(:Move {name: "flamethrower"})` |

#### Relationships

| Relationship | From | To | Properties | Example |
|---|---|---|---|---|
| `HAS_TYPE` | `Pokemon` | `Type` | `slot` (1 = primary, 2 = secondary) | `(charizard)-[:HAS_TYPE {slot: 1}]->(fire)` |
| `HAS_ABILITY` | `Pokemon` | `Ability` | `is_hidden` (boolean) | `(charizard)-[:HAS_ABILITY {is_hidden: false}]->(blaze)` |
| `EVOLVES_TO` | `Pokemon` | `Pokemon` | *(none or `trigger` if you want)* | `(charmeleon)-[:EVOLVES_TO]->(charizard)` |
| `IN_HABITAT` | `Pokemon` | `Habitat` | — | `(charizard)-[:IN_HABITAT]->(mountain)` |
| `IN_EGG_GROUP` | `Pokemon` | `EggGroup` | — | `(charizard)-[:IN_EGG_GROUP]->(monster)` |
| `CAN_LEARN` | `Pokemon` | `Move` | — | `(charizard)-[:CAN_LEARN]->(flamethrower)` |
| `STRONG_AGAINST` | `Type` | `Type` | — | `(water)-[:STRONG_AGAINST]->(fire)` |
| `WEAK_AGAINST` | `Type` | `Type` | — | `(fire)-[:WEAK_AGAINST]->(water)` |
| `RESISTANT_TO` | `Type` | `Type` | — | `(fire)-[:RESISTANT_TO]->(grass)` |
| `IMMUNE_TO` | `Type` | `Type` | — | `(ground)-[:IMMUNE_TO]->(electric)` |

### 3.2 Type Effectiveness Matrix

> [!IMPORTANT]
> This is **critical for the demo query** ("Who is strong against Charizard?"). The backend must be able to traverse `Type` relationships to answer questions about strengths and weaknesses.

The PokeAPI provides type effectiveness data at:  
`GET https://pokeapi.co/api/v2/type/{id_or_name}`

For each of the **18 types** (even though Gen 1 only has 15, include all 18 for completeness), fetch the damage relations:

- `damage_relations.double_damage_to[]` → create `STRONG_AGAINST` edges
- `damage_relations.double_damage_from[]` → create `WEAK_AGAINST` edges
- `damage_relations.half_damage_to[]` → create `RESISTANT_TO` edges (from the target's perspective, the attacking type is "not very effective")
- `damage_relations.no_damage_to[]` → create `IMMUNE_TO` edges

This produces a fully traversable type-effectiveness sub-graph. The backend can then answer "What is super effective against Fire/Flying?" by traversing Charizard's types and following `WEAK_AGAINST` edges.

### 3.3 Constraints & Indexes

Before inserting any data, create **uniqueness constraints** in Neo4j:

- `CREATE CONSTRAINT FOR (p:Pokemon) REQUIRE p.name IS UNIQUE`
- `CREATE CONSTRAINT FOR (t:Type) REQUIRE t.name IS UNIQUE`
- `CREATE CONSTRAINT FOR (a:Ability) REQUIRE a.name IS UNIQUE`
- `CREATE CONSTRAINT FOR (h:Habitat) REQUIRE h.name IS UNIQUE`
- `CREATE CONSTRAINT FOR (e:EggGroup) REQUIRE e.name IS UNIQUE`
- `CREATE CONSTRAINT FOR (m:Move) REQUIRE m.name IS UNIQUE`

These also double as indexes, speeding up `MERGE` operations.

### 3.4 Idempotent Insertion Strategy

Use **`MERGE`** instead of `CREATE` for all node and relationship creation. This ensures the script can be re-run without producing duplicates.

Pattern:
```
MERGE (p:Pokemon {name: $name})
SET p.id = $id, p.hp = $hp, ...
```

### 3.5 Batch Operations

- Use Neo4j's **`UNWIND`** clause to batch-insert data rather than running 151 individual transactions.
- Group operations: create all `Type` nodes first, then all `Pokemon` nodes, then all relationships.
- Use a single driver session with explicit transactions for atomicity.

### 3.6 Connection Management

- Connect using the official `neo4j` Python driver with `GraphDatabase.driver()`.
- Verify connectivity on startup with `driver.verify_connectivity()`.
- Close the driver cleanly in a `finally` block or context manager.

---

## 4. Feature: ChromaDB Vector Store Seeding (`seed_chroma.py`)

### 4.1 Two Separate Collections

ChromaDB must be seeded with **two distinct collections**:

#### Collection 1: `pokemon_text`

- **Purpose:** Semantic text search over Pokédex lore/flavor text.
- **Embedding:** Use ChromaDB's **default embedding function** (Sentence Transformers / `all-MiniLM-L6-v2`) or explicitly set one.
- **Documents:** The cleaned `flavor_text` string for each Pokémon.
- **Metadata per document:**
  - `name`: Pokémon name (e.g., `"bulbasaur"`)
  - `id`: Pokédex number
  - `types`: Comma-separated type string (e.g., `"grass,poison"`)
  - `genus`: e.g., `"Seed Pokémon"`
  - `is_legendary`: boolean
- **IDs:** Use the Pokémon name as the document ID (e.g., `"bulbasaur"`) for easy deduplication.

#### Collection 2: `pokemon_images`

- **Purpose:** Visual similarity search — when a user uploads an image of a Pokémon, find the closest matching sprite.
- **Embedding Function:** **`OpenCLIPEmbeddingFunction`** from `chromadb.utils.embedding_functions`.
  - Model: `ViT-B-32` (good balance of speed and accuracy)
  - Pretrained: `laion2b_s34b_b79k`
- **Data:** The actual sprite **image bytes** (PNG) for each Pokémon.
- **Metadata per image:**
  - `name`: Pokémon name
  - `id`: Pokédex number
  - `sprite_url`: Original URL for reference
- **IDs:** Use the Pokémon name as the document ID.

> [!WARNING]
> The OpenCLIP embedding model is **large** (~400MB+). The first run will download it. Make sure the environment has sufficient disk space and a stable internet connection. Consider adding a note about this in the ingestion README.

### 4.2 Image Handling

- Download each sprite PNG from the URL provided by PokeAPI.
- Convert to a PIL Image or pass raw bytes, depending on what the ChromaDB OpenCLIP embedding function expects.
- Handle missing sprites gracefully — log a warning and skip the Pokémon in the image collection (but still add its text).
- Consider resizing images to a consistent dimension (e.g., 96×96) before embedding to normalize input, though OpenCLIP handles variable sizes.

### 4.3 Text Cleaning

The `flavor_text` field from PokéAPI often contains:
- Form feed characters (`\f`)
- Newlines mid-word (`\n`)
- Soft hyphens and other Unicode artifacts
- Version-specific duplicates

Implement a cleaning function that:
1. Replaces `\f` and `\n` with spaces
2. Collapses multiple whitespace into single spaces
3. Strips leading/trailing whitespace
4. Picks only the **most recent English-language** flavor text entry (e.g., from the latest game version)

### 4.4 Batch Upsert

- Use ChromaDB's `collection.upsert()` (not `add()`) so the script is idempotent.
- Batch in groups of ~20–30 to avoid memory spikes, especially for image embeddings.
- Display progress during embedding — image embedding is **slow** (several seconds per image on CPU).

### 4.5 Verification Queries

After seeding, run quick sanity checks:
- `pokemon_text.count()` should return **151**
- `pokemon_images.count()` should return **~151** (minus any with missing sprites)
- Run a test query: `pokemon_text.query(query_texts=["a fire-breathing dragon"], n_results=3)` and verify that Charizard/Charmander appear in results.
- Run a test image query with one of the downloaded sprites and verify it returns the correct Pokémon as the top match.

---

## 5. Feature: Main Orchestrator (`populate.py`)

### 5.1 Execution Flow

The main script ties everything together in this order:

```
1. Load environment variables (config.py)
2. Verify Neo4j connectivity
3. Verify ChromaDB connectivity
4. Fetch all 151 Pokémon from PokéAPI (with caching)
5. Fetch all evolution chains (deduplicated)
6. Fetch type effectiveness data (18 types)
7. Parse and validate all data into PokemonData models
8. Seed Neo4j:
   a. Create constraints/indexes
   b. Create Type nodes + type effectiveness relationships
   c. Create Pokemon nodes
   d. Create Ability, Habitat, EggGroup, Move nodes
   e. Create all relationships
   f. Create EVOLVES_TO relationships
9. Seed ChromaDB:
   a. Create/get pokemon_text collection
   b. Upsert all text documents with embeddings
   c. Create/get pokemon_images collection (with OpenCLIP)
   d. Upsert all image embeddings
10. Run verification queries on both databases
11. Print summary report
```

### 5.2 CLI Interface

Add basic command-line argument support (using `argparse` or just simple flags):

| Flag | Behavior |
|---|---|
| `--skip-fetch` | Skip API fetching, use cached JSON files only |
| `--neo4j-only` | Only seed Neo4j, skip ChromaDB |
| `--chroma-only` | Only seed ChromaDB, skip Neo4j |
| `--verify-only` | Only run verification queries, don't seed anything |
| `--clean` | Wipe existing data in both databases before seeding |

### 5.3 Logging & Output

- Use `rich` for colored console output with structured panels.
- Log every major step with timestamps.
- At the end, print a summary table:

```
┌─────────────────────────────────────────┐
│         Ingestion Complete ✅           │
├─────────────────┬───────────────────────┤
│ Pokémon Fetched │ 151                   │
│ Neo4j Nodes     │ 523                   │
│ Neo4j Edges     │ 1,847                 │
│ Chroma Texts    │ 151                   │
│ Chroma Images   │ 151                   │
│ Time Elapsed    │ 3m 42s                │
└─────────────────┴───────────────────────┘
```

---

## 6. Error Handling & Edge Cases

### 6.1 Known PokéAPI Quirks

| Issue | Handling |
|---|---|
| Some Gen 1 Pokémon have `null` habitats | Store `habitat` as `None`; skip creating the `IN_HABITAT` relationship |
| Flavor text has Unicode control characters | Clean aggressively (see §4.3) |
| `MissingNo.`-style edge cases | Only fetch IDs 1–151, no need to worry about glitch Pokémon |
| Some Pokémon have hidden abilities added in later gens | Still include them — they're part of the canonical data |
| Evolution chain for Eevee branches 3 ways | Recursive parser must handle branching (see §2.3) |
| `sprites.front_default` can theoretically be `null` | Log warning, skip image embedding for that Pokémon |

### 6.2 Database Connectivity Failures

- If Neo4j is unreachable on startup, print a clear error message: *"Neo4j is not reachable at bolt://localhost:7687. Did you run `docker-compose up neo4j`?"*
- Same for ChromaDB: *"ChromaDB is not reachable at http://localhost:8001."*
- Do **not** silently fail — exit with a non-zero code.

### 6.3 Partial Failure Recovery

- The caching layer (§2.5) ensures API data doesn't need to be re-fetched.
- Neo4j `MERGE` operations ensure re-runs don't duplicate nodes.
- ChromaDB `upsert()` ensures re-runs don't duplicate documents.
- The `--neo4j-only` / `--chroma-only` flags allow re-running only the failed stage.

---

## 7. Testing Plan

### 7.1 Unit Tests

| What to Test | How |
|---|---|
| PokéAPI JSON parsing logic | Mock API responses with saved JSON fixtures; verify `PokemonData` model is correctly populated |
| Evolution chain recursive parser | Test with Eevee's branching chain and a simple linear chain (Charmander → Charmeleon → Charizard) |
| Flavor text cleaning function | Feed in raw strings with `\f`, `\n`, etc.; verify clean output |
| Type effectiveness edge creation | Verify that fetching the "fire" type produces correct `STRONG_AGAINST` / `WEAK_AGAINST` pairs |

### 7.2 Integration Tests (Require Docker)

| What to Test | How |
|---|---|
| Neo4j seeding | Run the seeder against a live Neo4j container; query node counts and relationship counts |
| ChromaDB seeding | Run the seeder against a live ChromaDB container; verify collection counts and run a test query |
| Full pipeline | Run `populate.py` end-to-end; verify both databases are populated correctly |

### 7.3 Smoke Test Script

Create a `ingestion/verify.py` that connects to both databases and runs the demo queries that will be used in the Phase 4 presentation:

1. **Graph traversal:** *"What types are strong against Charizard?"* — Query Neo4j for Charizard's types, follow `WEAK_AGAINST` edges, return the attacking types.
2. **Text search:** *"A fire-breathing dragon"* — Query ChromaDB `pokemon_text` collection, verify Charizard/Charmander are in top results.
3. **Image search:** Pass Pikachu's sprite to `pokemon_images` collection, verify Pikachu is the #1 result.

---

## 8. Deliverables Checklist

When Phase 1 is complete, the following must be true:

- [ ] `ingestion/` directory exists with all module files
- [ ] `pyproject.toml` has all dependencies and can be installed with `uv sync`
- [ ] `populate.py` runs successfully with `uv run python populate.py`
- [ ] Neo4j contains **151 Pokemon nodes**, **18 Type nodes**, all relationship types described in §3.1
- [ ] Neo4j type effectiveness sub-graph is fully populated (all `STRONG_AGAINST`, `WEAK_AGAINST`, `RESISTANT_TO`, `IMMUNE_TO` edges)
- [ ] Neo4j evolution chains are correct (e.g., querying Charmander's chain returns Charmander → Charmeleon → Charizard)
- [ ] ChromaDB `pokemon_text` collection has **151 documents**
- [ ] ChromaDB `pokemon_images` collection has **~151 documents** with OpenCLIP embeddings
- [ ] A text query for "electric mouse" returns Pikachu as a top result
- [ ] An image query with Pikachu's sprite returns Pikachu as the #1 match
- [ ] Script is **idempotent** — running it twice produces no duplicates
- [ ] Script handles network errors gracefully with retries and caching
- [ ] `ingestion/README.md` documents how to run the script, prerequisites, and expected output

---

## 9. Coordination Notes for Phase 2 & 3

### What Phase 2 (Backend) Needs From You

The backend developer needs to know:

1. **Collection names:** `pokemon_text` and `pokemon_images` — these are hardcoded in the backend's ChromaDB queries.
2. **Embedding function for images:** The backend must use the **same** `OpenCLIPEmbeddingFunction` with the **same model** (`ViT-B-32`, `laion2b_s34b_b79k`) when embedding user-uploaded images for similarity search. If the embedding functions don't match, similarity search will return garbage.
3. **Neo4j schema:** The node labels (`Pokemon`, `Type`, `Ability`, etc.) and relationship types (`HAS_TYPE`, `EVOLVES_TO`, `STRONG_AGAINST`, etc.) must be documented and frozen before the backend starts writing Cypher queries.
4. **Metadata fields in ChromaDB:** The backend will filter by metadata (e.g., `where={"name": "pikachu"}`), so the metadata schema must be agreed upon.

### What Phase 3 (Frontend) Needs From You

The frontend developer needs:

1. **Sprite URLs stored in Neo4j:** The frontend will display the Pokémon sprite on the "Pokédex Visor" card. The `sprite_url` field on the `Pokemon` node will be used for this.
2. **Stat names:** Confirm the exact stat key names (`hp`, `attack`, `defense`, `sp_atk`, `sp_def`, `speed`) so the frontend can render a stats radar chart or bar chart.
3. **Sample Neo4j query results:** Provide example JSON payloads that the backend would return after querying Neo4j, so the frontend can start building the UI against mock data.

---

## 10. Estimated Timeline

| Task | Estimated Effort |
|---|---|
| Environment setup + folder structure | 30 min |
| PokéAPI fetching with caching | 2–3 hours |
| Pydantic models + data parsing | 1 hour |
| Neo4j schema design + seeding | 2–3 hours |
| Type effectiveness matrix | 1 hour |
| ChromaDB text collection seeding | 1 hour |
| ChromaDB image collection (OpenCLIP) | 2 hours (including model download time) |
| Verification queries + smoke tests | 1 hour |
| Error handling, retries, polish | 1 hour |
| Documentation (README) | 30 min |
| **Total** | **~12–14 hours** |
