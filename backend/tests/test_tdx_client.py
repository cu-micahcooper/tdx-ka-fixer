# backend/tests/test_tdx_client.py
import pytest
import respx
import httpx
from services.tdx_client import TDXClient

TDX_BASE = "https://test.tdx.com/TDWebApi"

@pytest.fixture
def client():
    return TDXClient(
        base_url=TDX_BASE,
        app_id=42,
        beid="test-beid",
        web_services_key="test-wskey",
    )

@respx.mock
def test_authenticate_stores_token(client):
    respx.post(f"{TDX_BASE}/api/auth/loginadmin").mock(
        return_value=httpx.Response(200, json="fake-token-string")
    )
    client.authenticate()
    assert client.token == "fake-token-string"

@respx.mock
def test_authenticate_raises_on_failure(client):
    respx.post(f"{TDX_BASE}/api/auth/loginadmin").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(RuntimeError, match="TDX auth failed"):
        client.authenticate()

SAMPLE_ARTICLE = {
    "ID": 123,
    "Subject": "How to reset password",
    "Body": "<p>Click forgot password.</p>",
    "CategoryID": 5,
    "CategoryName": "Account",
    "CreatedDate": "2024-01-01T00:00:00Z",
    "ModifiedDate": "2024-06-01T00:00:00Z",
    "NumViews": 42,
    "IsActive": True,
}

@respx.mock
def test_list_articles(client):
    client.token = "fake-token"
    respx.post(f"{TDX_BASE}/api/42/knowledgebase/search").mock(
        return_value=httpx.Response(200, json=[SAMPLE_ARTICLE])
    )
    articles = client.list_articles()
    assert len(articles) == 1
    assert articles[0]["ID"] == 123

@respx.mock
def test_get_article(client):
    client.token = "fake-token"
    respx.get(f"{TDX_BASE}/api/42/knowledgebase/123").mock(
        return_value=httpx.Response(200, json=SAMPLE_ARTICLE)
    )
    article = client.get_article(123)
    assert article["Subject"] == "How to reset password"

@respx.mock
def test_update_article(client):
    client.token = "fake-token"
    respx.post(f"{TDX_BASE}/api/42/knowledgebase/123").mock(
        return_value=httpx.Response(200, json={**SAMPLE_ARTICLE, "Body": "New body"})
    )
    result = client.update_article(123, "New body")
    assert result["Body"] == "New body"

@respx.mock
def test_list_categories(client):
    client.token = "fake-token"
    respx.get(f"{TDX_BASE}/api/42/knowledgebase/categories").mock(
        return_value=httpx.Response(200, json=[{"ID": 1, "Name": "General"}])
    )
    categories = client.list_categories()
    assert len(categories) == 1
    assert categories[0]["Name"] == "General"

@respx.mock
def test_401_triggers_reauthentication_and_retry(client):
    """A 401 response should cause re-authentication and a successful retry."""
    client.token = "expired-token"

    # First call returns 401; second call (after re-auth) returns 200
    search_route = respx.post(f"{TDX_BASE}/api/42/knowledgebase/search")
    search_route.side_effect = [
        httpx.Response(401, text="Unauthorized"),
        httpx.Response(200, json=[SAMPLE_ARTICLE]),
    ]

    # Re-auth endpoint returns a new token
    respx.post(f"{TDX_BASE}/api/auth/loginadmin").mock(
        return_value=httpx.Response(200, json="new-token")
    )

    articles = client.list_articles()
    assert client.token == "new-token"
    assert len(articles) == 1
    assert articles[0]["ID"] == 123
