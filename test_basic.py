#!/usr/bin/env python3
"""
Basic test script for Phase 0 and Phase 1.1 structure
Tests configuration loading and basic module imports
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_file_structure():
    """Test that all required files exist"""
    print("=== Testing File Structure ===")
    
    required_files = [
        'src/mf_faq/__init__.py',
        'src/mf_faq/config/__init__.py',
        'src/mf_faq/config/sources.yaml',
        'src/mf_faq/config/refusal_intents.yaml',
        'src/mf_faq/config/disclaimer.txt',
        'src/mf_faq/config/pii_patterns.yaml',
        'src/mf_faq/config/governance_rules.md',
        'src/mf_faq/ingestion/__init__.py',
        'src/mf_faq/ingestion/fetcher.py',
        'data/raw/',
        'requirements.txt'
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            existing_files.append(file_path)
            print(f"✓ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"✗ {file_path}")
    
    print(f"\nFile Structure: {len(existing_files)}/{len(required_files)} files exist")
    
    return len(missing_files) == 0


def test_config_loading():
    """Test configuration loading without dependencies"""
    print("\n=== Testing Configuration Loading ===")
    
    try:
        # Test basic YAML loading
        import yaml
        
        sources_file = Path('src/mf_faq/config/sources.yaml')
        if sources_file.exists():
            with open(sources_file, 'r') as f:
                sources = yaml.safe_load(f)
                print(f"✓ Sources loaded: {len(sources.get('schemes', []))} schemes")
                
                # Check for required URLs
                urls = []
                for scheme in sources.get('schemes', []):
                    for source in scheme.get('sources', []):
                        url = source.get('url')
                        if url:
                            urls.append(url)
                
                expected_urls = [
                    'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
                    'https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth',
                    'https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth',
                    'https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth',
                    'https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth'
                ]
                
                if set(urls) == set(expected_urls):
                    print("✓ All required HDFC URLs present")
                    return True
                else:
                    print("✗ Missing or incorrect URLs in sources")
                    return False
        else:
            print("✗ Sources file not found")
            return False
            
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


def test_disclaimer():
    """Test disclaimer loading"""
    print("\n=== Testing Disclaimer ===")
    
    try:
        disclaimer_file = Path('src/mf_faq/config/disclaimer.txt')
        if disclaimer_file.exists():
            with open(disclaimer_file, 'r') as f:
                disclaimer = f.read().strip()
                print(f"✓ Disclaimer loaded: '{disclaimer}'")
                return disclaimer == "Facts-only. No investment advice."
        else:
            print("✗ Disclaimer file not found")
            return False
    except Exception as e:
        print(f"✗ Disclaimer test failed: {e}")
        return False


def test_pii_patterns():
    """Test PII patterns loading"""
    print("\n=== Testing PII Patterns ===")
    
    try:
        import yaml
        
        pii_file = Path('src/mf_faq/config/pii_patterns.yaml')
        if pii_file.exists():
            with open(pii_file, 'r') as f:
                pii_config = yaml.safe_load(f)
                
                patterns = pii_config.get('pan_patterns', [])
                print(f"✓ PAN patterns: {len(patterns)}")
                
                patterns = pii_config.get('aadhaar_patterns', [])
                print(f"✓ Aadhaar patterns: {len(patterns)}")
                
                patterns = pii_config.get('email_patterns', [])
                print(f"✓ Email patterns: {len(patterns)}")
                
                return len(pii_config.get('pan_patterns', [])) > 0
        else:
            print("✗ PII patterns file not found")
            return False
    except Exception as e:
        print(f"✗ PII patterns test failed: {e}")
        return False


def test_refusal_intents():
    """Test refusal intents loading"""
    print("\n=== Testing Refusal Intents ===")
    
    try:
        import yaml
        
        intents_file = Path('src/mf_faq/config/refusal_intents.yaml')
        if intents_file.exists():
            with open(intents_file, 'r') as f:
                intents = yaml.safe_load(f)
                
                intent_types = intents.get('intents', {}).keys()
                print(f"✓ Intent types: {list(intent_types)}")
                
                # Check for required intents
                required_intents = ['advisory', 'comparison', 'prediction']
                missing_intents = [intent for intent in required_intents if intent not in intent_types]
                
                if not missing_intents:
                    print("✓ All required refusal intents present")
                    return True
                else:
                    print(f"✗ Missing intents: {missing_intents}")
                    return False
        else:
            print("✗ Refusal intents file not found")
            return False
    except Exception as e:
        print(f"✗ Refusal intents test failed: {e}")
        return False


def main():
    """Run all basic tests"""
    print("=== Phase 0 & Phase 1.1 Basic Tests ===\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Configuration Loading", test_config_loading),
        ("Disclaimer", test_disclaimer),
        ("PII Patterns", test_pii_patterns),
        ("Refusal Intents", test_refusal_intents)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed! Phase 0 & Phase 1.1 structure is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
