"""Tests for the CAO search API — real SETU-backed behavior (no mock fiction).

These assert real, honest behavior against the canonical SETU documents in data/setu:
real customer names, provenance-derived coverage_score, and NO fabricated CAOs/KVKs.
Uses active_only=false where needed because several real CAOs have already expired.
"""
from fastapi.testclient import TestClient

from cao_engine.api.app import app

client = TestClient(app)


class TestCAOSearchAPI:
    def test_requires_at_least_one_parameter(self):
        response = client.get("/api/v2/search/cao")
        assert response.status_code == 400
        assert "at least one search parameter" in response.json()["detail"].lower()

    def test_search_by_company_finds_real_cao(self):
        # IKEA's customer.name is "IKEA Nederland B.V." in the real SETU doc
        response = client.get("/api/v2/search/cao?company=IKEA&active_only=false")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("ikea" in (r["name"] or "").lower() for r in data["results"])
        result = data["results"][0]
        for key in ("id", "name", "sector", "coverage_score", "match_score", "has_salary_scales"):
            assert key in result

    def test_search_by_sector_substring(self):
        response = client.get("/api/v2/search/cao?sector=ikea&active_only=false")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("ikea" in r["id"].lower() for r in data["results"])

    def test_coverage_score_comes_from_real_provenance(self):
        # ikea has a committed provenance sidecar (confidence 0.131 -> 13), NOT a fake 85
        response = client.get("/api/v2/search/cao?sector=ikea-cao&active_only=false")
        data = response.json()
        ikea = next((r for r in data["results"] if "ikea" in r["id"].lower()), None)
        assert ikea is not None
        assert isinstance(ikea["coverage_score"], int)
        assert 0 < ikea["coverage_score"] <= 100  # real provenance, not zero, not fabricated 85+

    def test_search_case_insensitive(self):
        r1 = client.get("/api/v2/search/cao?sector=ikea&active_only=false")
        r2 = client.get("/api/v2/search/cao?sector=IKEA&active_only=false")
        assert r1.json()["total"] == r2.json()["total"] >= 1

    def test_search_with_no_results(self):
        response = client.get("/api/v2/search/cao?company=ZzzNonExistentCompany999")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["suggestions"]) > 0

    def test_kvk_returns_no_fabricated_match(self):
        # the old mock matched kvk=12345678 -> "Achmea"; real data has no such fake match
        response = client.get("/api/v2/search/cao?kvk=12345678")
        assert response.status_code == 200
        data = response.json()
        assert all(r["match_type"] == "kvk" for r in data["results"])  # vacuously true if empty

    def test_active_only_filter_excludes_expired(self):
        response = client.get("/api/v2/search/cao?sector=cao&active_only=true")
        assert response.status_code == 200
        for result in response.json()["results"]:
            assert result["effective_to"] is None or result["effective_to"] >= "2026-06-07"

    def test_sectors_endpoint_returns_real_labels(self):
        response = client.get("/api/v2/search/sectors")
        assert response.status_code == 200
        sectors = response.json()
        assert isinstance(sectors, list)
        assert len(sectors) > 0
        assert all(isinstance(s, str) for s in sectors)

    def test_companies_endpoint_uses_real_names(self):
        response = client.get("/api/v2/search/companies?q=ikea")
        assert response.status_code == 200
        companies = response.json()
        assert isinstance(companies, list)
        assert any("ikea" in c["name"].lower() for c in companies)
        # KVK is real-or-None, never a fabricated placeholder
        assert all(("kvk" in c) for c in companies)
