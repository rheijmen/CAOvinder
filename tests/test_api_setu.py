"""
Test API endpoints for SETU document listing
TDD approach - write failing test first, then fix
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json

from cao_engine.api.app import app
from cao_engine.config import Settings


class TestSETUDocumentListing:
    """Test that the API correctly lists SETU documents"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def settings(self):
        return Settings()

    def test_api_lists_setu_documents(self, client, settings):
        """Test that /api/v1/caos endpoint returns SETU documents"""
        # Given: We have SETU documents in data/setu/
        setu_files = list(settings.setu_dir.glob("*.json"))
        assert len(setu_files) > 0, "No SETU files found for testing"

        # When: We request the CAO list
        response = client.get("/api/v1/caos")

        # Then: We should get our SETU documents
        assert response.status_code == 200
        data = response.json()

        # Should have at least one CAO (we extracted Groothandel Bloemen)
        assert data["total"] > 0, f"Expected CAOs but got {data['total']}"

        # Check the first CAO has expected fields
        if data["data"]:
            cao = data["data"][0]
            assert "id" in cao
            assert "name" in cao
            assert "effectivePeriod" in cao
            assert "status" in cao

    def test_api_cao_detail_returns_setu_data(self, client, settings):
        """Test that individual CAO detail includes SETU data"""
        # Given: We have at least one SETU document
        setu_files = list(settings.setu_dir.glob("*.json"))
        if not setu_files:
            pytest.skip("No SETU files available for testing")

        setu_id = setu_files[0].stem  # Get ID from filename

        # When: We request the specific CAO
        response = client.get(f"/api/v1/caos/{setu_id}")

        # Then: We should get the SETU document
        assert response.status_code == 200
        data = response.json()

        # Should have SETU fields
        assert "documentId" in data
        assert "remuneration" in data or "leaveArrangements" in data
        assert "_compliance" in data  # Our compliance metadata