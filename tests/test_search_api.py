"""Tests for CAO search API endpoints."""

import pytest
from fastapi.testclient import TestClient
from cao_engine.api.app import app

client = TestClient(app)


class TestCAOSearchAPI:
    """Test the CAO search functionality."""

    def test_search_requires_at_least_one_parameter(self):
        """Test that search requires at least one search parameter."""
        response = client.get("/api/v2/search/cao")
        assert response.status_code == 400
        assert "at least one search parameter" in response.json()["detail"].lower()

    def test_search_by_company_name(self):
        """Test searching for CAO by company name."""
        response = client.get("/api/v2/search/cao?company=Achmea")
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data

        # Should find Achmea
        assert data["total"] >= 1
        assert any(r["company"] == "Achmea" for r in data["results"])

        # Check result structure
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "name" in result
            assert "sector" in result
            assert "match_score" in result
            assert "coverage_score" in result

    def test_search_by_sector(self):
        """Test searching for CAO by sector."""
        response = client.get("/api/v2/search/cao?sector=Metalektro")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 1
        assert data["results"][0]["sector"] == "Metalektro"

    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        response1 = client.get("/api/v2/search/cao?company=achmea")
        response2 = client.get("/api/v2/search/cao?company=ACHMEA")
        response3 = client.get("/api/v2/search/cao?company=Achmea")

        assert response1.json()["total"] > 0
        assert response1.json()["total"] == response2.json()["total"]
        assert response2.json()["total"] == response3.json()["total"]

    def test_search_with_no_results(self):
        """Test search that returns no results."""
        response = client.get("/api/v2/search/cao?company=NonExistentCompany123")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0
        assert len(data["suggestions"]) > 0  # Should provide suggestions

    def test_search_with_kvk_number(self):
        """Test searching by KVK number."""
        response = client.get("/api/v2/search/cao?kvk=12345678")
        assert response.status_code == 200

        data = response.json()
        # This is a mock KVK for Achmea
        if data["total"] > 0:
            assert data["results"][0]["company"] == "Achmea"
            assert data["results"][0]["match_type"] == "kvk"

    def test_search_partial_match(self):
        """Test that partial matches work."""
        response = client.get("/api/v2/search/cao?sector=handel")
        assert response.status_code == 200

        data = response.json()
        # Should match "Groothandel" and possibly "Detailhandel"
        assert any("handel" in r["sector"].lower() for r in data["results"])

    def test_search_with_pagination(self):
        """Test search with limit and offset."""
        response = client.get("/api/v2/search/cao?sector=handel&limit=1&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data["results"]) <= 1

    def test_search_active_only_filter(self):
        """Test that active_only filter works."""
        # Search with active_only=true (default)
        response = client.get("/api/v2/search/cao?sector=Metalektro&active_only=true")
        assert response.status_code == 200

        data = response.json()
        # All results should have future effective_to dates
        for result in data["results"]:
            assert result["effective_to"] > "2026-01-01"

    def test_sectors_endpoint(self):
        """Test the sectors list endpoint."""
        response = client.get("/api/v2/search/sectors")
        assert response.status_code == 200

        sectors = response.json()
        assert isinstance(sectors, list)
        assert len(sectors) > 0
        assert "Metalektro" in sectors
        assert "Transport" in sectors

    def test_companies_search_endpoint(self):
        """Test the companies autocomplete endpoint."""
        response = client.get("/api/v2/search/companies?q=ac")
        assert response.status_code == 200

        companies = response.json()
        assert isinstance(companies, list)
        # Should find Achmea
        assert any(c["name"] == "Achmea" for c in companies)

    def test_match_scoring(self):
        """Test that match scoring works correctly."""
        # Exact company match should score higher than partial
        response = client.get("/api/v2/search/cao?company=Achmea")
        data = response.json()

        if data["total"] > 0:
            assert data["results"][0]["match_score"] >= 90  # High score for exact match
            assert data["results"][0]["match_type"] == "company"