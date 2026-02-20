# backend/services/tdx_client.py
import httpx
from typing import Optional

class TDXClient:
    def __init__(self, base_url: str, app_id: int, beid: str, web_services_key: str):
        self.base_url = base_url.rstrip("/")
        self.app_id = app_id
        self.beid = beid
        self.web_services_key = web_services_key
        self.token: Optional[str] = None

    def authenticate(self) -> None:
        url = f"{self.base_url}/api/auth/loginadmin"
        payload = {"BEID": self.beid, "WebServicesKey": self.web_services_key}
        with httpx.Client() as http:
            response = http.post(url, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"TDX auth failed: {response.status_code} {response.text}")
        self.token = response.json()

    def _headers(self) -> dict:
        if not self.token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    def list_articles(self, max_results: int = 5000) -> list[dict]:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/search"
        payload = {"MaxResults": max_results, "IsActive": True}
        with httpx.Client() as http:
            response = http.post(url, json=payload, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_article(self, article_id: int) -> dict:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/{article_id}"
        with httpx.Client() as http:
            response = http.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def update_article(self, article_id: int, new_body: str) -> dict:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/{article_id}"
        with httpx.Client() as http:
            response = http.post(url, json={"Body": new_body}, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def list_categories(self) -> list[dict]:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/categories"
        with httpx.Client() as http:
            response = http.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()
