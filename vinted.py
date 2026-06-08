import re
import time
import requests


COUNTRY_DOMAINS = {
    "pt": "www.vinted.pt",
    "fr": "www.vinted.fr",
    "es": "www.vinted.es",
    "de": "www.vinted.de",
    "uk": "www.vinted.co.uk",
    "it": "www.vinted.it",
    "be": "www.vinted.be",
    "nl": "www.vinted.nl",
    "pl": "www.vinted.pl",
    "cz": "www.vinted.cz",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "application/json, text/plain, */*",
    "DNT": "1",
}


class VintedBlockedError(Exception):
    """Raised when Vinted blocks the request (IP or rate limit)."""


class VintedClient:
    def __init__(self, country: str = "pt", proxy: str | None = None):
        """
        country: código do país (pt, fr, es, de, uk, it, be, nl, pl, cz)
        proxy: URL do proxy opcional, ex: "http://user:pass@host:port"
               Útil se correres de um servidor/VPN.
        """
        domain = COUNTRY_DOMAINS.get(country, f"www.vinted.{country}")
        self.base_url = f"https://{domain}"
        self.api_url = f"{self.base_url}/api/v2"
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers["Referer"] = self.base_url + "/"
        self.session.headers["Origin"] = self.base_url
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self._last_auth = 0
        self._auth_ttl = 300  # re-auth every 5 minutes
        self._authenticate()

    def _authenticate(self):
        try:
            resp = self.session.get(
                self.base_url,
                headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                timeout=15,
            )
            if resp.status_code == 403:
                raise VintedBlockedError(
                    f"O Vinted bloqueou o acesso (HTTP 403). "
                    f"Certifica-te de que estás a correr o monitor em casa/VPN "
                    f"e não num servidor cloud. Resposta: {resp.text[:100]}"
                )
            resp.raise_for_status()
            # Extract CSRF token if present
            match = re.search(r'"CSRF_TOKEN"\s*:\s*"([^"]+)"', resp.text)
            if match:
                self.session.headers["X-CSRF-Token"] = match.group(1)
            self._last_auth = time.time()
        except VintedBlockedError:
            raise
        except requests.RequestException:
            pass  # Continue without auth — public catalog may still work

    def _maybe_refresh(self):
        if time.time() - self._last_auth > self._auth_ttl:
            self._authenticate()

    def search(
        self,
        search_text: str = "",
        price_from: float | None = None,
        price_to: float | None = None,
        order: str = "newest_first",
        per_page: int = 24,
        catalog_ids: list[int] | None = None,
        brand_ids: list[int] | None = None,
        size_ids: list[int] | None = None,
        status_ids: list[int] | None = None,
    ) -> list[dict]:
        self._maybe_refresh()

        params: dict = {
            "search_text": search_text,
            "per_page": per_page,
            "order": order,
        }
        if price_from is not None:
            params["price_from"] = price_from
        if price_to is not None:
            params["price_to"] = price_to
        if catalog_ids:
            params["catalog_ids[]"] = catalog_ids
        if brand_ids:
            params["brand_ids[]"] = brand_ids
        if size_ids:
            params["size_ids[]"] = size_ids
        if status_ids:
            params["status_ids[]"] = status_ids

        try:
            resp = self.session.get(
                f"{self.api_url}/catalog/items",
                params=params,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                # Re-authenticate and retry once
                self._authenticate()
                try:
                    resp = self.session.get(
                        f"{self.api_url}/catalog/items",
                        params=params,
                        timeout=20,
                    )
                    resp.raise_for_status()
                    return resp.json().get("items", [])
                except requests.RequestException:
                    return []
            return []
        except requests.RequestException:
            return []

    def item_url(self, item: dict) -> str:
        url = item.get("url", "")
        if url and not url.startswith("http"):
            url = self.base_url + url
        return url
