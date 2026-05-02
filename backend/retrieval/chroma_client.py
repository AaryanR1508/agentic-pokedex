import io

import numpy as np
from PIL import Image
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from typing import Optional


class ChromaClient:
    def __init__(self, host: str = "chromadb"):
        self.client = chromadb.HttpClient(
            host=host,
            port=8000,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Load the OpenCLIP model once at construction time so that the
        # HuggingFace Hub check (and any model download) only happens on
        # startup, not on every image query.
        self._openclip_ef = embedding_functions.OpenCLIPEmbeddingFunction(
            model_name="ViT-B-32",
            checkpoint="laion2b_s34b_b79k",
        )

    def search_image(self, image_bytes: bytes) -> Optional[str]:
        # _encode_image internally calls PIL.Image.fromarray(), which requires
        # a numpy ndarray — not a PIL Image object.
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_array = np.array(image)
        embedding = self._openclip_ef._encode_image(image_array)  # list[float]

        collection = self.client.get_or_create_collection(
            "pokemon_images",
            embedding_function=self._openclip_ef,
        )

        results = collection.query(
            query_embeddings=[embedding],
            n_results=1,
        )

        if results["ids"] and results["ids"][0]:
            metadata = results["metadatas"][0][0]
            return metadata.get("name")

        return None

    def search_text(self, query: str) -> Optional[str]:
        collection = self.client.get_or_create_collection(
            "pokemon_text"
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
            "pokemon_text"
        )

        results = collection.get(where={"name": name})

        if results["ids"]:
            return results["metadatas"][0]

        return None