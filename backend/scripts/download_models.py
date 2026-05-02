"""
Run once at Docker image build time to pre-download the OpenCLIP model
weights into the image layer (HF_HOME=/app/.cache/huggingface).

This means the model is never fetched again on container startup.
"""
from chromadb.utils import embedding_functions

print("Downloading OpenCLIP ViT-B-32 (laion2b_s34b_b79k) ...")
embedding_functions.OpenCLIPEmbeddingFunction(
    model_name="ViT-B-32",
    checkpoint="laion2b_s34b_b79k",
)
print("OpenCLIP model cached successfully.")
