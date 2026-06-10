"""
Lookup de IDs e análise de preços do Vinted.
Usado pelo comando: python3 main.py lookup
"""
import statistics
from vinted import VintedClient


def lookup_sizes(client: VintedClient, search_text: str) -> list[dict]:
    """Busca tamanhos disponíveis para uma pesquisa."""
    try:
        resp = client.session.get(
            f"{client.api_url}/catalog/filters",
            params={"search_text": search_text},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        filters = data.get("filters", [])
        for f in filters:
            if f.get("code") in ("size", "size_id", "sizes"):
                return f.get("options", [])
        return []
    except Exception:
        return []


def analyze_prices(client: VintedClient, search_text: str, sample: int = 48) -> dict:
    """Analisa distribuição de preços dos primeiros resultados."""
    items = client.search(search_text=search_text, order="relevance", per_page=sample)
    if not items:
        return {}

    prices = []
    for item in items:
        try:
            p = float(item.get("price_numeric") or item.get("price", 0))
            if p > 0:
                prices.append(p)
        except (TypeError, ValueError):
            pass

    if not prices:
        return {}

    prices.sort()
    return {
        "count": len(prices),
        "min": prices[0],
        "max": prices[-1],
        "median": statistics.median(prices),
        "mean": round(statistics.mean(prices), 2),
        "p25": prices[int(len(prices) * 0.25)],   # 25% mais baratos
        "p75": prices[int(len(prices) * 0.75)],   # 75% mais baratos
        "suggested_price_to": prices[int(len(prices) * 0.40)],  # abaixo de 40% = deal
    }


def print_price_analysis(search_text: str, stats: dict):
    from rich.table import Table
    from rich import box
    from rich.console import Console

    console = Console()

    if not stats:
        console.print("[red]Sem resultados para analisar.[/]")
        return

    console.print(f"\n[bold]Análise de preços para:[/] [cyan]{search_text}[/]\n")

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("", style="dim")
    table.add_column("", style="bold")

    table.add_row("Artigos analisados", str(stats["count"]))
    table.add_row("Preço mínimo", f"{stats['min']:.2f} €")
    table.add_row("Preço máximo", f"{stats['max']:.2f} €")
    table.add_row("Mediana", f"{stats['median']:.2f} €")
    table.add_row("Média", f"{stats['mean']:.2f} €")
    table.add_row("", "")
    table.add_row("25% mais baratos abaixo de", f"[green]{stats['p25']:.2f} €[/]")
    table.add_row("75% mais baratos abaixo de", f"[yellow]{stats['p75']:.2f} €[/]")

    console.print(table)
    console.print(
        f"[bold]Sugestão de price_to:[/] "
        f"[green]{stats['p25']:.0f} €[/] (bom deal) "
        f"ou [yellow]{stats['p75']:.0f} €[/] (ver tudo)\n"
    )
