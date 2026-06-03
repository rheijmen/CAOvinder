from fastapi.testclient import TestClient

from cao_engine.api.app import app

client = TestClient(app)


def test_openapi_json_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "CAO Centraal"


def test_llms_txt_served_as_markdown():
    r = client.get("/llms.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "# CAO Centraal" in r.text
    assert "/openapi.json" in r.text
    assert "/api/v2/cao/" in r.text


def test_llms_full_txt_available():
    r = client.get("/llms-full.txt")
    assert r.status_code == 200
    assert "# CAO Centraal" in r.text
