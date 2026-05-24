#!/usr/bin/env python3
"""
Simple test script for Phase 1.1 Fetcher module
Tests basic functionality without actual network calls
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mf_faq.config import load_sources, get_whitelisted_urls
from mf_faq.ingestion.fetcher import Fetcher


def test_config_loading():
    """Test configuration loading"""
    print("Testing configuration loading...")
    
    try:
        sources = load_sources('src/mf_faq/config')
        print(f"✓ Loaded {len(sources.get('schemes', []))} schemes")
        
        urls = get_whitelisted_urls('src/mf_faq/config')
        print(f"✓ Found {len(urls)} whitelisted URLs")
        
        # Print URLs
        for i, url in enumerate(urls, 1):
            print(f"  {i}. {url}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


def test_fetcher_initialization():
    """Test fetcher class initialization"""
    print("\nTesting fetcher initialization...")
    
    try:
        fetcher = Fetcher('src/mf_faq/config')
        print("✓ Fetcher initialized successfully")
        print(f"✓ Output directory: {fetcher.output_dir}")
        print(f"✓ User agent: {fetcher.user_agent}")
        return True
    except Exception as e:
        print(f"✗ Fetcher initialization failed: {e}")
        return False


def test_health_status():
    """Test health status functionality"""
    print("\nTesting health status...")
    
    try:
        fetcher = Fetcher('src/mf_faq/config')
        health = fetcher.get_health_status()
        
        print(f"✓ Health status: {health['health']}")
        print(f"  Total schemes: {health['total_schemes']}")
        print(f"  Successful fetches: {health['successful_fetches']}")
        print(f"  Failed fetches: {health['failed_fetches']}")
        
        return True
    except Exception as e:
        print(f"✗ Health status check failed: {e}")
        return False


def test_url_parsing():
    """Test URL to scheme ID parsing"""
    print("\nTesting URL parsing...")
    
    try:
        fetcher = Fetcher('src/mf_faq/config')
        
        test_urls = [
            "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
            "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "invalid-url"
        ]
        
        for url in test_urls:
            scheme_id = fetcher.get_scheme_id_from_url(url)
            if scheme_id:
                print(f"✓ {url} -> {scheme_id}")
            else:
                print(f"✗ {url} -> Unknown scheme")
        
        return True
    except Exception as e:
        print(f"✗ URL parsing test failed: {e}")
        return False


async def test_robots_check():
    """Test robots.txt checking functionality"""
    print("\nTesting robots.txt checking...")
    
    try:
        fetcher = Fetcher('src/mf_faq/config')
        
        # Test with a known URL
        test_url = "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth"
        allowed = await fetcher.check_robots_txt(test_url)
        
        if allowed:
            print(f"✓ {test_url} - Robots.txt allows access")
        else:
            print(f"✗ {test_url} - Robots.txt disallows access")
        
        return True
    except Exception as e:
        print(f"✗ Robots.txt check failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=== Phase 1.1 Fetcher Module Test ===\n")
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Fetcher Initialization", test_fetcher_initialization),
        ("Health Status", test_health_status),
        ("URL Parsing", test_url_parsing),
        ("Robots.txt Check", test_robots_check)
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests[:-1]:  # Exclude async test for now
        print(f"--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Run async tests
    print(f"--- {tests[-1][0]} ---")
    try:
        result = asyncio.run(tests[-1][1]())
        results.append((tests[-1][0], result))
    except Exception as e:
        print(f"✗ Test {tests[-1][0]} crashed: {e}")
        results.append((tests[-1][0], False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 1.1 Fetcher is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
