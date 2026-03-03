"""Simple working tests for the CAO Intelligence Engine."""

import pytest
from pathlib import Path
import json
import tempfile
import os

# Set test environment variables
os.environ["MISTRAL_API_KEY"] = "test-key"
os.environ["GOOGLE_API_KEY"] = "test-key"

from cao_engine.storage.json_store import JSONStore
from cao_engine.storage.moment_store import MomentStore
from cao_engine.models.momenten import Moment, MomentCategorie, MomentType, MomentenSet
from cao_engine.config import Settings


class TestStorage:
    """Test storage functionality."""

    def test_moment_store_creation(self):
        """Test creating a moment store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(data_dir=Path(tmpdir), log_level="DEBUG")
            store = MomentStore(settings)
            assert store._dir.exists()

    def test_saving_moment(self):
        """Test saving a moment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(data_dir=Path(tmpdir), log_level="DEBUG")
            store = MomentStore(settings)

            moment = Moment(
                cao_naam="test-cao",
                categorie=MomentCategorie.LOON,
                type=MomentType.LOONSVERHOGING,
                datum="2024-06-01",
                beschrijving="Test salary increase",
                element="loon",
                percentage=3.0,
                bron_tekst="Test source text"
            )

            # Create MomentenSet
            momenten_set = MomentenSet(
                cao_naam="test-cao",
                momenten=[moment]
            )

            store.save(momenten_set)

            # Check file was created (note the underscore in filename)
            file_path = Path(tmpdir) / "momenten" / "test_cao_momenten.json"
            assert file_path.exists()

    def test_loading_moments(self):
        """Test loading moments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(data_dir=Path(tmpdir), log_level="DEBUG")
            store = MomentStore(settings)

            moment = Moment(
                cao_naam="test-cao",
                categorie=MomentCategorie.LOON,
                type=MomentType.LOONSVERHOGING,
                datum="2024-06-01",
                beschrijving="Test salary increase",
                element="loon",
                percentage=3.0,
                bron_tekst="Test source text"
            )

            # Create MomentenSet
            momenten_set = MomentenSet(
                cao_naam="test-cao",
                momenten=[moment]
            )

            # Save and load
            store.save(momenten_set)
            loaded = store.load("test-cao")

            assert loaded is not None
            assert len(loaded.momenten) == 1
            assert loaded.momenten[0].beschrijving == "Test salary increase"


class TestValidation:
    """Test validation functionality."""

    def test_setu_validation_basic(self):
        """Test basic SETU validation."""
        from cao_engine.validation.setu_validator import SETUValidator

        validator = SETUValidator()

        # Valid SETU data
        valid_data = {
            "documentType": "InquiryPayEquity",
            "documentVersion": "2.0"
        }

        # Use the correct method name
        result = validator.validate_extraction(valid_data, "source markdown")
        assert result is not None
        assert result.total_fields > 0

    def test_cross_reference_validator_creation(self):
        """Test creating cross-reference validator."""
        from cao_engine.validation.cross_reference_validator import CrossReferenceValidator
        validator = CrossReferenceValidator()
        assert validator is not None


class TestAPI:
    """Test API functionality."""

    def test_health_endpoint(self):
        """Test the health endpoint."""
        from fastapi.testclient import TestClient
        from cao_engine.api.app import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_404_endpoint(self):
        """Test 404 handling."""
        from fastapi.testclient import TestClient
        from cao_engine.api.app import app

        client = TestClient(app)
        response = client.get("/nonexistent")

        assert response.status_code == 404


class TestModels:
    """Test data models."""

    def test_moment_creation(self):
        """Test creating a moment."""
        moment = Moment(
            cao_naam="test",
            categorie=MomentCategorie.LOON,
            type=MomentType.LOONSVERHOGING,
            beschrijving="Test",
            element="loon",
            bron_tekst="Source"
        )

        assert moment.cao_naam == "test"
        assert moment.categorie == MomentCategorie.LOON

    def test_moment_with_date(self):
        """Test moment with date."""
        moment = Moment(
            cao_naam="test",
            categorie=MomentCategorie.DOCUMENT,
            type=MomentType.CAO_INGANGSDATUM,
            datum="2024-01-01",
            beschrijving="CAO start",
            element="document",
            bron_tekst="Article 1"
        )

        assert str(moment.datum) == "2024-01-01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])