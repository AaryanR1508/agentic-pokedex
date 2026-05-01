from typing import Optional, Dict, Any, List
from neo4j import AsyncGraphDatabase, Driver


class Neo4jClient:
    def __init__(self, driver: Driver):
        self.driver = driver

    async def close(self):
        await self.driver.close()

    async def get_pokemon_details(self, name: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (p:Pokemon {name: $name})
        OPTIONAL MATCH (p)-[:HAS_TYPE]->(t:Type)
        OPTIONAL MATCH (p)-[:EVOLVES_TO]->(evo:Pokemon)
        RETURN p.name as name, p.id as id, p.hp as hp, p.attack as attack,
               p.defense as defense, p.sp_atk as sp_atk,
               p.sp_def as sp_def, p.speed as speed,
               p.flavor_text as flavor_text,
               p.sprite_url as sprite_url, collect(DISTINCT t.name) as types,
               collect(DISTINCT evo.name) as evolutions
        """

        async with self.driver.session() as session:
            result = await session.run(query, name=name.lower())
            record = await result.single()
            if record:
                return dict(record)
        return None

    async def get_type_effectiveness(self, pokemon_name: str) -> List[str]:
        query = """
        MATCH (p:Pokemon {name: $name})-[:HAS_TYPE]->(t:Type)
        MATCH (attacking_type:Type)-[:STRONG_AGAINST]->(t)
        RETURN DISTINCT attacking_type.name as strong_against
        """

        async with self.driver.session() as session:
            result = await session.run(query, name=pokemon_name.lower())
            records = await result.data()
            return [r["strong_against"] for r in records]

    async def get_pokemon_by_type(self, type_name: str) -> List[str]:
        query = """
        MATCH (p:Pokemon)-[:HAS_TYPE]->(t:Type {name: $type})
        RETURN p.name as name
        """

        async with self.driver.session() as session:
            result = await session.run(query, type=type_name.lower())
            records = await result.data()
            return [r["name"] for r in records]

    async def search_pokemon(self, query_text: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (p:Pokemon)
        WHERE p.name CONTAINS $query OR p.flavor_text CONTAINS $query
        OPTIONAL MATCH (p)-[:HAS_TYPE]->(t:Type)
        OPTIONAL MATCH (p)-[:EVOLVES_TO]->(evo:Pokemon)
        RETURN p.name as name, p.sprite_url as sprite_url,
               collect(DISTINCT t.name) as types,
               collect(DISTINCT evo.name) as evolutions,
               p.flavor_text as flavor_text
        LIMIT 1
        """

        async with self.driver.session() as session:
            result = await session.run(query, query=query_text.lower())
            record = await result.single()
            if record:
                return dict(record)
        return None