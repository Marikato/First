import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from vinted import VintedClient


SEEN_FILE = Path.home() / ".vinted_seen.json"


@dataclass
class MonitorConfig:
    name: str
    search_text: str = ""
    price_to: float | None = None
    price_from: float | None = None
    order: str = "newest_first"
    per_page: int = 24
    catalog_ids: list[int] = field(default_factory=list)
    brand_ids: list[int] = field(default_factory=list)
    size_ids: list[int] = field(default_factory=list)
    status_ids: list[int] = field(default_factory=list)


@dataclass
class Deal:
    item: dict
    monitor: MonitorConfig
    score: int  # 0=new, 1=good, 2=great, 3=fire

    @property
    def title(self) -> str:
        return self.item.get("title", "No title")

    @property
    def price(self) -> str:
        p = self.item.get("price_numeric") or self.item.get("price", 0)
        currency = self.item.get("currency", "€")
        try:
            return f"{float(p):.2f} {currency}"
        except (TypeError, ValueError):
            return f"{p} {currency}"

    @property
    def price_numeric(self) -> float:
        try:
            return float(self.item.get("price_numeric") or self.item.get("price", 0))
        except (TypeError, ValueError):
            return 0.0

    @property
    def brand(self) -> str:
        brand = self.item.get("brand_title") or self.item.get("brand", {})
        if isinstance(brand, dict):
            return brand.get("title", "")
        return str(brand)

    @property
    def size(self) -> str:
        return self.item.get("size_title") or self.item.get("size", "")

    @property
    def condition(self) -> str:
        status = self.item.get("status") or self.item.get("status_id", "")
        status_map = {
            "6": "Novo com etiqueta",
            "1": "Novo sem etiqueta",
            "2": "Muito bom estado",
            "3": "Bom estado",
            "4": "Estado razoável",
            6: "Novo com etiqueta",
            1: "Novo sem etiqueta",
            2: "Muito bom estado",
            3: "Bom estado",
            4: "Estado razoável",
        }
        return status_map.get(status, str(status))

    @property
    def image_url(self) -> str:
        photos = self.item.get("photos", [])
        if photos:
            photo = photos[0]
            return photo.get("url") or photo.get("thumbnail_url") or ""
        return self.item.get("photo", {}).get("url", "") if isinstance(self.item.get("photo"), dict) else ""

    @property
    def item_id(self) -> str:
        return str(self.item.get("id", ""))


def _load_seen() -> dict[str, set[str]]:
    if not SEEN_FILE.exists():
        return {}
    try:
        data = json.loads(SEEN_FILE.read_text())
        return {k: set(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_seen(seen: dict[str, set[str]]):
    try:
        SEEN_FILE.write_text(json.dumps({k: list(v) for k, v in seen.items()}, indent=2))
    except OSError:
        pass


def _deal_score(item: dict, monitor: MonitorConfig) -> int:
    """Score: 3=fire, 2=great, 1=good, 0=new (no price context)"""
    if monitor.price_to is None:
        return 0
    try:
        price = float(item.get("price_numeric") or item.get("price", 0))
    except (TypeError, ValueError):
        return 0

    ratio = price / monitor.price_to
    if ratio <= 0.40:
        return 3
    if ratio <= 0.60:
        return 2
    if ratio <= 0.80:
        return 1
    return 0


class VintedMonitor:
    def __init__(self, config_path: str = "monitors.json", proxy: str | None = None):
        self.config_path = Path(config_path)
        self._load_config()
        self.client = VintedClient(country=self.country, proxy=proxy)
        self.seen = _load_seen()

    def _load_config(self):
        data = json.loads(self.config_path.read_text())
        self.country: str = data.get("country", "pt")
        self.check_interval: int = int(data.get("check_interval", 60))
        self.discord_webhook: str | None = data.get("discord_webhook") or None
        self.telegram_token: str | None = data.get("telegram_token") or None
        self.telegram_chat_id: int | str | None = data.get("telegram_chat_id") or None
        self.monitors: list[MonitorConfig] = []
        for m in data.get("monitors", []):
            self.monitors.append(MonitorConfig(
                name=m["name"],
                search_text=m.get("search_text", ""),
                price_to=m.get("price_to"),
                price_from=m.get("price_from"),
                order=m.get("order", "newest_first"),
                per_page=m.get("per_page", 24),
                catalog_ids=m.get("catalog_ids", []),
                brand_ids=m.get("brand_ids", []),
                size_ids=m.get("size_ids", []),
                status_ids=m.get("status_ids", []),
            ))

    def check_monitor(self, monitor: MonitorConfig) -> list[Deal]:
        items = self.client.search(
            search_text=monitor.search_text,
            price_from=monitor.price_from,
            price_to=monitor.price_to,
            order=monitor.order,
            per_page=monitor.per_page,
            catalog_ids=monitor.catalog_ids or None,
            brand_ids=monitor.brand_ids or None,
            size_ids=monitor.size_ids or None,
            status_ids=monitor.status_ids or None,
        )

        seen_key = monitor.name
        if seen_key not in self.seen:
            self.seen[seen_key] = set()

        new_deals: list[Deal] = []
        for item in items:
            item_id = str(item.get("id", ""))
            if not item_id:
                continue
            if item_id not in self.seen[seen_key]:
                self.seen[seen_key].add(item_id)
                score = _deal_score(item, monitor)
                new_deals.append(Deal(item=item, monitor=monitor, score=score))

        _save_seen(self.seen)
        return new_deals

    def check_all(self) -> list[Deal]:
        all_deals: list[Deal] = []
        for monitor in self.monitors:
            deals = self.check_monitor(monitor)
            all_deals.extend(deals)
            time.sleep(1)  # small delay between monitors to avoid rate limiting
        return all_deals

    def add_monitor(self, config: dict):
        data = json.loads(self.config_path.read_text())
        data.setdefault("monitors", []).append(config)
        self.config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def remove_monitor(self, name: str) -> bool:
        data = json.loads(self.config_path.read_text())
        before = len(data.get("monitors", []))
        data["monitors"] = [m for m in data.get("monitors", []) if m["name"] != name]
        if len(data["monitors"]) < before:
            self.config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        return False


def load_monitors_from_config(config_path: str = "monitors.json") -> list[MonitorConfig]:
    """Read monitor configs without connecting to Vinted."""
    data = json.loads(Path(config_path).read_text())
    return [
        MonitorConfig(
            name=m["name"],
            search_text=m.get("search_text", ""),
            price_to=m.get("price_to"),
            price_from=m.get("price_from"),
            order=m.get("order", "newest_first"),
            per_page=m.get("per_page", 24),
            catalog_ids=m.get("catalog_ids", []),
            brand_ids=m.get("brand_ids", []),
            size_ids=m.get("size_ids", []),
            status_ids=m.get("status_ids", []),
        )
        for m in data.get("monitors", [])
    ]
