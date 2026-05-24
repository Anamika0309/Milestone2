#!/usr/bin/env python3
"""
Direct test of Query Normalizer
"""

import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from mf_faq.retrieval.query_normalizer import QueryNormalizer

def main():
    print("Testing Query Normalizer directly...")
    
    try:
        normalizer = QueryNormalizer()
        query = "What is the expense ratio of HDFC equity fund?"
        result = normalizer.normalize_query(query)
        
        print(f"Original Query: {result['original_query']}")
        print(f"Normalized Query: {result['normalized_query']}")
        print(f"Detected Terms: {result['detected_terms']}")
        print("✅ Query Normalizer working correctly!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
