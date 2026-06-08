import time
import requests
from monitor import Deal

API = "https://api.telegram.org/bot{token}/{method}"

SCORE_EMOJI = {
    3: "🔥",
    2: "✨",
    1: "👍",
    0: "🆕",
}

SCORE_LABEL = {
    3: "FIRE DEAL",
    2: "GREAT DEAL",
    1: "GOOD DEAL",
    0: "Novo item",
}


def _url(token: str, method: str) -> str:
    return API.format(token=token, method=method)


def get_chat_id(token: str) -> int | None:
    """Retorna o chat_id da última mensagem recebida pelo bot."""
    try:
        resp = requests.get(_url(token, "getUpdates"), timeout=10)
        resp.raise_for_status()
        results = resp.json().get("result", [])
        if results:
            return results[-1]["message"]["chat"]["id"]
    except (requests.RequestException, KeyError, IndexError):
        pass
    return None


def send_deal(token: str, chat_id: int | str, deal: Deal, item_url: str) -> bool:
    emoji = SCORE_EMOJI[deal.score]
    label = SCORE_LABEL[deal.score]

    lines = [
        f"{emoji} <b>{label}</b>",
        f"",
        f"<b>{_esc(deal.title)}</b>",
        f"💰 <b>{_esc(deal.price)}</b>",
    ]
    if deal.monitor.price_to:
        lines[-1] += f"  <i>(máx: {deal.monitor.price_to:.0f} €)</i>"
    if deal.brand:
        lines.append(f"🏷 {_esc(deal.brand)}")
    if deal.size:
        lines.append(f"📐 {_esc(deal.size)}")
    if deal.condition:
        lines.append(f"🔍 {_esc(deal.condition)}")
    lines.append(f"📡 Monitor: {_esc(deal.monitor.name)}")
    lines.append(f"")
    lines.append(f'<a href="{item_url}">Ver no Vinted →</a>')

    text = "\n".join(lines)

    # Se tiver imagem usa sendPhoto, senão sendMessage
    if deal.image_url:
        payload = {
            "chat_id": chat_id,
            "photo": deal.image_url,
            "caption": text,
            "parse_mode": "HTML",
        }
        method = "sendPhoto"
    else:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        method = "sendMessage"

    try:
        resp = requests.post(_url(token, method), json=payload, timeout=15)
        if resp.status_code == 429:
            retry_after = float(resp.json().get("parameters", {}).get("retry_after", 2))
            time.sleep(retry_after)
            resp = requests.post(_url(token, method), json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


def send_deals_batch(token: str, chat_id: int | str, deals: list[Deal], client) -> int:
    sent = 0
    for deal in deals:
        url = client.item_url(deal.item)
        if send_deal(token, chat_id, deal, url):
            sent += 1
        time.sleep(0.3)
    return sent


def _esc(text: str) -> str:
    """Escape HTML special chars."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
