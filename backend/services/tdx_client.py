# backend/services/tdx_client.py
import httpx
from typing import Optional

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
        with httpx.Client() as http:
            response = http.post(url, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"TDX auth failed: {response.status_code} {response.text}")
        self.token = response.text.strip()

    def _headers(self) -> dict:
        if not self.token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        with httpx.Client() as http:
            response = http.request(method, url, headers=self._headers(), **kwargs)
        if response.status_code == 401:
            self.authenticate()
            with httpx.Client() as http:
                response = http.request(method, url, headers=self._headers(), **kwargs)
        response.raise_for_status()
        return response

    def list_articles(self, max_results: int = 5000) -> list[dict]:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/search"
        payload = {"MaxResults": max_results, "IsActive": True}
        response = self._request("POST", url, json=payload)
        return response.json()

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
