# backend/services/tdx_client.py
import time
import httpx
from typing import Optional

_TIMEOUT = httpx.Timeout(30.0)


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
            with httpx.Client() as http:
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

    def list_articles(self) -> list[dict]:
        """Fetch all KB articles by iterating every category.

        The TDX search endpoint hard-caps at 50 results per call regardless of
        MaxResults, so we iterate all categories (including subcategories) and
        deduplicate by article ID to get the full KB.
        """
        categories = self.list_categories()
        seen: set[int] = set()
        articles: list[dict] = []
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/search"
        for cat in self._flatten_categories(categories):
            response = self._request("POST", url, json={"CategoryID": cat["ID"]})
            for article in response.json():
                if article["ID"] not in seen:
                    seen.add(article["ID"])
                    articles.append(article)
        return articles

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
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/{article_id}"
        response = self._request("POST", url, json={"Body": new_body})
        return response.json()

    def list_categories(self) -> list[dict]:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/categories"
        response = self._request("GET", url)
        return response.json()
