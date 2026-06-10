"""
Wizard interativo para criar monitores com filtros completos do Vinted.
"""
from vinted import VintedClient
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

CONDITIONS = [
    (6, "Novo com etiqueta"),
    (1, "Novo sem etiqueta"),
    (2, "Muito bom estado"),
    (3, "Bom estado"),
    (4, "Estado razoável"),
]


# ─── helpers ────────────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else default


def _pick_numbered(items: list[tuple], prompt: str, multi: bool = True) -> list:
    """Show a numbered list and let the user pick one or more items."""
    if not items:
        return []

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("", style="dim", width=4)
    table.add_column("")
    for i, (_, label) in enumerate(items, 1):
        table.add_row(str(i), label)
    console.print(table)

    hint = "números separados por vírgula, Enter para todos" if multi else "número"
    raw = input(f"{prompt} ({hint}): ").strip()

    if not raw:
        return [v for v, _ in items]  # all selected

    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(items):
                selected.append(items[idx][0])
    return selected


# ─── category ────────────────────────────────────────────────────────────────

def _fetch_categories(client: VintedClient) -> list[tuple]:
    # Categorias principais do Vinted PT (hardcoded como fallback fiável)
    # Estes IDs são os mesmos em vinted.pt/fr/es/de
    return [
        (1, "Mulher"),
        (4, "Homem"),
        (3, "Criança"),
        (5, "Casa"),
        (7, "Entretenimento"),
    ]


def pick_category(client: VintedClient) -> int | None:
    console.print("\n[bold]Categoria[/]")
    console.print("[dim]A carregar categorias...[/]")
    cats = _fetch_categories(client)
    if not cats:
        console.print("[yellow]Não foi possível carregar categorias. Deixa em branco para todas.[/]")
        return None

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("", style="dim", width=4)
    table.add_column("")
    for i, (_, label) in enumerate(cats, 1):
        table.add_row(str(i), label)
    console.print(table)

    raw = input("Categoria (número, Enter para todas): ").strip()
    if not raw or not raw.isdigit():
        return None
    idx = int(raw) - 1
    if 0 <= idx < len(cats):
        return cats[idx][0]
    return None


# ─── brands ──────────────────────────────────────────────────────────────────

def _search_brands(client: VintedClient, query: str) -> list[tuple]:
    # Tenta vários endpoints conhecidos da API do Vinted
    endpoints = [
        f"{client.api_url}/brands",
        f"{client.base_url}/api/v2/brands",
    ]
    params_options = [
        {"search_text": query, "per_page": 15},
        {"q": query, "per_page": 15},
    ]
    for url in endpoints:
        for params in params_options:
            try:
                resp = client.session.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    brands = data.get("brands", data.get("items", []))
                    if brands:
                        return [(b["id"], b.get("title", b.get("name", ""))) for b in brands if b.get("id")]
            except Exception:
                continue
    return []


# IDs reais de marcas populares no Vinted
KNOWN_BRANDS = {
    "nike": (53, "Nike"),
    "adidas": (14, "Adidas"),
    "supreme": (1524, "Supreme"),
    "stussy": (1058, "Stüssy"),
    "ralph lauren": (88, "Ralph Lauren"),
    "carhartt": (226, "Carhartt"),
    "fendi": (261, "Fendi"),
    "bape": (1062, "A Bathing Ape (BAPE)"),
    "palace": (2543, "Palace"),
    "corteiz": (5555, "Corteiz"),
    "stone island": (773, "Stone Island"),
    "north face": (2107, "The North Face"),
    "jordan": (53, "Nike"),  # Jordan é sub-marca Nike no Vinted
    "off white": (2064, "Off-White"),
    "new balance": (19, "New Balance"),
    "puma": (24, "Puma"),
    "champion": (536, "Champion"),
    "tommy": (69, "Tommy Hilfiger"),
    "lacoste": (66, "Lacoste"),
    "hugo boss": (72, "Hugo Boss"),
}


def pick_brands(client: VintedClient) -> list[int]:
    console.print("\n[bold]Marcas[/]")
    brand_ids = []
    selected_names = []

    while True:
        query = input("Pesquisar marca (Enter para terminar): ").strip().lower()
        if not query:
            break

        # Tenta primeiro na lista local
        local = [(bid, name) for k, (bid, name) in KNOWN_BRANDS.items() if query in k]
        if local:
            picked = _pick_numbered(local, "Escolhe marca", multi=False)
            brand_ids.extend(picked)
            selected_names.extend([name for bid, name in local if bid in picked])
        else:
            # Tenta na API
            results = _search_brands(client, query)
            if results:
                picked = _pick_numbered(results, "Escolhe marca", multi=False)
                brand_ids.extend(picked)
                selected_names.extend([name for bid, name in results if bid in picked])
            else:
                console.print(f"[yellow]Marca '{query}' não encontrada.[/]")
                continue

        if selected_names:
            console.print(f"[green]✓ {', '.join(set(selected_names))}[/]")

    return list(set(brand_ids))


# ─── sizes ───────────────────────────────────────────────────────────────────

# IDs reais do Vinted para os tamanhos mais comuns (roupa + calçado)
CLOTHING_SIZES = [
    (1271, "XS / 32-34"),
    (1272, "S / 36-38"),
    (1273, "M / 40-42"),
    (1274, "L / 44-46"),
    (1275, "XL / 48-50"),
    (1276, "XXL / 52-54"),
    (1277, "XXXL / 56+"),
]

KIDS_SIZES = [
    (1258, "68 cm / 0-3M"),
    (1259, "74 cm / 3-6M"),
    (1260, "80 cm / 6-12M"),
    (1261, "86 cm / 12-18M"),
    (1262, "92 cm / 18-24M"),
    (1263, "98 cm / 2-3Y"),
    (1264, "104 cm / 3-4Y"),
    (1265, "110 cm / 4-5Y"),
    (1266, "116 cm / 5-6Y"),
    (1267, "122 cm / 6-7Y"),
    (1268, "128 cm / 7-8Y"),
    (1269, "134 cm / 8-9Y"),
    (1270, "140 cm / 9-10Y"),
]

SHOES_SIZES = [
    (1305, "35"),
    (1306, "36"),
    (1307, "37"),
    (1308, "38"),
    (1309, "39"),
    (1310, "40"),
    (1311, "41"),
    (1312, "42"),
    (1313, "43"),
    (1314, "44"),
    (1315, "45"),
    (1316, "46"),
    (1317, "47"),
    (1318, "48"),
]


def pick_sizes(client: VintedClient) -> list[int]:
    console.print("\n[bold]Tamanhos[/]")
    console.print("  1) Roupa (XS–XXXL)")
    console.print("  2) Calçado (35–48)")
    console.print("  3) Crianças (68cm–140cm)")
    console.print("  4) Sem filtro de tamanho")

    choice = input("Tipo de tamanho: ").strip()
    if choice == "1":
        return _pick_numbered(CLOTHING_SIZES, "Escolhe tamanhos", multi=True)
    elif choice == "2":
        return _pick_numbered(SHOES_SIZES, "Escolhe tamanhos", multi=True)
    elif choice == "3":
        return _pick_numbered(KIDS_SIZES, "Escolhe tamanhos", multi=True)
    return []


# ─── condition ───────────────────────────────────────────────────────────────

def pick_conditions() -> list[int]:
    console.print("\n[bold]Condição[/]")
    items = CONDITIONS
    return _pick_numbered(items, "Escolhe condições", multi=True)


# ─── price ───────────────────────────────────────────────────────────────────

def pick_price(client: VintedClient, search_text: str) -> tuple[float | None, float | None]:
    console.print("\n[bold]Preço[/]")

    if search_text:
        console.print("[dim]A analisar preços reais no Vinted...[/]")
        try:
            from lookup import analyze_prices, print_price_analysis
            stats = analyze_prices(client, search_text)
            if stats:
                print_price_analysis(search_text, stats)
        except Exception:
            pass

    from_raw = input("Preço mínimo em € (Enter para sem limite): ").strip()
    to_raw = input("Preço máximo em € (Enter para sem limite): ").strip()

    price_from = float(from_raw) if from_raw.replace(".", "").isdigit() else None
    price_to = float(to_raw) if to_raw.replace(".", "").isdigit() else None
    return price_from, price_to


# ─── main wizard ─────────────────────────────────────────────────────────────

def run(client: VintedClient) -> dict | None:
    console.print("\n[bold magenta]═══ NOVO MONITOR ═══[/]\n")

    name = input("Nome do monitor: ").strip()
    if not name:
        return None

    search = input("Texto de pesquisa (opcional, ex: nike, jordan, levis): ").strip()

    catalog_id = pick_category(client)
    brand_ids = pick_brands(client)
    size_ids = pick_sizes(client)
    status_ids = pick_conditions()
    price_from, price_to = pick_price(client, search)

    config: dict = {"name": name, "order": "newest_first"}
    if search:
        config["search_text"] = search
    if catalog_id:
        config["catalog_ids"] = [catalog_id]
    if brand_ids:
        config["brand_ids"] = brand_ids
    if size_ids:
        config["size_ids"] = size_ids
    if status_ids:
        config["status_ids"] = status_ids
    if price_from is not None:
        config["price_from"] = price_from
    if price_to is not None:
        config["price_to"] = price_to

    console.print("\n[bold]Resumo do monitor:[/]")
    _print_summary(config)
    confirm = input("\nGuardar? (s/n): ").strip().lower()
    if confirm in ("s", "y", "sim", "yes", ""):
        return config
    return None


def _print_summary(config: dict):
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("", style="dim")
    table.add_column("")

    table.add_row("Nome", config["name"])
    if config.get("search_text"):
        table.add_row("Pesquisa", config["search_text"])
    if config.get("catalog_ids"):
        table.add_row("Categoria", str(config["catalog_ids"]))
    if config.get("brand_ids"):
        table.add_row("Marcas", str(config["brand_ids"]))
    if config.get("size_ids"):
        table.add_row("Tamanhos", str(config["size_ids"]))
    if config.get("status_ids"):
        cond_map = dict(CONDITIONS)
        labels = [cond_map.get(s, str(s)) for s in config["status_ids"]]
        table.add_row("Condição", ", ".join(labels))
    if config.get("price_from") or config.get("price_to"):
        pf = f"{config['price_from']:.0f} €" if config.get("price_from") else "—"
        pt = f"{config['price_to']:.0f} €" if config.get("price_to") else "—"
        table.add_row("Preço", f"{pf} → {pt}")

    console.print(table)
