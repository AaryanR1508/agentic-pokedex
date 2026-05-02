FROM python:3.11-slim

# Install system dependencies required for uv and ML building
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Install uv (The Rust-based blazing fast package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Pin HuggingFace cache to a predictable path inside the image
ENV HF_HOME=/app/.cache/huggingface

# Copy dependency files
COPY pyproject.toml ./

# Sync dependencies instantly
RUN uv sync

# Pre-download the OpenCLIP model at build time so it is baked into the
# image layer and never re-fetched on container startup.
COPY scripts/download_models.py ./scripts/download_models.py
RUN uv run python scripts/download_models.py

COPY . .

# Expose port and run Uvicorn
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]