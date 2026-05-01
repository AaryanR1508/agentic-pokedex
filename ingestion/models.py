from typing import Optional
from pydantic import BaseModel, Field


class PokemonStats(BaseModel):
    hp: int
    attack: int
    defense: int
    sp_atk: int
    sp_def: int
    speed: int


class PokemonData(BaseModel):
    id: int
    name: str
    types: list[str]
    stats: PokemonStats
    abilities: list[str]
    height: int
    weight: int
    sprite_url: Optional[str] = None
    sprite_shiny_url: Optional[str] = None
    sprite_bytes: Optional[bytes] = None
    moves: list[str]
    base_experience: Optional[int] = None
    flavor_text: str
    genus: str
    evolution_chain: list[tuple[str, str]] = Field(default_factory=list)
    habitat: Optional[str] = None
    color: str
    is_legendary: bool = False
    is_mythical: bool = False
    egg_groups: list[str] = Field(default_factory=list)
    growth_rate: str


class TypeEffectiveness(BaseModel):
    type_name: str
    strong_against: list[str]
    weak_against: list[str]
    resistant_to: list[str]
    immune_to: list[str]