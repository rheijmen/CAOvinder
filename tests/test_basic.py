"""
Basic tests to verify the test infrastructure is working.
"""

import pytest
from fastapi.testclient import TestClient
from cao_engine.api.app import app


class TestBasicEndpoints:
    """Basic API tests that work."""

    def test_health_check(self):
        """Test health endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_404_on_unknown_route(self):
        """Test 404 on unknown route."""
        client = TestClient(app)
        response = client.get("/unknown-route")
        assert response.status_code == 404


class TestSimpleFunctions:
    """Test simple functions."""

    def test_basic_math(self):
        """Test basic math works."""
        assert 1 + 1 == 2
        assert 10 * 5 == 50

    def test_string_operations(self):
        """Test string operations."""
        test_string = "CAO Intelligence Engine"
        assert "CAO" in test_string
        assert test_string.lower() == "cao intelligence engine"
        assert test_string.upper() == "CAO INTELLIGENCE ENGINE"

    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3, 4, 5]
        assert len(test_list) == 5
        assert sum(test_list) == 15
        assert max(test_list) == 5
        assert min(test_list) == 1


class TestDataStructures:
    """Test data structure operations."""

    def test_dictionary_operations(self):
        """Test dictionary operations."""
        test_dict = {"cao": "Metalektro", "year": 2024, "active": True}
        assert test_dict["cao"] == "Metalektro"
        assert test_dict.get("year") == 2024
        assert test_dict.get("missing", "default") == "default"
        assert len(test_dict) == 3

    def test_set_operations(self):
        """Test set operations."""
        set_a = {1, 2, 3, 4}
        set_b = {3, 4, 5, 6}

        assert set_a.intersection(set_b) == {3, 4}
        assert set_a.union(set_b) == {1, 2, 3, 4, 5, 6}
        assert set_a.difference(set_b) == {1, 2}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])