# Pokemon Data Ingestion Pipeline

This module fetches all 151 Gen 1 Pokemon from the PokéAPI and seeds them into Neo4j (Knowledge Graph) and ChromaDB (Vector Store).

## Prerequisites

1. Docker and docker-compose must be running
2. Neo4j and ChromaDB containers must be running

```bash
# Start the required services
docker-compose up -d neo4j chromadb
```

3. Create a `.env` file in the project root with the following variables:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CHROMA_HOST=localhost
CHROMA_PORT=8001
```

## Installation

```bash
cd ingestion
uv sync
```

## Usage

### Full Pipeline (Fetch + Seed)

```bash
uv run python populate.py
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--skip-fetch` | Skip API fetching, use cached JSON files only |
| `--neo4j-only` | Only seed Neo4j, skip ChromaDB |
| `--chroma-only` | Only seed ChromaDB, skip Neo4j |
| `--verify-only` | Only run verification queries, don't seed anything |
| `--clean` | Wipe existing data in both databases before seeding |

### Examples

```bash
# Re-seed only Neo4j (skip fetching)
uv run python populate.py --neo4j-only --skip-fetch

# Clean and re-seed everything
uv run python populate.py --clean

# Verify existing data without re-seeding
uv run python populate.py --verify-only
```

## Data Model

### Neo4j Nodes

- **Pokemon**: id, name, height, weight, stats, flavor_text, genus, color, etc.
- **Type**: 18 Pokemon types (fire, water, grass, etc.)
- **Ability**: Pokemon abilities
- **Move**: Learnable moves
- **Habitat**: Pokemon habitats
- **EggGroup**: Egg groups

### Neo4j Relationships

- `HAS_TYPE` - Pokemon has types (with slot property)
- `HAS_ABILITY` - Pokemon has abilities
- `EVOLVES_TO` - Pokemon evolution chains
- `IN_HABITAT` - Pokemon habitat
- `IN_EGG_GROUP` - Pokemon egg groups
- `CAN_LEARN` - Pokemon can learn moves
- `STRONG_AGAINST` - Type is super effective against
- `WEAK_AGAINST` - Type is not very effective against
- `RESISTANT_TO` - Type resists damage
- `IMMUNE_TO` - Type is immune to

### ChromaDB Collections

- **pokemon_text**: Semantic text search over Pokemon lore (flavor_text)
- **pokemon_images**: Visual similarity search using OpenCLIP embeddings

## Output

On successful completion, you'll see a summary:

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

## Caching

API responses are cached in `ingestion/.cache/` to allow resumption if the script crashes. Delete this directory to force a fresh fetch.

## First Run Notes

- The OpenCLIP embedding model (~400MB) will be downloaded on first run
- Image embedding is slow (several seconds per image on CPU)
- Total runtime: approximately 5-10 minutes depending on network speed