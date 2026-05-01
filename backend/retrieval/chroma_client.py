import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional
import base64


class ChromaClient:
    def __init__(self, host: str = "chromadb"):
        self.client = chromadb.HttpClient(
            host=host,
            port=8000,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def search_image(self, image_bytes: bytes) -> Optional[str]:
        from chromadb.api.models.Collection import EmbeddingFunction

        collection = self.client.get_or_create_collection(
            "pokemon_images",
            embedding_function="openclip"
        )

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        results = collection.query(
            query_images=[image_base64],
            n_results=1
        )

        if results["ids"] and results["ids"][0]:
            doc_id = results["ids"][0][0]
            metadata = results["metadatas"][0][0]
            return metadata.get("name")

        return None

    def search_text(self, query: str) -> Optional[str]:
        collection = self.client.get_or_create_collection(
            "pokemon_text",
            embedding_function="openclip"
        )

        results = collection.query(
            query_texts=[query],
            n_results=1
        )

        if results["documents"] and results["documents"][0]:
            return results["documents"][0][0]

        return None

    def get_pokemon_info_by_name(self, name: str) -> Optional[dict]:
        collection = self.client.get_or_create_collection(
            "pokemon_images",
            embedding_function="openclip"
        )

        results = collection.get(where={"name": name})

        if results["ids"]:
            return results["metadatas"][0]

        return None