#!/usr/bin/env python3
"""
Vinted Deal Monitor — monitora artigos por filtros e mostra bons deals.

Uso:
  python main.py                     # Iniciar monitorização
  python main.py --config outro.json # Usar outro ficheiro de config
  python main.py add                 # Adicionar monitor interativamente
  python main.py list                # Listar monitores
  python main.py remove "Nome"       # Remover monitor pelo nome
  python main.py check               # Verificar uma vez (sem loop)
"""

import sys
import time
import argparse
import json
from pathlib import Path
from monitor import VintedMonitor, MonitorConfig, load_monitors_from_config
from display import (
    console,
    print_banner,
    print_monitors_table,
    print_deals_batch,
    print_status,
    print_error,
    print_no_new,
)


def _make_monitor(args) -> VintedMonitor:
    from vinted import VintedBlockedError
    try:
        return VintedMonitor(args.config, proxy=getattr(args, "proxy", None))
    except VintedBlockedError as e:
        print_error(str(e))
        raise SystemExit(1)


def cmd_list(args):
    from pathlib import Path
    config_path = Path(args.config)
    if not config_path.exists():
        _create_default_config(config_path)
    print_monitors_table(load_monitors_from_config(args.config))


ROUPA_SIZES = {
    "XS": 1271, "S": 1272, "M": 1273, "L": 1274,
    "XL": 1275, "XXL": 1276, "XXXL": 1277,
}
CALCADO_SIZES = {
    "36": 1305, "37": 1306, "38": 1307, "39": 1308, "40": 1309,
    "41": 1310, "42": 1311, "43": 1312, "44": 1313, "45": 1314,
    "46": 1315,
}


def cmd_add(args):
    monitor = VintedMonitor(args.config, proxy=getattr(args, "proxy", None))
    console.print("[bold magenta]Adicionar novo monitor[/]\n")

    name = input("Nome do monitor: ").strip()
    if not name:
        print_error("Nome não pode estar vazio.")
        return

    search = input("Texto de pesquisa (ex: nike air max): ").strip()
    price_to_raw = input("Preço máximo em € (Enter para sem limite): ").strip()
    price_from_raw = input("Preço mínimo em € (Enter para sem limite): ").strip()

    # Tamanhos
    console.print("\n[dim]Tamanhos de roupa:[/] XS S M L XL XXL XXXL")
    console.print("[dim]Tamanhos de calçado:[/] 36 37 38 39 40 41 42 43 44 45 46")
    sizes_raw = input("Tamanhos (separados por vírgula, Enter para todos): ").strip().upper()
    size_ids = []
    if sizes_raw:
        for s in sizes_raw.split(","):
            s = s.strip()
            sid = ROUPA_SIZES.get(s) or CALCADO_SIZES.get(s)
            if sid:
                size_ids.append(sid)
            else:
                console.print(f"[yellow]Tamanho '{s}' não reconhecido, ignorado.[/]")

    new_monitor: dict = {"name": name}
    if search:
        new_monitor["search_text"] = search
    if price_to_raw:
        try:
            new_monitor["price_to"] = float(price_to_raw)
        except ValueError:
            print_error("Preço inválido, a ignorar.")
    if price_from_raw:
        try:
            new_monitor["price_from"] = float(price_from_raw)
        except ValueError:
            pass
    if size_ids:
        new_monitor["size_ids"] = size_ids

    monitor.add_monitor(new_monitor)
    console.print(f"\n[green]Monitor '[bold]{name}[/]' adicionado![/]")
    print_monitors_table(monitor.monitors)


def cmd_lookup(args):
    from lookup import analyze_prices, print_price_analysis
    monitor = _make_monitor(args)
    search = args.search or input("Pesquisa (ex: nike air max): ").strip()
    if not search:
        return
    console.print("[dim]A analisar preços no Vinted...[/]")
    stats = analyze_prices(monitor.client, search)
    print_price_analysis(search, stats)


def cmd_setup_telegram(args):
    import json
    from pathlib import Path
    from telegram_notify import get_chat_id

    config_path = Path(args.config)
    data = json.loads(config_path.read_text())
    token = data.get("telegram_token", "")

    if not token or "TOKEN" in token:
        console.print("[yellow]Mete primeiro o teu token em monitors.json no campo 'telegram_token'[/]")
        return

    console.print("[dim]A procurar chat_id...[/]")
    chat_id = get_chat_id(token)
    if chat_id:
        data["telegram_chat_id"] = chat_id
        config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        console.print(f"[green]Chat ID encontrado e guardado: [bold]{chat_id}[/][/]")
        console.print("[green]Telegram configurado! Podes arrancar o monitor.[/]")
    else:
        console.print("[red]Não encontrei nenhuma mensagem. Abre o bot no Telegram e manda qualquer mensagem primeiro.[/]")
        console.print(f"[dim]Link do bot: t.me/VintedMonitorDeals_bot[/]")


def cmd_remove(args):
    monitor = VintedMonitor(args.config)
    name = args.name
    if monitor.remove_monitor(name):
        console.print(f"[green]Monitor '[bold]{name}[/]' removido.[/]")
    else:
        print_error(f"Monitor '{name}' não encontrado.")
        print_monitors_table(monitor.monitors)


def _notify_discord(monitor, deals):
    webhook = monitor.discord_webhook
    if not webhook or "SEU_ID" in webhook:
        return
    from discord_notify import send_deals_batch
    sent = send_deals_batch(webhook, deals, monitor.client)
    if sent:
        print_status(f"[magenta]Discord: {sent} mensagem(ns) enviada(s)[/]")
    else:
        print_status("[yellow]Discord: falha ao enviar[/]")


def _notify_telegram(monitor, deals):
    token = monitor.telegram_token
    chat_id = monitor.telegram_chat_id
    if not token or "TOKEN" in str(token):
        return
    if not chat_id:
        return
    from telegram_notify import send_deals_batch
    sent = send_deals_batch(token, chat_id, deals, monitor.client)
    if sent:
        print_status(f"[blue]Telegram: {sent} mensagem(ns) enviada(s)[/]")
    else:
        print_status("[yellow]Telegram: falha ao enviar[/]")


def cmd_check(args):
    monitor = _make_monitor(args)
    print_banner()
    print_monitors_table(monitor.monitors)
    print_status("A verificar...")
    deals = monitor.check_all()
    if deals:
        print_deals_batch(deals, monitor.client)
        _notify_discord(monitor, deals)
        _notify_telegram(monitor, deals)
    else:
        print_no_new()


def cmd_run(args):
    monitor = _make_monitor(args)
    print_banner()
    print_monitors_table(monitor.monitors)

    notif_parts = []
    if monitor.discord_webhook and "SEU_ID" not in monitor.discord_webhook:
        notif_parts.append("[magenta]Discord[/]")
    if monitor.telegram_token and "TOKEN" not in str(monitor.telegram_token) and monitor.telegram_chat_id:
        notif_parts.append("[blue]Telegram[/]")
    webhook_status = " | " + ", ".join(notif_parts) + " ativo" if notif_parts else " | [dim]sem notificações[/]"

    console.print(
        f"[dim]A verificar a cada [bold]{monitor.check_interval}s[/]{webhook_status}. "
        f"Ctrl+C para parar.[/]\n"
    )

    first_run = True
    while True:
        try:
            deals = monitor.check_all()
            if first_run and not deals:
                print_status(
                    f"[green]Inicializado — {sum(len(v) for v in monitor.seen.values())} "
                    f"item(s) já vistos. A aguardar novidades...[/]"
                )
                first_run = False
            elif deals:
                print_deals_batch(deals, monitor.client)
                _notify_discord(monitor, deals)
                _notify_telegram(monitor, deals)
                first_run = False
            else:
                print_no_new()

            time.sleep(monitor.check_interval)

            # Reload config in case it was edited
            try:
                monitor = VintedMonitor(args.config, proxy=getattr(args, "proxy", None))
            except Exception:
                pass

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Monitor parado.[/]")
            break
        except Exception as e:
            print_error(f"Erro inesperado: {e}")
            time.sleep(30)


def main():
    parser = argparse.ArgumentParser(
        description="Vinted Deal Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        default="monitors.json",
        help="Ficheiro de configuração (default: monitors.json)",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="Proxy HTTP/HTTPS opcional, ex: http://user:pass@host:port",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="Listar monitores configurados")
    subparsers.add_parser("add", help="Adicionar monitor interativamente")
    subparsers.add_parser("check", help="Verificar uma vez e sair")
    subparsers.add_parser("setup-telegram", help="Buscar e guardar o chat_id do Telegram automaticamente")

    lookup_parser = subparsers.add_parser("lookup", help="Analisar preços reais do Vinted para definir price_to")
    lookup_parser.add_argument("search", nargs="?", default=None, help="Texto de pesquisa")

    remove_parser = subparsers.add_parser("remove", help="Remover monitor pelo nome")
    remove_parser.add_argument("name", help="Nome do monitor a remover")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        _create_default_config(config_path)
        console.print(
            f"[yellow]Ficheiro de config criado: [bold]{config_path}[/]. "
            f"Edita-o para configurar os teus monitores.[/]\n"
        )

    commands = {
        "list": cmd_list,
        "add": cmd_add,
        "remove": cmd_remove,
        "check": cmd_check,
        "setup-telegram": cmd_setup_telegram,
        "lookup": cmd_lookup,
        None: cmd_run,
    }

    handler = commands.get(args.command, cmd_run)
    handler(args)


def _create_default_config(path: Path):
    default = {
        "country": "pt",
        "check_interval": 60,
        "monitors": [
            {
                "name": "Exemplo - Nike Air Max",
                "search_text": "nike air max",
                "price_to": 60,
                "order": "newest_first"
            }
        ]
    }
    path.write_text(json.dumps(default, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
