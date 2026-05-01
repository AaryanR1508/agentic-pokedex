import base64
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.state import AgentState
from core.dependencies import get_llm


llm = get_llm()


async def router_node(state: AgentState) -> Dict[str, str]:
    audio = state.get("audio_bytes")
    image = state.get("image_bytes")
    text = state.get("text_query")

    modality = "text"
    if audio:
        modality = "audio"
    elif image:
        modality = "image"

    return {"modality": modality}


async def audio_handler_node(state: AgentState) -> Dict[str, Any]:
    from retrieval.neo4j_client import Neo4jClient
    from core.config import settings
    import neo4j

    audio_bytes = state.get("audio_bytes")
    if not audio_bytes:
        return {"retrieved_context": {}}

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    message = HumanMessage(
        content=[
            {"type": "text", "text": "Identify the Pokémon whose cry is in this audio. Respond with JUST the name."},
            {
                "type": "file",
                "source_type": "base64",
                "mime_type": state.get("audio_mime_type", "audio/ogg"),
                "data": audio_base64,
            },
        ]
    )

    response = llm.invoke([message])
    pokemon_name = response.content.strip().lower().replace(" ", "")

    driver = neo4j.AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    neo4j_client = Neo4jClient(driver)
    pokemon_data = await neo4j_client.get_pokemon_details(pokemon_name)
    await neo4j_client.close()

    if pokemon_data:
        graph_relationships = []
        if "evolutions" in pokemon_data and pokemon_data["evolutions"]:
            graph_relationships.extend([f"Evolves to {e.title()}" for e in pokemon_data["evolutions"]])
        pokemon_data["graph_relationships"] = graph_relationships
        
        return {
            "extracted_entity": pokemon_name,
            "retrieved_context": pokemon_data
        }

    return {
        "extracted_entity": pokemon_name,
        "retrieved_context": {"pokemon_name": pokemon_name, "source": "audio"}
    }


async def image_handler_node(state: AgentState) -> Dict[str, Any]:
    from retrieval.chroma_client import ChromaClient
    from retrieval.neo4j_client import Neo4jClient
    from core.config import settings
    import neo4j

    image_bytes = state.get("image_bytes")
    if not image_bytes:
        return {"retrieved_context": {}}

    chroma_client = ChromaClient(host=settings.chroma_host)
    pokemon_name = chroma_client.search_image(image_bytes)

    if not pokemon_name:
        return {
            "extracted_entity": None,
            "retrieved_context": {"error": "Could not identify Pokémon from image"}
        }

    driver = neo4j.AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    neo4j_client = Neo4jClient(driver)
    pokemon_data = await neo4j_client.get_pokemon_details(pokemon_name)
    await neo4j_client.close()

    if pokemon_data:
        graph_relationships = []
        if "evolutions" in pokemon_data and pokemon_data["evolutions"]:
            graph_relationships.extend([f"Evolves to {e.title()}" for e in pokemon_data["evolutions"]])
        pokemon_data["graph_relationships"] = graph_relationships
        
        return {
            "extracted_entity": pokemon_name,
            "retrieved_context": pokemon_data
        }

    return {
        "extracted_entity": pokemon_name,
        "retrieved_context": {"pokemon_name": pokemon_name, "source": "image"}
    }


async def text_handler_node(state: AgentState) -> Dict[str, Any]:
    from retrieval.neo4j_client import Neo4jClient
    from retrieval.chroma_client import ChromaClient
    from core.config import settings
    from core.dependencies import get_neo4j_client
    import neo4j

    text_query = state.get("text_query", "")
    if not text_query:
        return {"retrieved_context": {}}

    driver = neo4j.AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    neo4j_client = Neo4jClient(driver)

    entity_extract_prompt = ChatPromptTemplate.from_template(
        """Extract the Pokémon name and intent from this query.
        Query: {query}
        
        Respond in format: ENTITY=<pokemon_name>, INTENT=<intent>
        Intent can be: details, type_effectiveness, evolution, search
        If no specific Pokémon, ENTITY=unknown"""
    )

    entity_response = llm.invoke(
        entity_extract_prompt.format(query=text_query)
    )

    response_text = entity_response.content.strip()
    pokemon_name = None
    intent = "details"

    if "ENTITY=" in response_text:
        parts = response_text.split("ENTITY=")[1].split(",")
        if parts:
            name = parts[0].strip()
            if name != "unknown":
                pokemon_name = name.lower().replace(" ", "")

    if "INTENT=" in response_text:
        intent_part = response_text.split("INTENT=")[1].strip()
        if intent_part:
            intent = intent_part

    if pokemon_name:
        pokemon_data = await neo4j_client.get_pokemon_details(pokemon_name)
        if pokemon_data:
            graph_relationships = []
            if "evolutions" in pokemon_data and pokemon_data["evolutions"]:
                graph_relationships.extend([f"Evolves to {e.title()}" for e in pokemon_data["evolutions"]])
            
            if intent == "type_effectiveness":
                strong_against = await neo4j_client.get_type_effectiveness(pokemon_name)
                if strong_against:
                    graph_relationships.append(f"Strong against {', '.join(strong_against).title()}")
            
            pokemon_data["graph_relationships"] = graph_relationships
            
            await neo4j_client.close()
            return {
                "extracted_entity": pokemon_name,
                "intent": intent,
                "retrieved_context": pokemon_data
            }

    await neo4j_client.close()

    chroma_client = ChromaClient(host=settings.chroma_host)
    text_result = chroma_client.search_text(text_query)

    return {
        "extracted_entity": None,
        "intent": intent,
        "retrieved_context": {"flavor_text": text_result} if text_result else {}
    }


async def generator_node(state: AgentState) -> Dict[str, Any]:
    text_query = state.get("text_query", "")
    modality = state.get("modality", "text")
    entity = state.get("extracted_entity")
    context = state.get("retrieved_context", {})

    if not entity and "pokemon_name" in context:
        entity = context["pokemon_name"]

    template = """You are the Rotom Pokédex, a helpful, energetic AI assistant.
Answer the user's query using ONLY the provided database context.
If the context doesn't contain the answer, say you don't have that data in your current databanks.

User Query: {query}
Modality Routed: {modality}
Identified Entity: {entity}

Retrieved Context from DBs:
{context}

Response:"""

    prompt = ChatPromptTemplate.from_template(template)

    formatted_prompt = prompt.format(
        query=text_query or f"Identify this Pokémon",
        modality=modality,
        entity=entity or "unknown",
        context=str(context)
    )

    response = llm.invoke(formatted_prompt)

    return {"final_response": response.content}