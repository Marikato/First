import time
import requests
from monitor import Deal

SCORE_COLOR = {
    3: 0xE74C3C,  # vermelho — fire deal
    2: 0xF1C40F,  # amarelo — great deal
    1: 0x2ECC71,  # verde — good deal
    0: 0x5865F2,  # azul Discord — new
}

SCORE_LABEL = {
    3: "🔥 FIRE DEAL",
    2: "✨ GREAT DEAL",
    1: "👍 GOOD DEAL",
    0: "🆕 Novo item",
}


def send_deal(webhook_url: str, deal: Deal, item_url: str) -> bool:
    """Envia um embed do deal para o webhook Discord. Retorna True se OK."""
    fields = [
        {"name": "💰 Preço", "value": f"**{deal.price}**", "inline": True},
    ]
    if deal.monitor.price_to:
        fields[0]["value"] += f"\n*(máx: {deal.monitor.price_to:.0f} €)*"

    if deal.brand:
        fields.append({"name": "🏷️ Marca", "value": deal.brand, "inline": True})
    if deal.size:
        fields.append({"name": "📐 Tamanho", "value": deal.size, "inline": True})
    if deal.condition:
        fields.append({"name": "🔍 Estado", "value": deal.condition, "inline": True})

    fields.append({"name": "📡 Monitor", "value": deal.monitor.name, "inline": True})

    embed = {
        "title": deal.title[:256],
        "url": item_url,
        "color": SCORE_COLOR[deal.score],
        "description": SCORE_LABEL[deal.score],
        "fields": fields,
        "footer": {"text": "Vinted Deal Monitor"},
        "timestamp": _utc_now(),
    }

    if deal.image_url:
        embed["thumbnail"] = {"url": deal.image_url}

    payload = {"embeds": [embed]}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 429:
            # Rate limited — respeitar o retry_after do Discord
            retry_after = float(resp.json().get("retry_after", 1))
            time.sleep(retry_after)
            resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


def send_deals_batch(webhook_url: str, deals: list[Deal], client) -> int:
    """Envia todos os deals. Retorna o número de envios com sucesso."""
    sent = 0
    for deal in deals:
        url = client.item_url(deal.item)
        ok = send_deal(webhook_url, deal, url)
        if ok:
            sent += 1
        # Pequena pausa entre mensagens para não exceder rate limit
        time.sleep(0.5)
    return sent


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
