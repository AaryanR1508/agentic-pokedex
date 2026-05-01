import os
from pathlib import Path
from dotenv import load_dotenv


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def load_env():
    env_path = get_project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()


def get_neo4j_config():
    load_env()
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
    }


def get_chroma_config():
    load_env()
    return {
        "host": os.getenv("CHROMA_HOST", "localhost"),
        "port": int(os.getenv("CHROMA_PORT", "8001")),
    }