import argparse
import asyncio
import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from config import load_env, get_neo4j_config, get_chroma_config
from fetch import PokeAPIFetcher, download_all_sprites
from models import PokemonData, TypeEffectiveness
from seed_neo4j import create_neo4j_seeder, Neo4jSeeder
from seed_chroma import create_chroma_seeder, ChromaSeeder


console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="Populate databases with Pokemon data")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip API fetching, use cached JSON files only")
    parser.add_argument("--neo4j-only", action="store_true", help="Only seed Neo4j, skip ChromaDB")
    parser.add_argument("--chroma-only", action="store_true", help="Only seed ChromaDB, skip Neo4j")
    parser.add_argument("--verify-only", action="store_true", help="Only run verification queries, don't seed anything")
    parser.add_argument("--clean", action="store_true", help="Wipe existing data in both databases before seeding")
    return parser.parse_args()


async def fetch_all_data(progress: Progress) -> tuple[list[PokemonData], list[TypeEffectiveness]]:
    task_fetch = progress.add_task("[cyan]Fetching Pokemon data from PokéAPI...", total=151)

    semaphore = asyncio.Semaphore(10)
    fetcher = PokeAPIFetcher(semaphore)

    pokemon_data = await fetcher.fetch_all_pokemon(progress, task_fetch)

    progress.remove_task(task_fetch)
    console.print(f"✓ Fetched {len(pokemon_data)} Pokemon")

    console.print("[cyan]Downloading sprites...")
    await download_all_sprites(pokemon_data)
    console.print("✓ Downloaded sprites")

    console.print("[cyan]Fetching type effectiveness data...")
    type_effectiveness = await fetcher.fetch_type_effectiveness()
    console.print(f"✓ Fetched {len(type_effectiveness)} type effectiveness data")

    await fetcher.close()

    return pokemon_data, type_effectiveness


def verify_databases(neo4j_seeder: Neo4jSeeder, chroma_seeder: ChromaSeeder):
    console.print("\n[bold cyan]Running verification queries...[/bold cyan]")

    neo4j_stats = neo4j_seeder.get_stats()
    table = Table(title="Neo4j Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    for key, value in neo4j_stats.items():
        table.add_row(key, str(value))
    console.print(table)

    chroma_stats = chroma_seeder.verify_collections()
    table = Table(title="ChromaDB Stats")
    table.add_column("Collection", style="cyan")
    table.add_column("Count", style="green")
    for key, value in chroma_stats.items():
        table.add_row(key, str(value))
    console.print(table)

    text_results = chroma_seeder.test_text_search("a fire-breathing dragon", n_results=3)
    console.print(f"\n[cyan]Text search test:[/cyan] 'a fire-breathing dragon' -> {text_results}")

    console.print("\n✓ Verification complete")


async def main_async(args):
    start_time = time.time()

    load_env()

    console.print("[bold green]Starting Pokemon Data Ingestion Pipeline[/bold green]\n")

    neo4j_seeder = None
    chroma_seeder = None

    try:
        if not args.chroma_only:
            console.print("[cyan]Connecting to Neo4j...[/cyan]")
            neo4j_seeder = create_neo4j_seeder()
            if args.clean:
                console.print("[yellow]Clearing existing Neo4j data...[/yellow]")
                neo4j_seeder.clear_data()

        if not args.neo4j_only:
            console.print("[cyan]Connecting to ChromaDB...[/cyan]")
            chroma_seeder = create_chroma_seeder()
            if args.clean:
                console.print("[yellow]Clearing existing ChromaDB collections...[/yellow]")
                chroma_seeder.clear_collections()

        pokemon_data: list[PokemonData] = []
        type_effectiveness: list[TypeEffectiveness] = []

        if not args.verify_only:
            if not args.skip_fetch:
                with Progress() as progress:
                    pokemon_data, type_effectiveness = await fetch_all_data(progress)
            else:
                console.print("[yellow]Skipping fetch - using cached data[/yellow]")
                from fetch import CACHE_DIR
                console.print(f"Cache directory: {CACHE_DIR}")

        if args.verify_only:
            verify_databases(neo4j_seeder, chroma_seeder)
            return

        if not args.chroma_only and neo4j_seeder:
            console.print("\n[cyan]Seeding Neo4j...[/cyan]")
            neo4j_seeder.seed_all(pokemon_data, type_effectiveness)

        if not args.neo4j_only and chroma_seeder:
            console.print("\n[cyan]Seeding ChromaDB...[/cyan]")
            chroma_seeder.seed_all(pokemon_data)

        verify_databases(neo4j_seeder, chroma_seeder)

    finally:
        if neo4j_seeder:
            neo4j_seeder.close()
        if chroma_seeder:
            pass

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    console.print(f"\n[bold green]┌─────────────────────────────────────────┐[/bold green]")
    console.print(f"[bold green]│         Ingestion Complete ✅           │[/bold green]")
    console.print(f"[bold green]├─────────────────┬───────────────────────┤[/bold green]")
    console.print(f"[bold green]│ Pokémon Fetched │ {len(pokemon_data):<25} │[/bold green]")
    if neo4j_seeder:
        stats = neo4j_seeder.get_stats()
        console.print(f"[bold green]│ Neo4j Nodes     │ {stats['pokemon'] + stats['types'] + stats['abilities'] + stats['moves']:<25} │[/bold green]")
        console.print(f"[bold green]│ Neo4j Edges     │ {stats['relationships']:<25} │[/bold green]")
    if chroma_seeder:
        chroma_stats = chroma_seeder.verify_collections()
        console.print(f"[bold green]│ Chroma Texts    │ {chroma_stats['text_documents']:<25} │[/bold green]")
        console.print(f"[bold green]│ Chroma Images   │ {chroma_stats['image_documents']:<25} │[/bold green]")
    console.print(f"[bold green]│ Time Elapsed    │ {minutes}m {seconds}s{' ' * (17 - len(f'{minutes}m {seconds}s'))}│[/bold green]")
    console.print(f"[bold green]└─────────────────┴───────────────────────┘[/bold green]")


def main():
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()