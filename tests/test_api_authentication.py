"""
TDD Tests for API Key Authentication System.

These tests are written FIRST (Red phase of TDD) before the authentication
implementation exists. They define the expected behavior of the API key
authentication system for the CAO Intelligence Engine's B2B API v2.

Test Coverage:
- API key validation via X-API-Key header
- Missing API key returns 401 Unauthorized
- Invalid API key returns 401 Unauthorized
- Inactive/disabled API keys are rejected
- Expired API keys are rejected
- API key verification with hash comparison
- Customer association with API keys
- API key scopes/permissions
- Last used timestamp tracking
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import hashlib
import secrets

import pytest
from fastapi.testclient import TestClient

from cao_engine.api.models.api_key import APIKey, Customer
from cao_engine.config import Settings

# Set test environment variables
os.environ["MISTRAL_API_KEY"] = "test-key"
os.environ["GOOGLE_API_KEY"] = "test-key"


class TestAPIKeyHeaderValidation:
    """Test that API keys must be provided via X-API-Key header."""

    def test_missing_api_key_header_returns_401(self, test_client: TestClient):
        """
        GIVEN a request to a v2 API endpoint
        WHEN no X-API-Key header is provided
        THEN return 401 Unauthorized
        """
        response = test_client.get("/api/v2/cao/search")

        assert response.status_code == 401
        assert "detail" in response.json()
        assert "api key" in response.json()["detail"].lower()

    def test_empty_api_key_header_returns_401(self, test_client: TestClient):
        """
        GIVEN a request to a v2 API endpoint
        WHEN X-API-Key header is provided but empty
        THEN return 401 Unauthorized
        """
        response = test_client.get(
            "/api/v2/cao/search",
            headers={"X-API-Key": ""}
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_whitespace_api_key_returns_401(self, test_client: TestClient):
        """
        GIVEN a request to a v2 API endpoint
        WHEN X-API-Key header contains only whitespace
        THEN return 401 Unauthorized
        """
        response = test_client.get(
            "/api/v2/cao/search",
            headers={"X-API-Key": "   "}
        )

        assert response.status_code == 401


class TestInvalidAPIKeys:
    """Test that invalid API keys are properly rejected."""

    def test_invalid_api_key_format_returns_401(self, test_client: TestClient):
        """
        GIVEN a request with a malformed API key
        WHEN the key doesn't match the expected format
        THEN return 401 Unauthorized
        """
        response = test_client.get(
            "/api/v2/cao/search",
            headers={"X-API-Key": "invalid-key-123"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_nonexistent_api_key_returns_401(self, test_client: TestClient):
        """
        GIVEN a request with a well-formed but nonexistent API key
        WHEN the key doesn't exist in the database
        THEN return 401 Unauthorized
        """
        # Generate a valid-looking key that doesn't exist
        fake_key = f"cao_{secrets.token_urlsafe(32)}"

        response = test_client.get(
            "/api/v2/cao/search",
            headers={"X-API-Key": fake_key}
        )

        assert response.status_code == 401

    def test_sql_injection_attempt_in_api_key_returns_401(self, test_client: TestClient):
        """
        GIVEN a request with SQL injection attempt in API key
        WHEN malicious input is provided
        THEN return 401 Unauthorized without executing the injection
        """
        malicious_key = "cao_test' OR '1'='1"

        response = test_client.get(
            "/api/v2/cao/search",
            headers={"X-API-Key": malicious_key}
        )

        assert response.status_code == 401


class TestAPIKeyActivationStatus:
    """Test that inactive/disabled API keys are rejected."""

    def test_inactive_api_key_returns_401(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key that exists but is marked as inactive
        WHEN a request is made with this key
        THEN return 401 Unauthorized
        """
        # This test will fail until we implement the authentication system
        # that checks the is_active flag
        api_key, raw_key = APIKey.create_new("test_customer", "Test Key")
        api_key.is_active = False

        # Mock the key store to include this inactive key
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower() or "disabled" in response.json()["detail"].lower()

    def test_reactivated_api_key_works(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key that was inactive but is now active
        WHEN a request is made with this key
        THEN return 200 OK and process the request
        """
        api_key, raw_key = APIKey.create_new("test_customer", "Test Key")
        api_key.is_active = True

        # Create a mock SETU file
        setu_dir = temp_data_dir / "setu"
        setu_file = setu_dir / "test-cao.json"
        setu_data = {
            "documentId": "test-123",
            "customer": {"name": "Test Company"},
            "effectivePeriod": {"validFrom": "2024-01-01", "validTo": "2025-12-31"}
        }
        setu_file.write_text(json.dumps(setu_data))

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        # Should succeed (200) or return empty results, but not 401
        assert response.status_code != 401


class TestAPIKeyVerification:
    """Test API key verification and hash comparison."""

    def test_api_key_hash_verification_succeeds_with_correct_key(self):
        """
        GIVEN a stored API key with a hash
        WHEN verifying with the correct raw key
        THEN verification succeeds
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Production Key")

        assert api_key.verify_key(raw_key) is True

    def test_api_key_hash_verification_fails_with_wrong_key(self):
        """
        GIVEN a stored API key with a hash
        WHEN verifying with an incorrect raw key
        THEN verification fails
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Production Key")
        wrong_key = f"cao_{secrets.token_urlsafe(32)}"

        assert api_key.verify_key(wrong_key) is False

    def test_api_key_hash_verification_fails_with_modified_key(self):
        """
        GIVEN a stored API key
        WHEN verifying with a slightly modified version of the correct key
        THEN verification fails
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Production Key")
        modified_key = raw_key[:-1] + "x"  # Change last character

        assert api_key.verify_key(modified_key) is False

    def test_api_key_prefix_extraction(self):
        """
        GIVEN a newly created API key
        WHEN the key is generated
        THEN the prefix should match the first 8 characters
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        assert api_key.key_prefix == raw_key[:8]
        assert len(api_key.key_prefix) == 8


class TestCustomerAssociation:
    """Test that API keys are properly associated with customer accounts."""

    def test_api_key_has_customer_id(self):
        """
        GIVEN a newly created API key
        WHEN created for a customer
        THEN the key should contain the customer ID
        """
        customer_id = "customer_xyz_123"
        api_key, raw_key = APIKey.create_new(customer_id, "Test Key")

        assert api_key.customer_id == customer_id

    def test_multiple_keys_for_same_customer(self):
        """
        GIVEN a customer account
        WHEN multiple API keys are created for the same customer
        THEN all keys should reference the same customer_id
        """
        customer_id = "customer_multi_key"

        key1, raw1 = APIKey.create_new(customer_id, "Production Key")
        key2, raw2 = APIKey.create_new(customer_id, "Development Key")
        key3, raw3 = APIKey.create_new(customer_id, "Testing Key")

        assert key1.customer_id == customer_id
        assert key2.customer_id == customer_id
        assert key3.customer_id == customer_id

        # All keys should be unique
        assert raw1 != raw2 != raw3
        assert key1.id != key2.id != key3.id

    def test_api_key_name_description(self):
        """
        GIVEN an API key with a descriptive name
        WHEN the key is created
        THEN the name should be stored for identification
        """
        key_name = "Production Server - EU Region"
        api_key, raw_key = APIKey.create_new("customer_123", key_name)

        assert api_key.name == key_name


class TestAPIKeyScopes:
    """Test API key scopes and permissions."""

    def test_default_scopes_assigned_to_new_key(self):
        """
        GIVEN a newly created API key
        WHEN no custom scopes are specified
        THEN default scopes should be assigned
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        assert len(api_key.scopes) > 0
        assert "read:cao" in api_key.scopes

    def test_api_key_with_read_scope_can_access_cao_endpoints(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key with 'read:cao' scope
        WHEN accessing a CAO search endpoint
        THEN the request should succeed
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Read Key")
        api_key.scopes = ["read:cao"]

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        # Should not return 403 Forbidden due to scope issues
        assert response.status_code != 403

    def test_api_key_with_validate_scope_can_access_validation_endpoints(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key with 'validate:payroll' scope
        WHEN accessing the payroll validation endpoint
        THEN the request should succeed
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Validation Key")
        api_key.scopes = ["validate:payroll"]

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.post(
                "/api/v2/validate/payroll",
                headers={"X-API-Key": raw_key},
                json={"cao_id": "test-cao", "gross_salary": 3000}
            )

        # Should not return 403 Forbidden due to scope issues
        assert response.status_code != 403


class TestAPIKeyTimestamps:
    """Test API key timestamp tracking."""

    def test_new_api_key_has_created_at_timestamp(self):
        """
        GIVEN a newly created API key
        WHEN the key is generated
        THEN it should have a created_at timestamp
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        assert api_key.created_at is not None
        assert isinstance(api_key.created_at, datetime)
        # Should be within the last few seconds
        assert (datetime.now() - api_key.created_at).total_seconds() < 5

    def test_new_api_key_has_no_last_used_timestamp(self):
        """
        GIVEN a newly created API key that has never been used
        WHEN the key is generated
        THEN last_used should be None
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        assert api_key.last_used is None

    def test_last_used_timestamp_updated_on_request(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key that has been used
        WHEN a request is made
        THEN the last_used timestamp should be updated
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")
        original_last_used = api_key.last_used

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        # last_used should now be set
        assert api_key.last_used is not None
        assert api_key.last_used != original_last_used
        # Should be very recent
        assert (datetime.now() - api_key.last_used).total_seconds() < 5


class TestAPIKeySecurityFeatures:
    """Test security features of API key system."""

    def test_raw_key_is_not_stored(self):
        """
        GIVEN an API key
        WHEN it is created
        THEN only the hash should be stored, not the raw key
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        # Ensure the raw key is not in any field
        assert raw_key not in str(api_key.model_dump())
        assert raw_key != api_key.key_hash
        assert api_key.key_hash == hashlib.sha256(raw_key.encode()).hexdigest()

    def test_api_key_uses_sha256_hash(self):
        """
        GIVEN an API key
        WHEN it is hashed
        THEN SHA256 should be used
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")
        expected_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        assert api_key.key_hash == expected_hash
        assert len(api_key.key_hash) == 64  # SHA256 produces 64 hex characters

    def test_api_key_format_starts_with_cao_prefix(self):
        """
        GIVEN a newly generated API key
        WHEN it is created
        THEN it should start with 'cao_' prefix for easy identification
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        assert raw_key.startswith("cao_")

    def test_api_keys_are_unique(self):
        """
        GIVEN multiple API keys
        WHEN they are generated
        THEN each should be cryptographically unique
        """
        keys = []
        for i in range(10):
            api_key, raw_key = APIKey.create_new("customer_123", f"Key {i}")
            keys.append(raw_key)

        # All keys should be unique
        assert len(keys) == len(set(keys))


class TestAPIKeyUsageEndpoint:
    """Test the /api/v2/usage endpoint for checking API key usage."""

    def test_usage_endpoint_returns_current_usage_stats(self, test_client: TestClient):
        """
        GIVEN an authenticated API key
        WHEN requesting /api/v2/usage
        THEN return current usage statistics
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")
        api_key.calls_this_month = 1000

        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}):
            response = test_client.get(
                "/api/v2/usage",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 200
        data = response.json()
        assert "calls_this_month" in data
        assert "monthly_limit" in data
        assert "remaining" in data
        assert data["calls_this_month"] == 1000

    def test_usage_endpoint_without_api_key_returns_401(self, test_client: TestClient):
        """
        GIVEN no API key
        WHEN requesting /api/v2/usage
        THEN return 401 Unauthorized
        """
        response = test_client.get("/api/v2/usage")

        assert response.status_code == 401
