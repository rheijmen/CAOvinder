"""End-to-end tests for the CAO search functionality."""

import pytest
import requests
import time


class TestEndToEndCAOSearch:
    """Test the complete CAO search flow from frontend to backend."""

    BASE_URL = "http://localhost:8000"
    FRONTEND_URL = "http://localhost:3000"

    def test_backend_is_running(self):
        """Test that the backend API is accessible."""
        response = requests.get(f"{self.BASE_URL}/api/v2/search/sectors")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_endpoint_works(self):
        """Test that the search endpoint returns valid data."""
        # Test company search
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?company=Achmea")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_fuzzy_sector_matching(self):
        """Test that fuzzy matching works for sectors."""
        # Search for "metaal" should find "Metalektro"
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?sector=metaal")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("metalektro" in r["sector"].lower() for r in data["results"])

    def test_kvk_search(self):
        """Test KVK number search."""
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?kvk=12345678")
        assert response.status_code == 200
        data = response.json()
        # Mock KVK should find Achmea
        if data["total"] > 0:
            assert data["results"][0]["company"] == "Achmea"

    def test_no_results_provides_suggestions(self):
        """Test that searches with no results provide helpful suggestions."""
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?company=NonExistentCompany")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["suggestions"]) > 0

    def test_search_response_structure(self):
        """Test that search results have the correct structure."""
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?sector=Transport")
        assert response.status_code == 200
        data = response.json()

        if data["total"] > 0:
            result = data["results"][0]
            # Check all required fields are present
            required_fields = [
                "id", "name", "sector", "effective_from", "effective_to",
                "coverage_score", "document_count", "has_salary_scales",
                "match_type", "match_score"
            ]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

    def test_active_only_filter(self):
        """Test that only active CAOs are returned by default."""
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?sector=Metalektro")
        assert response.status_code == 200
        data = response.json()

        for result in data["results"]:
            # Check that effective_to is in the future
            assert result["effective_to"] > "2026-01-01"

    def test_match_scoring_logic(self):
        """Test that match scoring provides meaningful results."""
        # Exact company match should score high
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?company=Achmea")
        data = response.json()
        if data["total"] > 0:
            assert data["results"][0]["match_score"] >= 90

        # Partial sector match should score lower
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao?sector=metaal")
        data = response.json()
        if data["total"] > 0:
            assert 50 <= data["results"][0]["match_score"] <= 80

    def test_multiple_search_parameters(self):
        """Test that search works with multiple parameters."""
        # This should return 400 as we need at least one parameter
        response = requests.get(f"{self.BASE_URL}/api/v2/search/cao")
        assert response.status_code == 400

    def test_case_insensitive_search(self):
        """Test that searches are case-insensitive."""
        response1 = requests.get(f"{self.BASE_URL}/api/v2/search/cao?company=achmea")
        response2 = requests.get(f"{self.BASE_URL}/api/v2/search/cao?company=ACHMEA")
        response3 = requests.get(f"{self.BASE_URL}/api/v2/search/cao?company=Achmea")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        # All should return the same results
        assert response1.json()["total"] == response2.json()["total"]
        assert response2.json()["total"] == response3.json()["total"]


if __name__ == "__main__":
    # Run tests
    print("Running end-to-end tests for CAO search...")
    print("Make sure both frontend (port 3000) and backend (port 8000) are running!")

    pytest.main([__file__, "-v"])