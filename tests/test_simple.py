#!/usr/bin/env python3
"""Simple test script to verify CAO search functionality."""

import requests
import json

BASE_URL = "http://localhost:8000/api/v2/search/cao"

def test_search(search_type, query, expected_count=None):
    """Test a search and print results."""
    print(f"\n{'='*60}")
    print(f"Testing {search_type}: '{query}'")
    print(f"{'='*60}")

    response = requests.get(f"{BASE_URL}?{search_type}={query}")
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Results found: {data['total']}")

    if data['total'] > 0:
        for result in data['results']:
            print(f"\n✓ {result['name']}")
            print(f"  Company: {result.get('company', 'N/A')}")
            print(f"  Sector: {result['sector']}")
            print(f"  Match: {result['match_score']:.1f}% ({result['match_type']})")
            print(f"  Compliance: {result['coverage_score']}%")
    else:
        print("\n✗ No results found")
        if data.get('suggestions'):
            print("\nSuggestions:")
            for suggestion in data['suggestions']:
                print(f"  • {suggestion}")

    if expected_count is not None:
        assert data['total'] >= expected_count, f"Expected at least {expected_count} results, got {data['total']}"
        print(f"\n✅ Test passed: Found {data['total']} results (expected >= {expected_count})")

    return data['total'] > 0

def main():
    """Run all test scenarios."""
    print("\n" + "="*60)
    print("CAO SEARCH FUNCTIONALITY TESTS")
    print("="*60)

    # Test company searches
    print("\n### COMPANY SEARCHES ###")
    test_search("company", "NAM", expected_count=1)
    test_search("company", "Shell", expected_count=1)
    test_search("company", "ING", expected_count=1)
    test_search("company", "Albert Heijn", expected_count=1)
    test_search("company", "IKEA", expected_count=1)
    test_search("company", "Achmea", expected_count=1)

    # Test sector searches
    print("\n### SECTOR SEARCHES ###")
    test_search("sector", "Energie", expected_count=2)  # Should find NAM and Shell
    test_search("sector", "metaal", expected_count=1)   # Should find Metalektro
    test_search("sector", "handel", expected_count=2)   # Should find Detailhandel and Groothandel
    test_search("sector", "horeca", expected_count=1)
    test_search("sector", "bouw", expected_count=1)

    # Test partial matches
    print("\n### PARTIAL MATCHES ###")
    test_search("company", "nam")      # Should find NAM
    test_search("company", "ing")      # Should find ING
    test_search("company", "albert")   # Should find Albert Heijn
    test_search("sector", "fin")       # Should find Financiële dienstverlening

    # Test KVK search
    print("\n### KVK SEARCHES ###")
    test_search("kvk", "12345678", expected_count=1)  # Mock KVK for Achmea

    # Test no results
    print("\n### NO RESULTS TEST ###")
    test_search("company", "NonExistentCompany")
    test_search("sector", "NonExistentSector")

    print("\n" + "="*60)
    print("ALL TESTS COMPLETED SUCCESSFULLY! ✅")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
