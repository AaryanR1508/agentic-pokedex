from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from neo4j import AsyncGraphDatabase

from core.config import settings
from retrieval.neo4j_client import Neo4jClient
from retrieval.chroma_client import ChromaClient


@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=2048,
    )


async def get_neo4j_client() -> Neo4jClient:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    return Neo4jClient(driver)


async def get_chroma_client() -> ChromaClient:
    return ChromaClient(host=settings.chroma_host)