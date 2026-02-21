# backend/services/tdx_client.py
import time
import httpx
from typing import Optional

_TIMEOUT = httpx.Timeout(120.0)
_REQUEST_INTERVAL = 5.0  # seconds between requests to avoid TDX throttling


class TDXClient:
    def __init__(self, base_url: str, app_id: int, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.app_id = app_id
        self.username = username
        self.password = password
        self.token: Optional[str] = None

    def authenticate(self) -> None:
        url = f"{self.base_url}/api/auth/login"
        payload = {"UserName": self.username, "Password": self.password}
        with httpx.Client(timeout=_TIMEOUT) as http:
            response = http.post(url, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"TDX auth failed: {response.status_code} {response.text}")
        self.token = response.text.strip()

    def _headers(self) -> dict:
        if not self.token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        with httpx.Client(timeout=_TIMEOUT) as http:
            response = http.request(method, url, headers=self._headers(), **kwargs)
        if response.status_code == 401:
            self.authenticate()
            with httpx.Client(timeout=_TIMEOUT) as http:
                response = http.request(method, url, headers=self._headers(), **kwargs)
        # Respect TDX rate limit headers
        remaining = int(response.headers.get("x-ratelimit-remaining", 10))
        if remaining <= 2:
            reset_str = response.headers.get("x-ratelimit-reset")
            if reset_str:
                from email.utils import parsedate_to_datetime
                try:
                    reset_at = parsedate_to_datetime(reset_str).timestamp()
                    sleep_for = max(0.1, reset_at - time.time() + 0.5)
                    time.sleep(sleep_for)
                except Exception:
                    time.sleep(62)  # fallback: wait a full minute
            else:
                time.sleep(62)
        response.raise_for_status()
        return response

    # High-yield KB terms for the supplemental global pass.  Chosen because
    # they surface the most articles not already captured by the category pass.
    _SUPPLEMENTAL_TERMS = [
        "install", "zoom", "archive", "setup", "email",
        "network", "vpn", "password", "canvas", "dayforce",
    ]

    def list_articles(self) -> list[dict]:
        """Fetch all KB articles.

        The TDX search endpoint hard-caps at 50 results per call and exposes no
        real pagination — all Skip/Offset/PageIndex/MaxResults parameters are
        silently ignored.  Results are sorted by ModifiedDate desc, so large or
        older categories lose articles below the 50-result horizon.

        Strategy:
        1. Iterate every category (including sub-categories) and collect the 50
           most-recently-modified articles per category.
        2. Do a supplemental global pass with common KB search terms to surface
           articles that were pushed below the horizon in their category.

        All results are deduplicated by article ID.
        """
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/search"
        seen: set[int] = set()
        articles: list[dict] = []

        # Pass 1: per-category
        for cat in self._flatten_categories(self.list_categories()):
            time.sleep(_REQUEST_INTERVAL)
            batch: list[dict] = self._request(
                "POST", url, json={"CategoryID": cat["ID"]}
            ).json()
            self._collect(batch, seen, articles)

        # Pass 2: global supplemental searches
        for term in self._SUPPLEMENTAL_TERMS:
            time.sleep(_REQUEST_INTERVAL)
            batch = self._request(
                "POST", url, json={"SearchText": term}
            ).json()
            self._collect(batch, seen, articles)

        return articles

    def _collect(self, batch: list[dict], seen: set[int], articles: list[dict]) -> None:
        for a in batch:
            if a["ID"] not in seen:
                seen.add(a["ID"])
                articles.append(a)

    @staticmethod
    def _flatten_categories(categories: list[dict]) -> list[dict]:
        result = []
        for cat in categories:
            result.append(cat)
            subs = cat.get("Subcategories") or []
            if subs:
                result.extend(TDXClient._flatten_categories(subs))
        return result

    def get_article(self, article_id: int) -> dict:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/{article_id}"
        response = self._request("GET", url)
        return response.json()

    def update_article(self, article_id: int, new_body: str) -> dict:
        # Fetch current article to preserve all required fields
        current = self.get_article(article_id)
        current["Body"] = new_body
        time.sleep(_REQUEST_INTERVAL)
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/{article_id}"
        response = self._request("PUT", url, json=current)
        return response.json()

    def list_categories(self) -> list[dict]:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/categories"
        response = self._request("GET", url)
        return response.json()
