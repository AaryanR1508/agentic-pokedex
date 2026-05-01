import asyncio
import json
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.progress import Progress, TaskID

from models import PokemonData, PokemonStats, TypeEffectiveness


CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

POKEMON_API_BASE = "https://pokeapi.co/api/v2"
MAX_CONCURRENT = 10


def clean_flavor_text(text: str) -> str:
    text = re.sub(r"[\n\f\r]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_latest_flavor_text(entries: list[dict]) -> str:
    english_entries = [e for e in entries if e["language"]["name"] == "en"]
    if not english_entries:
        return ""
    english_entries.sort(key=lambda e: e["version"]["name"], reverse=True)
    return clean_flavor_text(english_entries[0]["flavor_text"])


def get_genus(genera: list[dict]) -> str:
    for g in genera:
        if g["language"]["name"] == "en":
            return g["genus"]
    return ""


def parse_evolution_chain(chain: dict) -> list[tuple[str, str]]:
    evolutions = []

    def walk(node: dict):
        species_name = node["species"]["name"]
        for evolution in node.get("evolves_to", []):
            evolutions.append((species_name, evolution["species"]["name"]))
            walk(evolution)

    walk(chain)
    return evolutions


def extract_stats(stats: list[dict]) -> PokemonStats:
    stat_map = {s["stat"]["name"]: s["base_stat"] for s in stats}
    return PokemonStats(
        hp=stat_map.get("hp", 0),
        attack=stat_map.get("attack", 0),
        defense=stat_map.get("defense", 0),
        sp_atk=stat_map.get("special-attack", 0),
        sp_def=stat_map.get("special-defense", 0),
        speed=stat_map.get("speed", 0),
    )


class PokeAPIFetcher:
    def __init__(self, semaphore: asyncio.Semaphore):
        self.semaphore = semaphore
        self.client = httpx.AsyncClient(timeout=30.0)
        self.evolution_cache: dict[str, list[tuple[str, str]]] = {}

    async def close(self):
        await self.client.aclose()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(self, url: str) -> dict:
        async with self.semaphore:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()

    async def fetch_pokemon_data(self, pokemon_id: int) -> Optional[dict]:
        cache_file = CACHE_DIR / f"pokemon_{pokemon_id}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{POKEMON_API_BASE}/pokemon/{pokemon_id}"
        data = await self._get(url)
        cache_file.write_text(json.dumps(data))
        return data

    async def fetch_species_data(self, pokemon_id: int) -> Optional[dict]:
        cache_file = CACHE_DIR / f"species_{pokemon_id}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{POKEMON_API_BASE}/pokemon-species/{pokemon_id}"
        data = await self._get(url)
        cache_file.write_text(json.dumps(data))
        return data

    async def fetch_evolution_chain(self, url: str) -> list[tuple[str, str]]:
        if url in self.evolution_cache:
            return self.evolution_cache[url]

        cache_file_name = re.sub(r"[^\w]", "_", url.split("/")[-2])
        cache_file = CACHE_DIR / f"evolution_{cache_file_name}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            evolutions = parse_evolution_chain(data)
            self.evolution_cache[url] = evolutions
            return evolutions

        data = await self._get(url)
        cache_file.write_text(json.dumps(data))
        evolutions = parse_evolution_chain(data)
        self.evolution_cache[url] = evolutions
        return evolutions

    async def fetch_type_data(self, type_name: str) -> Optional[dict]:
        cache_file = CACHE_DIR / f"type_{type_name}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{POKEMON_API_BASE}/type/{type_name}"
        data = await self._get(url)
        cache_file.write_text(json.dumps(data))
        return data

    async def build_pokemon_data(self, pokemon_json: dict, species_json: dict) -> PokemonData:
        types = [t["type"]["name"] for t in pokemon_json["types"]]
        stats = extract_stats(pokemon_json["stats"])
        abilities = [a["ability"]["name"] for a in pokemon_json["abilities"]]
        moves = [m["move"]["name"] for m in pokemon_json["moves"]]

        evolution_chain = []
        if species_json.get("evolution_chain", {}).get("url"):
            evolution_chain = await self.fetch_evolution_chain(
                species_json["evolution_chain"]["url"]
            )

        sprite_url = pokemon_json["sprites"].get("front_default")
        sprite_shiny_url = pokemon_json["sprites"].get("front_shiny")

        egg_groups = [eg["name"] for eg in species_json.get("egg_groups", [])]

        return PokemonData(
            id=pokemon_json["id"],
            name=pokemon_json["name"],
            types=types,
            stats=stats,
            abilities=abilities,
            height=pokemon_json["height"],
            weight=pokemon_json["weight"],
            sprite_url=sprite_url,
            sprite_shiny_url=sprite_shiny_url,
            moves=moves,
            base_experience=pokemon_json.get("base_experience"),
            flavor_text=get_latest_flavor_text(species_json.get("flavor_text_entries", [])),
            genus=get_genus(species_json.get("genera", [])),
            evolution_chain=evolution_chain,
            habitat=species_json.get("habitat", {}).get("name"),
            color=species_json.get("color", {}).get("name", "unknown"),
            is_legendary=species_json.get("is_legendary", False),
            is_mythical=species_json.get("is_mythical", False),
            egg_groups=egg_groups,
            growth_rate=species_json.get("growth_rate", {}).get("name", "unknown"),
        )

    async def fetch_all_pokemon(
        self, progress: Progress, task_id: TaskID
    ) -> list[PokemonData]:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def fetch_one(pokemon_id: int) -> Optional[PokemonData]:
            try:
                pokemon_json = await self.fetch_pokemon_data(pokemon_id)
                species_json = await self.fetch_species_data(pokemon_id)
                if pokemon_json and species_json:
                    return await self.build_pokemon_data(pokemon_json, species_json)
            except Exception as e:
                print(f"Error fetching Pokemon {pokemon_id}: {e}")
            return None

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_one(i)) for i in range(1, 152)]

        results = []
        for task in tasks:
            result = task.result()
            if result:
                results.append(result)
                progress.advance(task_id)

        return results

    async def fetch_type_effectiveness(self) -> list[TypeEffectiveness]:
        type_names = [
            "normal", "fire", "water", "electric", "grass", "ice",
            "fighting", "poison", "ground", "flying", "psychic",
            "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"
        ]

        results = []
        for type_name in type_names:
            data = await self.fetch_type_data(type_name)
            if data:
                relations = data["damage_relations"]
                results.append(TypeEffectiveness(
                    type_name=type_name,
                    strong_against=[t["name"] for t in relations["double_damage_to"]],
                    weak_against=[t["name"] for t in relations["double_damage_from"]],
                    resistant_to=[t["name"] for t in relations["half_damage_to"]],
                    immune_to=[t["name"] for t in relations["no_damage_to"]],
                ))
        return results


async def download_sprite(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    except Exception:
        return None


async def download_all_sprites(pokemon_list: list[PokemonData]):
    async def download_with_id(pokemon: PokemonData):
        bytes_data = await download_sprite(pokemon.sprite_url)
        return pokemon.id, bytes_data

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(download_with_id(p)) for p in pokemon_list]

    for task in tasks:
        pokemon_id, sprite_bytes = task.result()
        for pokemon in pokemon_list:
            if pokemon.id == pokemon_id:
                pokemon.sprite_bytes = sprite_bytes
                break