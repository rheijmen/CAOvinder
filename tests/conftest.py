"""
Shared pytest fixtures for CAO Intelligence Engine tests.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cao_engine.api.app import app
from cao_engine.config import Settings


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_settings() -> Settings:
    """Create test settings with mock API keys."""
    import os
    # Set environment variables for Settings
    os.environ["MISTRAL_API_KEY"] = "test-mistral-key"
    os.environ["GOOGLE_API_KEY"] = "test-google-key"

    settings = Settings(
        data_dir=Path(tempfile.mkdtemp()),
        log_level="DEBUG",
    )
    return settings


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = Path(tmpdir)
        # Create subdirectories
        (data_path / "raw").mkdir(exist_ok=True)
        (data_path / "ocr").mkdir(exist_ok=True)
        (data_path / "setu").mkdir(exist_ok=True)
        (data_path / "setu_raw").mkdir(exist_ok=True)
        (data_path / "setu_reports").mkdir(exist_ok=True)
        (data_path / "statutory").mkdir(exist_ok=True)
        (data_path / "momenten").mkdir(exist_ok=True)
        (data_path / "timelines").mkdir(exist_ok=True)
        yield data_path


@pytest.fixture
def sample_ocr_output() -> Dict[str, Any]:
    """Sample OCR output for testing."""
    return {
        "content": """
# CAO Metalektro 2024-2025

## 1. Looptijd
Deze cao loopt van 1 juni 2024 tot en met 31 december 2025.

## 2. Loongebouw

### Functiegroepen
- Groep A: Eenvoudige werkzaamheden
- Groep B: Standaard productiewerk
- Groep C: Gespecialiseerd werk

### Salarisschalen
| Groep | Minimum | Maximum |
|-------|---------|---------|
| A     | €2.100  | €2.800  |
| B     | €2.400  | €3.200  |
| C     | €2.800  | €4.000  |
        """,
        "tables": [
            {
                "headers": ["Groep", "Minimum", "Maximum"],
                "rows": [
                    ["A", "€2.100", "€2.800"],
                    ["B", "€2.400", "€3.200"],
                    ["C", "€2.800", "€4.000"],
                ]
            }
        ],
        "metadata": {
            "pages": 45,
            "processing_time": 12.5,
            "language": "nl"
        }
    }


@pytest.fixture
def sample_setu_data() -> Dict[str, Any]:
    """Sample SETU v2.0 data for testing."""
    return {
        "documentType": "InquiryPayEquity",
        "documentVersion": "2.0",
        "supplier": {
            "supplierId": "TEST123",
            "supplierName": "Test Uitzendbureau B.V."
        },
        "customer": {
            "customerId": "CUST456",
            "customerName": "Test Inlener B.V."
        },
        "referenceData": {
            "caoName": "CAO Metalektro",
            "caoCode": "METAL2024",
            "validFrom": "2024-06-01",
            "validTo": "2025-12-31"
        },
        "payEquity": {
            "wageStructure": {
                "functionGroups": [
                    {
                        "code": "A",
                        "name": "Eenvoudige werkzaamheden",
                        "minWage": 2100.00,
                        "maxWage": 2800.00
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_cao_document() -> Dict[str, Any]:
    """Sample CAO document data."""
    return {
        "name": "CAO Metalektro",
        "version": "2024-2025",
        "effective_date": "2024-06-01",
        "expiry_date": "2025-12-31",
        "pdf_file": "cao-metalektro-2024.pdf",
        "ocr_status": "completed",
        "extraction_status": "pending"
    }


@pytest.fixture
def mock_mistral_client():
    """Mock Mistral AI client."""
    with patch("cao_engine.ocr.client.Mistral") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client."""
    with patch("cao_engine.extraction.gemini_primary.genai") as mock:
        yield mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    with patch("cao_engine.extraction.claude_setu_extractor.Anthropic") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client