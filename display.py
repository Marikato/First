from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box
from monitor import Deal, MonitorConfig

console = Console()

SCORE_BADGE = {
    3: ("[bold white on red] 🔥 FIRE DEAL [/]", "red"),
    2: ("[bold black on yellow] ✨ GREAT DEAL [/]", "yellow"),
    1: ("[bold white on green] 👍 GOOD DEAL [/]", "green"),
    0: ("[dim] NEW [/]", "white"),
}

SCORE_BORDER = {
    3: "red",
    2: "yellow",
    1: "green",
    0: "blue",
}


def print_banner():
    banner = Text()
    banner.append("  VINTED DEAL MONITOR  ", style="bold white on dark_magenta")
    console.print()
    console.print(banner, justify="center")
    console.print()


def print_monitors_table(monitors: list[MonitorConfig]):
    table = Table(
        title="Monitores Ativos",
        box=box.ROUNDED,
        border_style="magenta",
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Nome", style="bold")
    table.add_column("Pesquisa")
    table.add_column("Preço Máx", justify="right", style="green")
    table.add_column("Tamanhos")

    for i, m in enumerate(monitors, 1):
        price_max = f"{m.price_to:.0f} €" if m.price_to else "—"
        sizes = ", ".join(str(s) for s in m.size_ids) if m.size_ids else "todos"
        table.add_row(str(i), m.name, m.search_text or "(qualquer)", price_max, sizes)

    console.print(table)
    console.print()


def print_deal(deal: Deal, url: str):
    badge_markup, border_color = SCORE_BADGE[deal.score]

    title_text = Text(deal.title, style="bold")

    lines: list[str] = [f"[bold cyan]{deal.price}[/]"]
    if deal.brand:
        lines.append(f"[dim]Marca:[/] {deal.brand}")
    if deal.size:
        lines.append(f"[dim]Tamanho:[/] {deal.size}")
    if deal.condition:
        lines.append(f"[dim]Estado:[/] {deal.condition}")
    lines.append(f"[dim]Monitor:[/] {deal.monitor.name}")
    lines.append(f"[link={url}][underline blue]{url}[/][/]")

    body = "\n".join(lines)

    panel = Panel(
        f"{badge_markup}\n\n{body}",
        title=title_text,
        border_style=border_color,
        expand=False,
        padding=(0, 1),
    )
    console.print(panel)


def print_deals_batch(deals: list[Deal], client):
    if not deals:
        return

    ts = datetime.now().strftime("%H:%M:%S")
    console.rule(f"[dim]{ts} — {len(deals)} novo(s) item(s)[/]")

    for deal in deals:
        url = client.item_url(deal.item)
        print_deal(deal, url)

    console.print()


def print_status(msg: str, style: str = "dim"):
    ts = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{ts}[/] {msg}", style=style)


def print_error(msg: str):
    console.print(f"[bold red]ERRO:[/] {msg}")


def print_no_new():
    ts = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{ts} — Sem novidades...[/]")
