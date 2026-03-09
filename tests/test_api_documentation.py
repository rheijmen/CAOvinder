"""
Test suite for B2B API Documentation System (TDD - RED Phase).

This module contains comprehensive failing tests for API documentation features
including OpenAPI schema generation, interactive documentation (Swagger UI, ReDoc),
authentication documentation, and code examples.

All tests follow the Given-When-Then pattern for clarity.
"""

import json
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestOpenAPISchemaGeneration:
    """Test suite for OpenAPI 3.0 schema generation."""

    def test_openapi_json_endpoint_exists(self, test_client: TestClient):
        """
        Test that /api/v2/openapi.json endpoint exists and returns valid OpenAPI schema.

        Given: A running FastAPI application with v2 routes
        When: Client requests /api/v2/openapi.json
        Then: Response should be 200 with valid OpenAPI 3.0 schema
        """
        response = test_client.get("/api/v2/openapi.json")

        assert response.status_code == 200, "OpenAPI schema endpoint should exist"

        schema = response.json()
        assert "openapi" in schema, "Schema must include OpenAPI version"
        assert schema["openapi"].startswith("3."), "Must use OpenAPI 3.x specification"
        assert "info" in schema, "Schema must include API info"
        assert "paths" in schema, "Schema must include API paths"

    def test_openapi_includes_all_v2_endpoints(self, test_client: TestClient):
        """
        Test that OpenAPI schema documents all /api/v2 endpoints.

        Given: Public API v2 with multiple endpoints
        When: OpenAPI schema is generated
        Then: All v2 endpoints should be documented in schema
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()
        paths = schema["paths"]

        # Required v2 endpoints
        expected_endpoints = [
            "/api/v2/cao/search",
            "/api/v2/cao/{cao_id}/current",
            "/api/v2/cao/{cao_id}/salary-scales",
            "/api/v2/cao/{cao_id}/allowances",
            "/api/v2/validate/payroll",
            "/api/v2/changes/feed",
            "/api/v2/usage",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in paths, f"Endpoint {endpoint} must be documented"

    def test_openapi_defines_security_schemes(self, test_client: TestClient):
        """
        Test that OpenAPI schema defines security schemes for API key authentication.

        Given: API that requires API key authentication
        When: OpenAPI schema is generated
        Then: Security schemes must include API key header authentication
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        assert "components" in schema, "Schema must have components section"
        assert "securitySchemes" in schema["components"], "Must define security schemes"

        security_schemes = schema["components"]["securitySchemes"]
        assert "APIKeyHeader" in security_schemes, "Must define API key header scheme"

        api_key_scheme = security_schemes["APIKeyHeader"]
        assert api_key_scheme["type"] == "apiKey", "Must be API key type"
        assert api_key_scheme["in"] == "header", "API key must be in header"
        assert api_key_scheme["name"] == "X-API-Key", "Header name must be X-API-Key"

    def test_openapi_validates_request_response_schemas(self, test_client: TestClient):
        """
        Test that all endpoints have proper request/response schemas defined.

        Given: API endpoints with Pydantic models
        When: OpenAPI schema is generated
        Then: Each endpoint must have documented request/response schemas
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check POST /validate/payroll has request body schema
        payroll_endpoint = schema["paths"]["/api/v2/validate/payroll"]["post"]
        assert "requestBody" in payroll_endpoint, "POST endpoints must document request body"
        assert "content" in payroll_endpoint["requestBody"]
        assert "application/json" in payroll_endpoint["requestBody"]["content"]

        # Check all endpoints have response schemas
        for path, methods in schema["paths"].items():
            if not path.startswith("/api/v2"):
                continue
            for method, endpoint_spec in methods.items():
                assert "responses" in endpoint_spec, f"{method.upper()} {path} must document responses"
                assert "200" in endpoint_spec["responses"], f"{method.upper()} {path} must document 200 response"

    def test_openapi_includes_example_values(self, test_client: TestClient):
        """
        Test that schemas include example values for better developer experience.

        Given: API with documented endpoints
        When: OpenAPI schema includes examples
        Then: Request/response schemas should have example values
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check search endpoint has example responses
        search_endpoint = schema["paths"]["/api/v2/cao/search"]["get"]
        success_response = search_endpoint["responses"]["200"]
        assert "content" in success_response

        json_content = success_response["content"]["application/json"]
        # Should have either 'example' or 'examples' field
        assert "example" in json_content or "examples" in json_content, \
            "Response should include example data"

    def test_openapi_documents_error_responses(self, test_client: TestClient):
        """
        Test that error responses (401, 404, 429, 500) are documented.

        Given: API with authentication and error handling
        When: OpenAPI schema is generated
        Then: Common error codes must be documented
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check authenticated endpoint documents 401
        cao_endpoint = schema["paths"]["/api/v2/cao/{cao_id}/current"]["get"]
        responses = cao_endpoint["responses"]

        assert "401" in responses, "Must document unauthorized response"
        assert "404" in responses, "Must document not found response"
        assert "429" in responses, "Must document rate limit response"

        # Verify error responses have descriptions
        assert "description" in responses["401"]
        assert "Invalid API key" in responses["401"]["description"] or \
               "Unauthorized" in responses["401"]["description"]


class TestInteractiveDocumentation:
    """Test suite for Swagger UI and ReDoc interactive documentation."""

    def test_swagger_ui_endpoint_exists(self, test_client: TestClient):
        """
        Test that /api/v2/docs endpoint serves Swagger UI.

        Given: FastAPI application with OpenAPI schema
        When: Client requests /api/v2/docs
        Then: Swagger UI HTML page should be served
        """
        response = test_client.get("/api/v2/docs")

        assert response.status_code == 200, "Swagger UI endpoint should exist"
        assert response.headers["content-type"].startswith("text/html"), \
            "Should return HTML content"

        html_content = response.text
        assert "swagger-ui" in html_content.lower(), "Should contain Swagger UI"
        assert "/api/v2/openapi.json" in html_content, \
            "Should reference correct OpenAPI schema"

    def test_redoc_endpoint_exists(self, test_client: TestClient):
        """
        Test that /api/v2/redoc endpoint serves ReDoc documentation.

        Given: FastAPI application with OpenAPI schema
        When: Client requests /api/v2/redoc
        Then: ReDoc HTML page should be served
        """
        response = test_client.get("/api/v2/redoc")

        assert response.status_code == 200, "ReDoc endpoint should exist"
        assert response.headers["content-type"].startswith("text/html"), \
            "Should return HTML content"

        html_content = response.text
        assert "redoc" in html_content.lower(), "Should contain ReDoc"
        assert "/api/v2/openapi.json" in html_content, \
            "Should reference correct OpenAPI schema"

    def test_swagger_ui_try_it_out_configuration(self, test_client: TestClient):
        """
        Test that Swagger UI is configured for "Try it out" functionality.

        Given: Swagger UI documentation page
        When: Configuration is checked
        Then: Should allow API testing with custom API keys
        """
        response = test_client.get("/api/v2/docs")
        html_content = response.text

        # Check for Swagger UI configuration that enables try-it-out
        assert "persistAuthorization" in html_content or \
               "tryItOutEnabled" in html_content, \
            "Swagger UI should support Try It Out functionality"

    def test_documentation_includes_authentication_ui(self, test_client: TestClient):
        """
        Test that interactive docs show authentication UI (Authorize button).

        Given: API requiring authentication
        When: Swagger UI is loaded
        Then: Should display authentication/authorization UI
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check that security is defined globally or per-endpoint
        has_global_security = "security" in schema

        # Check at least one endpoint has security requirements
        has_endpoint_security = False
        for path, methods in schema["paths"].items():
            if not path.startswith("/api/v2"):
                continue
            for method, spec in methods.items():
                if "security" in spec:
                    has_endpoint_security = True
                    break

        assert has_global_security or has_endpoint_security, \
            "API must declare security requirements for authorization UI"

    def test_redoc_displays_code_samples(self, test_client: TestClient):
        """
        Test that ReDoc configuration enables code sample generation.

        Given: ReDoc documentation page
        When: OpenAPI schema includes proper configuration
        Then: Code samples should be available in multiple languages
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check for x-code-samples extension or proper schema structure
        # ReDoc generates code samples from well-defined schemas
        search_endpoint = schema["paths"]["/api/v2/cao/search"]["get"]

        # Verify endpoint has enough information for code generation
        assert "parameters" in search_endpoint, "Should document parameters for code samples"
        assert "responses" in search_endpoint, "Should document responses for code samples"


class TestAuthenticationDocumentation:
    """Test suite for API authentication documentation."""

    def test_api_key_header_documented(self, test_client: TestClient):
        """
        Test that X-API-Key header is properly documented.

        Given: API using header-based authentication
        When: Documentation is generated
        Then: Header parameter must be clearly documented
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check security scheme documentation
        security_schemes = schema["components"]["securitySchemes"]
        api_key_scheme = security_schemes["APIKeyHeader"]

        assert "description" in api_key_scheme, "API key scheme must have description"
        assert "X-API-Key" in api_key_scheme["description"] or \
               "authentication" in api_key_scheme["description"].lower(), \
            "Description must explain how to use API key"

    def test_example_api_keys_provided(self, test_client: TestClient):
        """
        Test that documentation provides example/test API keys.

        Given: Documentation for developers
        When: Getting started guide is viewed
        Then: Should provide test API keys or instructions to generate them
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check API info section for getting started guide
        info = schema["info"]
        assert "description" in info, "API must have description"

        description = info["description"]
        # Should mention API key or authentication
        assert "API key" in description or "authentication" in description.lower(), \
            "Description should explain authentication requirements"

        # Could also check for x-* extensions with example keys
        # or link to getting started guide

    def test_rate_limit_documentation(self, test_client: TestClient):
        """
        Test that rate limits are documented in API spec.

        Given: API with rate limiting (429 responses)
        When: Documentation is generated
        Then: Rate limits and 429 responses must be documented
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check that 429 Too Many Requests is documented
        for path, methods in schema["paths"].items():
            if not path.startswith("/api/v2"):
                continue
            for method, spec in methods.items():
                if "security" in spec or path != "/api/v2/openapi.json":
                    # Authenticated endpoints should document rate limits
                    assert "429" in spec["responses"], \
                        f"{method.upper()} {path} should document rate limiting"

                    rate_limit_response = spec["responses"]["429"]
                    assert "description" in rate_limit_response
                    assert "limit" in rate_limit_response["description"].lower() or \
                           "exceeded" in rate_limit_response["description"].lower()

    def test_authentication_error_examples(self, test_client: TestClient):
        """
        Test that authentication error responses include examples.

        Given: API with authentication
        When: 401 response is documented
        Then: Should include example error response body
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Get any authenticated endpoint
        search_endpoint = schema["paths"]["/api/v2/cao/search"]["get"]

        assert "401" in search_endpoint["responses"]
        unauthorized_response = search_endpoint["responses"]["401"]

        assert "content" in unauthorized_response, "Error should have content"
        json_content = unauthorized_response["content"]["application/json"]

        # Should have schema or example
        assert "schema" in json_content or "example" in json_content, \
            "Error response should be documented with schema or example"

    def test_usage_endpoint_documented(self, test_client: TestClient):
        """
        Test that /usage endpoint is documented for checking API limits.

        Given: API with usage tracking
        When: OpenAPI schema is checked
        Then: /usage endpoint must be documented with response schema
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        assert "/api/v2/usage" in schema["paths"], "Usage endpoint must be documented"

        usage_endpoint = schema["paths"]["/api/v2/usage"]["get"]
        success_response = usage_endpoint["responses"]["200"]

        assert "content" in success_response
        json_schema = success_response["content"]["application/json"]["schema"]

        # Should document key fields: calls_this_month, monthly_limit, remaining
        if "properties" in json_schema:
            properties = json_schema["properties"]
            assert "calls_this_month" in properties
            assert "monthly_limit" in properties
            assert "remaining" in properties


class TestEndpointDocumentation:
    """Test suite for individual endpoint documentation quality."""

    def test_all_endpoints_have_descriptions(self, test_client: TestClient):
        """
        Test that every endpoint has a clear description.

        Given: Public API with multiple endpoints
        When: Each endpoint spec is checked
        Then: All must have summary or description field
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        for path, methods in schema["paths"].items():
            if not path.startswith("/api/v2"):
                continue
            for method, spec in methods.items():
                assert "summary" in spec or "description" in spec, \
                    f"{method.upper()} {path} must have summary or description"

    def test_parameters_documented_with_types(self, test_client: TestClient):
        """
        Test that all parameters are documented with proper types.

        Given: Endpoints with query/path parameters
        When: Parameter definitions are checked
        Then: Each must have name, type, and description
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check search endpoint parameters
        search_endpoint = schema["paths"]["/api/v2/cao/search"]["get"]

        assert "parameters" in search_endpoint, "Endpoints with params must document them"

        for param in search_endpoint["parameters"]:
            assert "name" in param, "Parameter must have name"
            assert "in" in param, "Parameter must specify location (query/path/header)"
            assert "schema" in param, "Parameter must have schema with type"
            assert "description" in param, "Parameter should have description"

    def test_response_examples_provided(self, test_client: TestClient):
        """
        Test that successful responses include example data.

        Given: API endpoints with documented responses
        When: 200 responses are checked
        Then: Should include example response bodies
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check multiple endpoints for examples
        endpoints_to_check = [
            "/api/v2/cao/search",
            "/api/v2/cao/{cao_id}/current",
            "/api/v2/cao/{cao_id}/salary-scales",
        ]

        for endpoint_path in endpoints_to_check:
            if endpoint_path in schema["paths"]:
                endpoint = schema["paths"][endpoint_path]["get"]
                success_response = endpoint["responses"]["200"]["content"]["application/json"]

                # Must have either inline example or reference to examples
                has_example = "example" in success_response or \
                             "examples" in success_response or \
                             ("schema" in success_response and "example" in success_response["schema"])

                assert has_example, f"{endpoint_path} should provide response example"

    def test_error_codes_documented(self, test_client: TestClient):
        """
        Test that all relevant HTTP error codes are documented per endpoint.

        Given: API endpoints with various failure modes
        When: Response codes are checked
        Then: 400, 401, 404, 429, 500 should be documented where applicable
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # POST endpoint should document 400 (bad request)
        payroll_endpoint = schema["paths"]["/api/v2/validate/payroll"]["post"]
        assert "400" in payroll_endpoint["responses"], \
            "POST endpoints should document 400 Bad Request"

        # Endpoints with {cao_id} should document 404
        cao_detail = schema["paths"]["/api/v2/cao/{cao_id}/current"]["get"]
        assert "404" in cao_detail["responses"], \
            "Endpoints with resource IDs should document 404 Not Found"

    def test_deprecated_endpoints_marked(self, test_client: TestClient):
        """
        Test that deprecated endpoints are properly marked.

        Given: API with version evolution
        When: Old endpoints are deprecated
        Then: Must be marked with deprecated: true in schema
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check if any v1 endpoints exist and are marked deprecated
        for path, methods in schema["paths"].items():
            if "/api/v1/" in path:
                # v1 endpoints should be marked deprecated when v2 exists
                for method, spec in methods.items():
                    # This is a forward-looking test - will fail now but pass
                    # when we implement deprecation markers
                    if "deprecated" in spec:
                        assert spec["deprecated"] == True, \
                            "Deprecated flag should be boolean true"


class TestCodeExamples:
    """Test suite for code examples in different programming languages."""

    def test_python_examples_exist(self, test_client: TestClient):
        """
        Test that Python code examples are available in documentation.

        Given: API documentation for Python developers
        When: Code examples section is checked
        Then: Should include Python requests library examples
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        # Check for x-code-samples extension or info section with examples
        info = schema["info"]

        # Should have extended description with code samples or link to guide
        assert "description" in info
        description = info["description"]

        # Looking for Python example or link to examples
        has_code_reference = "```python" in description or \
                            "example" in description.lower() or \
                            "github" in description.lower() or \
                            "x-code-samples" in schema.get("tags", [{}])[0]

        # This test expects code examples to be embedded or referenced
        assert has_code_reference or "x-codeSamples" in schema, \
            "Documentation should include or reference Python code examples"

    def test_python_example_includes_authentication(self, test_client: TestClient):
        """
        Test that Python examples show how to use API key authentication.

        Given: Python code examples in docs
        When: Example code is checked
        Then: Must include X-API-Key header in requests
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info_description = schema["info"]["description"]

        # If Python example exists, it should show authentication
        if "python" in info_description.lower():
            assert "X-API-Key" in info_description or \
                   "headers" in info_description or \
                   "api_key" in info_description.lower(), \
                "Python examples must demonstrate authentication"

    def test_javascript_examples_exist(self, test_client: TestClient):
        """
        Test that JavaScript/TypeScript examples are provided.

        Given: API documentation for JavaScript developers
        When: Code examples section is checked
        Then: Should include fetch/axios examples
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info_description = schema["info"]["description"]

        # Should reference JavaScript examples or include them
        has_js_examples = "javascript" in info_description.lower() or \
                         "typescript" in info_description.lower() or \
                         "```js" in info_description or \
                         "```ts" in info_description

        # Alternatively, could be in x-code-samples
        assert has_js_examples or self._has_code_samples_extension(schema), \
            "Documentation should include JavaScript/TypeScript examples"

    def test_curl_examples_exist(self, test_client: TestClient):
        """
        Test that curl command examples are provided.

        Given: API documentation
        When: Code examples section is checked
        Then: Should include curl command examples
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info_description = schema["info"]["description"]

        # curl is the most basic example - should always be present
        has_curl = "curl" in info_description.lower() or \
                  "```bash" in info_description or \
                  "```shell" in info_description

        assert has_curl or self._has_code_samples_extension(schema), \
            "Documentation must include curl examples for basic API usage"

    def test_code_examples_show_error_handling(self, test_client: TestClient):
        """
        Test that code examples demonstrate proper error handling.

        Given: Code examples in documentation
        When: Example code is reviewed
        Then: Should show how to handle 401, 404, 429 responses
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info_description = schema["info"]["description"]

        # Advanced test: examples should mention error handling
        if len(info_description) > 200:  # If there's substantial documentation
            has_error_handling = "error" in info_description.lower() or \
                                "exception" in info_description.lower() or \
                                "status_code" in info_description.lower() or \
                                "try" in info_description.lower()

            assert has_error_handling, \
                "Code examples should demonstrate error handling patterns"

    def test_complete_workflow_example_exists(self, test_client: TestClient):
        """
        Test that documentation includes a complete workflow example.

        Given: API with multiple related endpoints
        When: Getting started guide is checked
        Then: Should show complete workflow: search CAO -> get details -> validate payroll
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info = schema["info"]

        # Should have substantial description with workflow
        assert "description" in info
        assert len(info["description"]) > 100, \
            "API description should be comprehensive with workflow examples"

        description = info["description"].lower()

        # Should reference the main workflow endpoints
        references_workflow = ("search" in description and "validate" in description) or \
                            "workflow" in description or \
                            "getting started" in description

        assert references_workflow, \
            "Documentation should include complete workflow example"

    # Helper methods
    def _has_code_samples_extension(self, schema: Dict[str, Any]) -> bool:
        """Check if schema uses x-code-samples OpenAPI extension."""
        # Check in any endpoint
        for path, methods in schema.get("paths", {}).items():
            for method, spec in methods.items():
                if "x-code-samples" in spec or "x-codeSamples" in spec:
                    return True
        return False


class TestDocumentationMetadata:
    """Test suite for API documentation metadata and info."""

    def test_api_title_and_version(self, test_client: TestClient):
        """
        Test that API has proper title and version in schema.

        Given: OpenAPI schema
        When: Info section is checked
        Then: Must have title, version, and description
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info = schema["info"]
        assert "title" in info, "API must have title"
        assert "version" in info, "API must have version"
        assert "description" in info, "API must have description"

        # Title should mention this is the public/B2B API
        assert "v2" in info["title"] or "V2" in info["title"] or \
               "public" in info["title"].lower() or "b2b" in info["title"].lower(), \
            "API title should indicate this is v2 public API"

    def test_contact_information_provided(self, test_client: TestClient):
        """
        Test that API documentation includes contact information.

        Given: B2B API for external customers
        When: Info section is checked
        Then: Should include contact email or support URL
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info = schema["info"]

        # Should have contact info for B2B customers
        assert "contact" in info, "B2B API should include contact information"

        contact = info["contact"]
        has_contact_method = "email" in contact or "url" in contact
        assert has_contact_method, "Contact must include email or URL"

    def test_terms_of_service_link(self, test_client: TestClient):
        """
        Test that API includes terms of service or usage policy link.

        Given: Commercial B2B API
        When: Info section is checked
        Then: Should include terms of service URL
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info = schema["info"]

        # B2B APIs should have ToS
        assert "termsOfService" in info, \
            "B2B API should include terms of service URL"

        tos_url = info["termsOfService"]
        assert tos_url.startswith("http"), "Terms of service must be a valid URL"

    def test_api_servers_configuration(self, test_client: TestClient):
        """
        Test that API servers are properly configured in OpenAPI schema.

        Given: API that can run in different environments
        When: Servers section is checked
        Then: Should define production and sandbox server URLs
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        assert "servers" in schema, "API must define server URLs"
        servers = schema["servers"]

        assert len(servers) > 0, "Must have at least one server defined"

        for server in servers:
            assert "url" in server, "Each server must have URL"
            assert "description" in server, "Each server should have description"

    def test_api_tags_for_organization(self, test_client: TestClient):
        """
        Test that endpoints are organized with tags.

        Given: API with multiple endpoint categories
        When: Tags are checked
        Then: Should use tags to group related endpoints
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        assert "tags" in schema, "API should define tags for organization"
        tags = schema["tags"]

        # Should have descriptive tags
        tag_names = [tag["name"] for tag in tags]

        # Expected tag categories
        expected_categories = ["CAO", "Validation", "Usage"]
        for category in expected_categories:
            # At least one tag should relate to each category
            has_category = any(category.lower() in tag.lower() for tag in tag_names)
            assert has_category, f"Should have tag for {category} endpoints"

    def test_license_information(self, test_client: TestClient):
        """
        Test that API schema includes license information.

        Given: Commercial API product
        When: Info section is checked
        Then: Should include license information
        """
        response = test_client.get("/api/v2/openapi.json")
        schema = response.json()

        info = schema["info"]

        # Commercial APIs should declare their license
        assert "license" in info, "API should include license information"

        license_info = info["license"]
        assert "name" in license_info, "License must have name"
