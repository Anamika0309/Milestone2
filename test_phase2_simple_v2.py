#!/usr/bin/env python3
"""
Simple Phase 2 Test - Minimal Dependencies
Tests core Phase 2 functionality without heavy dependencies
"""

import sys
import os
sys.path.insert(0, 'src')

def test_phase2_simple():
    """Simple test of Phase 2 components"""
    print("Testing Phase 2 Components (Simple)")
    print("=" * 50)
    
    # Test 1: Query Normalizer
    print("1. Testing Query Normalizer...")
    try:
        from mf_faq.retrieval.query_normalizer import QueryNormalizer
        normalizer = QueryNormalizer()
        result = normalizer.normalize_query("What is expense ratio?")
        print(f"   Normalized: '{result}'")
        print("   ✅ Query Normalizer working")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Scheme Resolver
    print("2. Testing Scheme Resolver...")
    try:
        from mf_faq.retrieval.scheme_resolver import SchemeResolver
        resolver = SchemeResolver()
        schemes = resolver.resolve_schemes("HDFC Equity Fund")
        print(f"   Found {len(schemes)} schemes")
        print("   ✅ Scheme Resolver working")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Hybrid Retriever (without ChromaDB)
    print("3. Testing Hybrid Retriever...")
    try:
        from mf_faq.retrieval.hybrid_retriever import HybridRetriever
        retriever = HybridRetriever()
        
        # Test query type detection
        query_type = retriever.detect_query_type("expense ratio")
        print(f"   Query type: {query_type}")
        
        # Test query embedding generation
        embedding = retriever.generate_query_embedding("test query")
        print(f"   Embedding dimension: {len(embedding)}")
        
        print("   ✅ Hybrid Retriever working")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 4: Confidence Gate
    print("4. Testing Confidence Gate...")
    try:
        from mf_faq.retrieval.confidence_gate import ConfidenceGate
        gate = ConfidenceGate()
        
        # Test with mock results
        mock_results = [
            {'text': 'Test result 1', 'confidence': 0.8},
            {'text': 'Test result 2', 'confidence': 0.6}
        ]
        
        filtered = gate.filter_results(mock_results)
        print(f"   Filtered to {len(filtered)} results")
        print("   ✅ Confidence Gate working")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("=" * 50)
    print("Phase 2 Simple Test Complete!")
    return True

def main():
    """Main test function"""
    success = test_phase2_simple()
    if success:
        print("\n🎉 Phase 2 components working!")
        return 0
    else:
        print("\n❌ Phase 2 test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
