# API Authentication & Rate Limiting Test Strategy

## Overview

This document describes the TDD test strategy for the CAO Intelligence Engine's B2B API authentication and rate limiting system.

**Current Status**: RED PHASE ✅
- Tests written FIRST before implementation
- Tests are failing as expected
- Ready for GREEN phase (implementation)

## Test Files Created

### 1. `/tests/test_api_authentication.py` (27 tests)

Comprehensive tests for API key authentication covering:

#### Header Validation (3 tests)
- ✅ Missing X-API-Key header returns 401
- ✅ Empty X-API-Key header returns 401
- ✅ Whitespace-only X-API-Key returns 401

#### Invalid Keys (3 tests)
- ✅ Invalid key format returns 401
- ✅ Nonexistent key returns 401
- ✅ SQL injection attempts are safely rejected

#### Activation Status (2 tests)
- ⚠️ Inactive API keys return 401 (FAILING - needs implementation)
- ✅ Reactivated keys work correctly

#### Key Verification (4 tests)
- ✅ Hash verification succeeds with correct key
- ✅ Hash verification fails with wrong key
- ✅ Hash verification fails with modified key
- ✅ Key prefix extraction works correctly

#### Customer Association (3 tests)
- ✅ API keys have customer_id
- ✅ Multiple keys can belong to same customer
- ✅ Key names/descriptions are stored

#### Scopes/Permissions (3 tests)
- ✅ Default scopes assigned to new keys
- ✅ Keys with read:cao scope can access CAO endpoints
- ✅ Keys with validate:payroll scope can access validation endpoints

#### Timestamps (3 tests)
- ✅ New keys have created_at timestamp
- ✅ New keys have no last_used timestamp
- ✅ last_used timestamp updates on request

#### Security Features (4 tests)
- ✅ Raw key is never stored (only hash)
- ✅ SHA256 hashing is used
- ✅ Keys start with 'cao_' prefix
- ✅ Keys are cryptographically unique

#### Usage Endpoint (2 tests)
- ⚠️ /api/v2/usage returns usage stats (FAILING - off by one)
- ⚠️ /api/v2/usage without key returns 401 (FAILING - returns 422)

**Results**: 23 PASSED, 4 FAILED (as expected in RED phase)

### 2. `/tests/test_api_rate_limiting.py` (29 tests)

Comprehensive tests for rate limiting covering:

#### Monthly Rate Limits (5 tests)
- ✅ New keys have default limit of 50,000
- ✅ New keys start with zero calls
- ✅ Custom monthly limits can be set
- ✅ Starter plan has lower limit (10,000)
- ✅ Enterprise plan has higher limit (1,000,000)

#### Call Counter Incrementation (4 tests)
- ✅ Successful requests increment counter
- ✅ Multiple requests increment correctly
- ✅ Failed authentication doesn't increment
- ✅ 404 requests still increment (authenticated)

#### Rate Limit Exceeded (4 tests)
- ✅ Exceeding limit returns 429
- ✅ At limit-1 succeeds (last allowed call)
- ✅ At exact limit returns 429
- ✅ Way over limit returns 429

#### can_make_request() Method (4 tests)
- ✅ Active key under limit can make request
- ✅ Active key at limit cannot make request
- ✅ Inactive key cannot make request
- ✅ Inactive key under limit still cannot make request

#### Rate Limit Remaining (4 tests)
- ✅ Remaining calls calculated correctly
- ⚠️ Usage endpoint returns remaining (FAILING - off by one)
- ✅ Remaining is zero when at limit
- ✅ Remaining is negative when over limit

#### Rate Limit Headers (2 tests)
- ⚠️ Successful requests include rate limit headers (FAILING - not implemented)
- ⚠️ 429 responses include Retry-After header (FAILING - not implemented)

#### Monthly Reset (1 test)
- ✅ Counter resets at start of new month (specification test)

#### Shared Limits (1 test)
- ✅ Different endpoints count toward same limit

#### Burst Protection (2 tests)
- ✅ Rapid sequential requests all count
- ✅ Requests stop when limit reached during burst

#### Edge Cases (2 tests)
- ✅ Zero limit prevents all requests
- ✅ Very high limit acts as unlimited

**Results**: 26 PASSED, 3 FAILED (as expected in RED phase)

## Key Failures (Expected in RED Phase)

### Authentication Failures
1. **Missing API key returns 422 instead of 401**
   - FastAPI validation returns 422 for missing required header
   - Need to customize error handling

2. **Inactive key detection**
   - Current implementation doesn't check `is_active` flag
   - Returns 429 instead of 401

3. **Usage endpoint counter off-by-one**
   - /api/v2/usage increments counter when called
   - Test expects 3800 remaining, gets 3799
   - This is correct behavior (usage call counts), test may need adjustment

### Rate Limiting Failures
1. **Missing rate limit headers**
   - X-RateLimit-Limit, X-RateLimit-Remaining not in responses
   - Need to implement custom middleware or response headers

2. **Missing Retry-After header**
   - 429 responses don't include when to retry
   - Should include seconds until monthly reset

## Test Coverage

### What IS Tested
- ✅ API key creation and uniqueness
- ✅ Hash-based verification (SHA256)
- ✅ Customer association
- ✅ Monthly rate limits (default and custom)
- ✅ Call counter incrementation
- ✅ Rate limit enforcement (429 responses)
- ✅ Active/inactive status checking
- ✅ Scopes/permissions
- ✅ Timestamp tracking (created_at, last_used)
- ✅ Security (no raw key storage, crypto uniqueness)
- ✅ Edge cases (zero limit, unlimited, burst)

### What is NOT Tested (Future Work)
- ❌ Database persistence (currently in-memory)
- ❌ Concurrent request handling
- ❌ Rate limit reset cron job/mechanism
- ❌ API key rotation/revocation
- ❌ Customer plan upgrades affecting limits
- ❌ Webhook notifications on rate limit approach
- ❌ Different rate limits per endpoint
- ❌ IP-based rate limiting
- ❌ OAuth2/JWT token integration

## Implementation Checklist (GREEN Phase)

To make these tests pass, implement:

### Priority 1: Core Authentication
- [ ] Customize FastAPI validation to return 401 for missing API keys
- [ ] Add check for `is_active` flag in `verify_api_key()`
- [ ] Return proper error messages in 401 responses

### Priority 2: Rate Limit Headers
- [ ] Add middleware to inject rate limit headers
- [ ] Include X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- [ ] Add Retry-After header to 429 responses

### Priority 3: Database Backend
- [ ] Replace in-memory API_KEYS_STORE with PostgreSQL
- [ ] Create `api_keys` table schema
- [ ] Create `customers` table schema
- [ ] Implement async database queries

### Priority 4: Monthly Reset
- [ ] Add `last_reset_date` field to APIKey model
- [ ] Implement automatic reset on first-use-of-new-month
- [ ] OR: Implement cron job for monthly reset

### Priority 5: Additional Features
- [ ] API key creation endpoint (admin only)
- [ ] API key deletion/revocation endpoint
- [ ] Customer management endpoints
- [ ] Plan upgrade/downgrade logic

## Running the Tests

```bash
# Run all authentication tests
pytest tests/test_api_authentication.py -v

# Run all rate limiting tests
pytest tests/test_api_rate_limiting.py -v

# Run both test suites
pytest tests/test_api_authentication.py tests/test_api_rate_limiting.py -v

# Run with coverage
pytest tests/test_api_authentication.py tests/test_api_rate_limiting.py --cov=cao_engine.api.v2 --cov-report=html
```

## Test Results Summary

```
Authentication Tests: 23 PASSED, 4 FAILED (85% pass rate)
Rate Limiting Tests:  26 PASSED, 3 FAILED (90% pass rate)
Total:                49 PASSED, 7 FAILED (87% pass rate)
```

**Status**: Ready for GREEN phase implementation! 🚀

## Notes

- Tests use FastAPI's TestClient for integration testing
- Tests mock the in-memory API_KEYS_STORE for isolation
- Tests use temp_data_dir fixture for filesystem isolation
- All tests are deterministic and can run in any order
- Tests follow Given-When-Then documentation style
- Test names clearly describe expected behavior

## Next Steps

1. **Review tests with team** - Ensure coverage matches requirements
2. **Prioritize implementation** - Start with Priority 1 items
3. **Implement features** - Make tests GREEN one by one
4. **Refactor** - Once all tests pass, optimize code
5. **Add more tests** - Cover edge cases discovered during implementation
6. **Document API** - Update OpenAPI/Swagger docs with auth requirements
