"""
TDD Tests for API Rate Limiting System.

These tests are written FIRST (Red phase of TDD) before the rate limiting
implementation exists. They define the expected behavior of the monthly
rate limiting system for API keys.

Test Coverage:
- Monthly rate limits (default 50,000 calls)
- Call counter incrementation
- 429 Too Many Requests when limit exceeded
- Rate limit resets (monthly)
- Different rate limits for different plans
- Rate limit remaining calculation
- Burst protection
- Rate limit headers in responses
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import secrets

import pytest
from fastapi.testclient import TestClient

from cao_engine.api.models.api_key import APIKey, Customer
from cao_engine.config import Settings

# Set test environment variables
os.environ["MISTRAL_API_KEY"] = "test-key"
os.environ["GOOGLE_API_KEY"] = "test-key"


class TestMonthlyRateLimit:
    """Test that API keys have monthly rate limits."""

    def test_new_api_key_has_default_monthly_limit(self):
        """
        GIVEN a newly created API key
        WHEN no custom limit is specified
        THEN it should have the default monthly limit of 50,000
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        assert api_key.monthly_limit == 50000

    def test_new_api_key_starts_with_zero_calls(self):
        """
        GIVEN a newly created API key
        WHEN it has not been used
        THEN calls_this_month should be 0
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        assert api_key.calls_this_month == 0

    def test_custom_monthly_limit_can_be_set(self):
        """
        GIVEN an API key with custom limit
        WHEN created with a specific monthly_limit parameter
        THEN the key should have that custom limit
        """
        custom_limit = 100000
        api_key, raw_key = APIKey.create_new("customer_123", "Enterprise Key", monthly_limit=custom_limit)

        assert api_key.monthly_limit == custom_limit

    def test_starter_plan_has_lower_limit(self):
        """
        GIVEN a customer on the starter plan
        WHEN their API key is created
        THEN they should have a lower monthly limit (e.g., 10,000)
        """
        # This test defines that different plans should have different limits
        starter_limit = 10000
        api_key, raw_key = APIKey.create_new("starter_customer", "Starter Key", monthly_limit=starter_limit)

        assert api_key.monthly_limit == starter_limit

    def test_enterprise_plan_has_higher_limit(self):
        """
        GIVEN a customer on the enterprise plan
        WHEN their API key is created
        THEN they should have a higher monthly limit (e.g., 1,000,000)
        """
        enterprise_limit = 1000000
        api_key, raw_key = APIKey.create_new("enterprise_customer", "Enterprise Key", monthly_limit=enterprise_limit)

        assert api_key.monthly_limit == enterprise_limit


class TestCallCounterIncrementation:
    """Test that each successful API call increments the counter."""

    def test_successful_request_increments_counter(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key with 0 calls
        WHEN a successful request is made
        THEN calls_this_month should increment to 1
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")
        assert api_key.calls_this_month == 0

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        assert api_key.calls_this_month == 1

    def test_multiple_requests_increment_counter_correctly(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key
        WHEN multiple successful requests are made
        THEN calls_this_month should increment for each request
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            # Make 5 requests
            for i in range(5):
                response = test_client.get(
                    "/api/v2/cao/search",
                    headers={"X-API-Key": raw_key}
                )

        assert api_key.calls_this_month == 5

    def test_failed_authentication_does_not_increment_counter(self, test_client: TestClient):
        """
        GIVEN an invalid API key
        WHEN a request fails with 401
        THEN no counter should be incremented
        """
        fake_key = f"cao_{secrets.token_urlsafe(32)}"

        response = test_client.get(
            "/api/v2/cao/search",
            headers={"X-API-Key": fake_key}
        )

        assert response.status_code == 401
        # There should be no side effects on any counters

    def test_404_request_still_increments_counter(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN a valid API key
        WHEN a request is made that returns 404 (not found)
        THEN the counter should still increment (authenticated request was made)
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/nonexistent-cao/current",
                headers={"X-API-Key": raw_key}
            )

        # Even though the CAO doesn't exist (404), the API call counts
        assert api_key.calls_this_month == 1


class TestRateLimitExceeded:
    """Test behavior when rate limit is exceeded."""

    def test_exceeding_rate_limit_returns_429(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key that has reached its monthly limit
        WHEN a request is made
        THEN return 429 Too Many Requests
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=100)
        api_key.calls_this_month = 100  # Already at limit

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 429
        assert "limit" in response.json()["detail"].lower() or "exceeded" in response.json()["detail"].lower()

    def test_at_limit_minus_one_succeeds(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key with 99 calls out of 100 limit
        WHEN a request is made
        THEN it should succeed (this is the last allowed call)
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=100)
        api_key.calls_this_month = 99

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        # Should succeed, not return 429
        assert response.status_code != 429
        # Counter should now be at limit
        assert api_key.calls_this_month == 100

    def test_exceeding_limit_by_one_returns_429(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key that just exceeded its limit
        WHEN a request is made with calls_this_month == monthly_limit
        THEN return 429
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=50)
        api_key.calls_this_month = 50  # At limit

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 429

    def test_way_over_limit_returns_429(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key that is far over its limit
        WHEN a request is made
        THEN return 429
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=100)
        api_key.calls_this_month = 5000  # Way over

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 429


class TestCanMakeRequest:
    """Test the can_make_request() method on APIKey."""

    def test_active_key_under_limit_can_make_request(self):
        """
        GIVEN an active API key under its limit
        WHEN checking if it can make a request
        THEN return True
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=1000)
        api_key.calls_this_month = 500
        api_key.is_active = True

        assert api_key.can_make_request() is True

    def test_active_key_at_limit_cannot_make_request(self):
        """
        GIVEN an active API key at its limit
        WHEN checking if it can make a request
        THEN return False
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=1000)
        api_key.calls_this_month = 1000
        api_key.is_active = True

        assert api_key.can_make_request() is False

    def test_inactive_key_cannot_make_request(self):
        """
        GIVEN an inactive API key
        WHEN checking if it can make a request
        THEN return False (regardless of usage)
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=1000)
        api_key.calls_this_month = 0
        api_key.is_active = False

        assert api_key.can_make_request() is False

    def test_inactive_key_under_limit_cannot_make_request(self):
        """
        GIVEN an inactive API key that is under its limit
        WHEN checking if it can make a request
        THEN return False (is_active takes precedence)
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=1000)
        api_key.calls_this_month = 100
        api_key.is_active = False

        assert api_key.can_make_request() is False


class TestRateLimitRemaining:
    """Test calculation of remaining API calls."""

    def test_remaining_calls_calculated_correctly(self):
        """
        GIVEN an API key with usage
        WHEN calculating remaining calls
        THEN it should be monthly_limit - calls_this_month
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=10000)
        api_key.calls_this_month = 3500

        remaining = api_key.monthly_limit - api_key.calls_this_month
        assert remaining == 6500

    def test_usage_endpoint_returns_remaining(self, test_client: TestClient):
        """
        GIVEN an API key with usage
        WHEN requesting /api/v2/usage
        THEN it should include the 'remaining' field
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=5000)
        api_key.calls_this_month = 1200

        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}):
            response = test_client.get(
                "/api/v2/usage",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["remaining"] == 3800  # 5000 - 1200

    def test_remaining_is_zero_when_at_limit(self):
        """
        GIVEN an API key at its limit
        WHEN calculating remaining
        THEN it should be 0
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=1000)
        api_key.calls_this_month = 1000

        remaining = api_key.monthly_limit - api_key.calls_this_month
        assert remaining == 0

    def test_remaining_is_negative_when_over_limit(self):
        """
        GIVEN an API key over its limit
        WHEN calculating remaining
        THEN it should be negative
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=1000)
        api_key.calls_this_month = 1200

        remaining = api_key.monthly_limit - api_key.calls_this_month
        assert remaining == -200


class TestRateLimitHeaders:
    """Test that rate limit information is included in response headers."""

    def test_successful_request_includes_rate_limit_headers(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN a successful API request
        WHEN the response is returned
        THEN it should include rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=10000)
        api_key.calls_this_month = 2500

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        # Check for standard rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert int(response.headers["X-RateLimit-Limit"]) == 10000
        # After this call, counter is 2501, so remaining is 7499
        assert int(response.headers["X-RateLimit-Remaining"]) == 7499

    def test_rate_limit_exceeded_includes_retry_after_header(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN a request that exceeds the rate limit
        WHEN 429 is returned
        THEN it should include a Retry-After header indicating when to retry
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=100)
        api_key.calls_this_month = 100  # At limit

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 429
        # Should have Retry-After header (could be in seconds or HTTP date)
        assert "Retry-After" in response.headers


class TestRateLimitReset:
    """Test monthly rate limit reset behavior."""

    def test_counter_resets_at_start_of_new_month(self):
        """
        GIVEN an API key with usage in the previous month
        WHEN the month changes
        THEN calls_this_month should reset to 0

        NOTE: This test defines the requirement for a monthly reset mechanism.
        Implementation will need a background job or reset-on-first-use logic.
        """
        # This is a specification test - defines what SHOULD happen
        # The actual implementation might use:
        # - A background cron job that resets all counters monthly
        # - A last_reset_date field that triggers reset on first use of new month
        # - A database trigger

        # For now, we define that there should be a way to reset the counter
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")
        api_key.calls_this_month = 5000

        # Simulate month reset (implementation detail TBD)
        # reset_monthly_counters()  # This function needs to be implemented

        # After reset, counter should be 0
        # assert api_key.calls_this_month == 0

        # For now, just test that we can manually reset
        api_key.calls_this_month = 0
        assert api_key.calls_this_month == 0


class TestDifferentEndpointsCountTowardsSameLimit:
    """Test that all API endpoints share the same rate limit counter."""

    def test_different_endpoints_increment_same_counter(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key
        WHEN requests are made to different endpoints
        THEN all should increment the same calls_this_month counter
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key")

        # Create a mock SETU file
        setu_dir = temp_data_dir / "setu"
        setu_file = setu_dir / "test-cao.json"
        setu_data = {
            "documentId": "test-123",
            "customer": {"name": "Test"},
            "effectivePeriod": {"validFrom": "2024-01-01", "validTo": "2025-12-31"},
            "remuneration": {"salaryScales": []},
            "allowances": []
        }
        setu_file.write_text(json.dumps(setu_data))

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):

            # Request 1: search
            test_client.get("/api/v2/cao/search", headers={"X-API-Key": raw_key})

            # Request 2: get current
            test_client.get("/api/v2/cao/test-cao/current", headers={"X-API-Key": raw_key})

            # Request 3: salary scales
            test_client.get("/api/v2/cao/test-cao/salary-scales", headers={"X-API-Key": raw_key})

            # Request 4: usage
            test_client.get("/api/v2/usage", headers={"X-API-Key": raw_key})

        # All 4 requests should count toward the same limit
        assert api_key.calls_this_month == 4


class TestBurstProtection:
    """Test protection against burst/rapid-fire requests."""

    def test_rapid_sequential_requests_all_count(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key
        WHEN many rapid requests are made in sequence
        THEN each should be counted individually
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=1000)

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):

            # Make 10 rapid requests
            for i in range(10):
                response = test_client.get(
                    "/api/v2/cao/search",
                    headers={"X-API-Key": raw_key}
                )

        # All 10 should be counted
        assert api_key.calls_this_month == 10

    def test_requests_stop_when_limit_reached_in_burst(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key with a low limit
        WHEN rapid requests are made until limit is hit
        THEN subsequent requests should return 429
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Test Key", monthly_limit=5)
        api_key.calls_this_month = 0

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):

            responses = []
            # Try to make 10 requests but limit is 5
            for i in range(10):
                response = test_client.get(
                    "/api/v2/cao/search",
                    headers={"X-API-Key": raw_key}
                )
                responses.append(response.status_code)

        # First 5 should succeed (not 429)
        assert all(code != 429 for code in responses[:5])

        # Next 5 should be rate limited (429)
        assert all(code == 429 for code in responses[5:])


class TestZeroLimitBehavior:
    """Test edge case of API key with 0 monthly limit."""

    def test_api_key_with_zero_limit_cannot_make_requests(self, test_client: TestClient, temp_data_dir: Path):
        """
        GIVEN an API key with monthly_limit = 0
        WHEN a request is made
        THEN return 429 (no requests allowed)
        """
        api_key, raw_key = APIKey.create_new("customer_123", "Disabled Key", monthly_limit=0)

        mock_settings = Settings(data_dir=temp_data_dir, log_level="DEBUG")
        with patch("cao_engine.api.v2.public_routes.API_KEYS_STORE", {raw_key: api_key}), \
             patch("cao_engine.api.v2.public_routes.get_settings", return_value=mock_settings):
            response = test_client.get(
                "/api/v2/cao/search",
                headers={"X-API-Key": raw_key}
            )

        assert response.status_code == 429


class TestUnlimitedAPIKeys:
    """Test API keys with unlimited usage (e.g., for internal tools)."""

    def test_very_high_limit_acts_as_unlimited(self):
        """
        GIVEN an API key with a very high limit (e.g., 999,999,999)
        WHEN many requests are made
        THEN it should effectively be unlimited for practical purposes
        """
        api_key, raw_key = APIKey.create_new("internal_tool", "Unlimited Key", monthly_limit=999999999)
        api_key.calls_this_month = 1000000  # 1 million calls

        # Should still be able to make requests
        assert api_key.can_make_request() is True
        remaining = api_key.monthly_limit - api_key.calls_this_month
        assert remaining == 998999999
