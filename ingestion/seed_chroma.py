import io
from typing import Optional

import chromadb
import numpy as np
from chromadb.utils import embedding_functions
from PIL import Image

from config import get_chroma_config
from models import PokemonData


class ChromaSeeder:
    def __init__(self, host: str, port: int):
        self.client = chromadb.HttpClient(host=host, port=port)
        self.text_collection = None
        self.image_collection = None
        self._verify_connectivity()

    def _verify_connectivity(self):
        try:
            self.client.heartbeat()
            print("✓ ChromaDB connection verified")
        except Exception as e:
            raise RuntimeError(f"ChromaDB is not reachable: {e}")

    def create_collections(self):
        openclip_ef = embedding_functions.OpenCLIPEmbeddingFunction(
            model_name="ViT-B-32",
            checkpoint="laion2b_s34b_b79k",
        )

        self.text_collection = self.client.get_or_create_collection(
            name="pokemon_text",
        )

        self.image_collection = self.client.get_or_create_collection(
            name="pokemon_images",
            embedding_function=openclip_ef,
        )

    def clear_collections(self):
        try:
            self.client.delete_collection("pokemon_text")
        except Exception:
            pass
        try:
            self.client.delete_collection("pokemon_images")
        except Exception:
            pass

    def seed_text_collection(self, pokemon_list: list[PokemonData]):
        if not self.text_collection:
            self.create_collections()

        print(f"Seeding text collection with {len(pokemon_list)} documents...")

        ids = []
        documents = []
        metadatas = []

        for pokemon in pokemon_list:
            ids.append(pokemon.name)
            documents.append(pokemon.flavor_text)
            metadatas.append({
                "name": pokemon.name,
                "id": pokemon.id,
                "types": ",".join(pokemon.types),
                "genus": pokemon.genus,
                "is_legendary": pokemon.is_legendary,
            })

        batch_size = 30
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            self.text_collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
            )
            print(f"  Seeded {min(i + batch_size, len(ids))}/{len(ids)} text documents")

        print("✓ Text collection seeding complete")

    def seed_image_collection(self, pokemon_list: list[PokemonData]):
        if not self.image_collection:
            self.create_collections()

        print(f"Seeding image collection with {len(pokemon_list)} images...")

        ids = []
        images = []
        metadatas = []

        for pokemon in pokemon_list:
            if pokemon.sprite_bytes:
                ids.append(pokemon.name)
                img = Image.open(io.BytesIO(pokemon.sprite_bytes))
                images.append(np.array(img))
                metadatas.append({
                    "name": pokemon.name,
                    "id": pokemon.id,
                    "sprite_url": pokemon.sprite_url or "",
                })

        batch_size = 20
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_images = images[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            self.image_collection.upsert(
                ids=batch_ids,
                images=batch_images,
                metadatas=batch_meta,
            )
            print(f"  Seeded {min(i + batch_size, len(ids))}/{len(ids)} images")

        print("✓ Image collection seeding complete")

    def seed_all(self, pokemon_list: list[PokemonData]):
        self.create_collections()
        self.seed_text_collection(pokemon_list)
        self.seed_image_collection(pokemon_list)

    def verify_collections(self) -> dict:
        text_count = self.text_collection.count() if self.text_collection else 0
        image_count = self.image_collection.count() if self.image_collection else 0
        return {
            "text_documents": text_count,
            "image_documents": image_count,
        }

    def test_text_search(self, query: str, n_results: int = 3) -> list:
        if not self.text_collection:
            return []
        results = self.text_collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        return results.get("ids", [[]])[0]

    def test_image_search(self, image_bytes: bytes, n_results: int = 3) -> list:
        if not self.image_collection:
            return []
        results = self.image_collection.query(
            images=[image_bytes],
            n_results=n_results,
        )
        return results.get("ids", [[]])[0]


def create_chroma_seeder() -> ChromaSeeder:
    config = get_chroma_config()
    return ChromaSeeder(
        host=config["host"],
        port=config["port"],
    )