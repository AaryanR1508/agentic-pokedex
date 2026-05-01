from neo4j import GraphDatabase

from config import get_neo4j_config
from models import PokemonData, TypeEffectiveness


class Neo4jSeeder:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._verify_connectivity()

    def _verify_connectivity(self):
        try:
            self.driver.verify_connectivity()
            print("✓ Neo4j connection verified")
        except Exception as e:
            raise RuntimeError(f"Neo4j is not reachable: {e}")

    def close(self):
        self.driver.close()

    def create_constraints(self):
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT FOR (p:Pokemon) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT FOR (t:Type) REQUIRE t.name IS UNIQUE",
                "CREATE CONSTRAINT FOR (a:Ability) REQUIRE a.name IS UNIQUE",
                "CREATE CONSTRAINT FOR (h:Habitat) REQUIRE h.name IS UNIQUE",
                "CREATE CONSTRAINT FOR (e:EggGroup) REQUIRE e.name IS UNIQUE",
                "CREATE CONSTRAINT FOR (m:Move) REQUIRE m.name IS UNIQUE",
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception:
                    pass

    def clear_data(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def seed_types_and_effectiveness(self, type_effectiveness: list[TypeEffectiveness]):
        with self.driver.session() as session:
            for te in type_effectiveness:
                session.run(
                    """
                    MERGE (t:Type {name: $type_name})
                    """,
                    type_name=te.type_name
                )

                for strong in te.strong_against:
                    session.run(
                        """
                        MATCH (attacker:Type {name: $type_name})
                        MATCH (defender:Type {name: $target})
                        MERGE (attacker)-[:STRONG_AGAINST]->(defender)
                        """,
                        type_name=te.type_name, target=strong
                    )

                for weak in te.weak_against:
                    session.run(
                        """
                        MATCH (attacker:Type {name: $type_name})
                        MATCH (defender:Type {name: $target})
                        MERGE (attacker)-[:WEAK_AGAINST]->(defender)
                        """,
                        type_name=te.type_name, target=weak
                    )

                for resistant in te.resistant_to:
                    session.run(
                        """
                        MATCH (attacker:Type {name: $type_name})
                        MATCH (defender:Type {name: $target})
                        MERGE (attacker)-[:RESISTANT_TO]->(defender)
                        """,
                        type_name=te.type_name, target=resistant
                    )

                for immune in te.immune_to:
                    session.run(
                        """
                        MATCH (attacker:Type {name: $type_name})
                        MATCH (defender:Type {name: $target})
                        MERGE (attacker)-[:IMMUNE_TO]->(defender)
                        """,
                        type_name=te.type_name, target=immune
                    )

    def seed_pokemon(self, pokemon: PokemonData):
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Pokemon {name: $name})
                SET p.id = $id,
                    p.height = $height,
                    p.weight = $weight,
                    p.base_experience = $base_experience,
                    p.flavor_text = $flavor_text,
                    p.genus = $genus,
                    p.color = $color,
                    p.is_legendary = $is_legendary,
                    p.is_mythical = $is_mythical,
                    p.growth_rate = $growth_rate,
                    p.hp = $hp,
                    p.attack = $attack,
                    p.defense = $defense,
                    p.sp_atk = $sp_atk,
                    p.sp_def = $sp_def,
                    p.speed = $speed,
                    p.sprite_url = $sprite_url
                """,
                name=pokemon.name,
                id=pokemon.id,
                height=pokemon.height,
                weight=pokemon.weight,
                base_experience=pokemon.base_experience,
                flavor_text=pokemon.flavor_text,
                genus=pokemon.genus,
                color=pokemon.color,
                is_legendary=pokemon.is_legendary,
                is_mythical=pokemon.is_mythical,
                growth_rate=pokemon.growth_rate,
                hp=pokemon.stats.hp,
                attack=pokemon.stats.attack,
                defense=pokemon.stats.defense,
                sp_atk=pokemon.stats.sp_atk,
                sp_def=pokemon.stats.sp_def,
                speed=pokemon.stats.speed,
                sprite_url=pokemon.sprite_url,
            )

            for slot, type_name in enumerate(pokemon.types, start=1):
                session.run(
                    """
                    MATCH (p:Pokemon {name: $pokemon_name})
                    MERGE (t:Type {name: $type_name})
                    MERGE (p)-[:HAS_TYPE {slot: $slot}]->(t)
                    """,
                    pokemon_name=pokemon.name,
                    type_name=type_name,
                    slot=slot
                )

            for ability in pokemon.abilities:
                session.run(
                    """
                    MATCH (p:Pokemon {name: $pokemon_name})
                    MERGE (a:Ability {name: $ability_name})
                    MERGE (p)-[:HAS_ABILITY]->(a)
                    """,
                    pokemon_name=pokemon.name,
                    ability_name=ability
                )

            if pokemon.habitat:
                session.run(
                    """
                    MATCH (p:Pokemon {name: $pokemon_name})
                    MERGE (h:Habitat {name: $habitat_name})
                    MERGE (p)-[:IN_HABITAT]->(h)
                    """,
                    pokemon_name=pokemon.name,
                    habitat_name=pokemon.habitat
                )

            for egg_group in pokemon.egg_groups:
                session.run(
                    """
                    MATCH (p:Pokemon {name: $pokemon_name})
                    MERGE (e:EggGroup {name: $egg_group})
                    MERGE (p)-[:IN_EGG_GROUP]->(e)
                    """,
                    pokemon_name=pokemon.name,
                    egg_group=egg_group
                )

            for move in pokemon.moves:
                session.run(
                    """
                    MATCH (p:Pokemon {name: $pokemon_name})
                    MERGE (m:Move {name: $move_name})
                    MERGE (p)-[:CAN_LEARN]->(m)
                    """,
                    pokemon_name=pokemon.name,
                    move_name=move
                )

            for evolves_from, evolves_to in pokemon.evolution_chain:
                session.run(
                    """
                    MATCH (p1:Pokemon {name: $evolves_from})
                    MATCH (p2:Pokemon {name: $evolves_to})
                    MERGE (p1)-[:EVOLVES_TO]->(p2)
                    """,
                    evolves_from=evolves_from,
                    evolves_to=evolves_to
                )

    def seed_all(self, pokemon_list: list[PokemonData], type_effectiveness: list[TypeEffectiveness]):
        print("Creating constraints...")
        self.create_constraints()

        print("Seeding type effectiveness data...")
        self.seed_types_and_effectiveness(type_effectiveness)

        print(f"Seeding {len(pokemon_list)} Pokemon nodes and relationships...")
        for i, pokemon in enumerate(pokemon_list, start=1):
            self.seed_pokemon(pokemon)
            if i % 20 == 0:
                print(f"  Seeded {i}/{len(pokemon_list)} Pokemon...")

        print("✓ Neo4j seeding complete")

    def get_stats(self) -> dict:
        with self.driver.session() as session:
            pokemon_count = session.run("MATCH (p:Pokemon) RETURN count(p) as count").single()["count"]
            type_count = session.run("MATCH (t:Type) RETURN count(t) as count").single()["count"]
            ability_count = session.run("MATCH (a:Ability) RETURN count(a) as count").single()["count"]
            move_count = session.run("MATCH (m:Move) RETURN count(m) as count").single()["count"]
            relationship_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

            return {
                "pokemon": pokemon_count,
                "types": type_count,
                "abilities": ability_count,
                "moves": move_count,
                "relationships": relationship_count,
            }


def create_neo4j_seeder() -> Neo4jSeeder:
    config = get_neo4j_config()
    return Neo4jSeeder(
        uri=config["uri"],
        user=config["user"],
        password=config["password"],
    )