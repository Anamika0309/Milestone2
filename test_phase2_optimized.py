#!/usr/bin/env python3
"""
Test Optimized Phase 2 Retrieval Pipeline
Tests hybrid dense-sparse ChromaDB strategy
"""

import sys
import os
sys.path.insert(0, 'src')

from mf_faq.retrieval.query_normalizer import QueryNormalizer
from mf_faq.retrieval.scheme_resolver import SchemeResolver
from mf_faq.retrieval.hybrid_retriever import HybridRetriever
from mf_faq.retrieval.cross_encoder_reranker import CrossEncoderReranker
from mf_faq.retrieval.confidence_gate import ConfidenceGate

def test_phase2_optimized():
    """Test optimized Phase 2 retrieval pipeline"""
    print("Testing Optimized Phase 2 Retrieval Pipeline")
    print("=" * 60)
    
    # Test queries for different query types
    test_queries = [
        {
            'query': 'What is the expense ratio of HDFC Equity Fund?',
            'type': 'numeric',
            'expected_weights': {'dense': 0.4, 'sparse': 0.6}
        },
        {
            'query': 'How does the investment strategy work?',
            'type': 'semantic',
            'expected_weights': {'dense': 0.7, 'sparse': 0.3}
        },
        {
            'query': 'HDFC Equity Fund performance comparison',
            'type': 'scheme-specific',
            'expected_weights': {'dense': 0.6, 'sparse': 0.4}
        }
    ]
    
    # Initialize Phase 2 components
    print("1. Initializing Phase 2 components...")
    try:
        query_normalizer = QueryNormalizer()
        scheme_resolver = SchemeResolver()
        hybrid_retriever = HybridRetriever()
        cross_encoder = CrossEncoderReranker()
        confidence_gate = ConfidenceGate()
        
        # Load indexes
        hybrid_retriever.load_indexes()
        print("   ✅ All components initialized successfully")
    except Exception as e:
        print(f"   ❌ Error initializing components: {e}")
        return False
    
    # Test each query type
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{i+1}. Testing {test_case['type']} query: '{test_case['query']}'")
        
        try:
            # Step 1: Query Normalization
            normalized_query = query_normalizer.normalize_query(test_case['query'])
            print(f"   Normalized: '{normalized_query}'")
            
            # Step 2: Scheme Resolution
            scheme_results = scheme_resolver.resolve_schemes(normalized_query)
            print(f"   Schemes found: {len(scheme_results)}")
            
            # Step 3: Hybrid Retrieval with adaptive weights
            original_weights = hybrid_retriever.fusion_weights.copy()
            retrieval_results = hybrid_retriever.retrieve(normalized_query)
            final_weights = hybrid_retriever.fusion_weights
            
            print(f"   Fusion weights: {final_weights}")
            print(f"   Expected weights: {test_case['expected_weights']}")
            
            # Check if weights were adjusted correctly
            if final_weights == test_case['expected_weights']:
                print("   ✅ Adaptive weights working correctly")
            else:
                print("   ⚠️  Weights not adjusted as expected")
            
            print(f"   Retrieved {len(retrieval_results)} results")
            
            # Step 4: Cross-Encoder Re-ranking
            if retrieval_results:
                reranked_results = cross_encoder.rerank(normalized_query, retrieval_results)
                print(f"   Re-ranked to {len(reranked_results)} results")
                
                # Step 5: Confidence Gate
                gated_results = confidence_gate.filter_results(reranked_results)
                print(f"   Confidence gated to {len(gated_results)} results")
                
                if gated_results:
                    top_result = gated_results[0]
                    print(f"   Top result confidence: {top_result.get('confidence', 0):.3f}")
                    print(f"   Top result: {top_result.get('text', '')[:100]}...")
                else:
                    print("   ⚠️  No results passed confidence gate")
            else:
                print("   ⚠️  No results to re-rank")
            
        except Exception as e:
            print(f"   ❌ Error processing query: {e}")
            continue
    
    # Test ChromaDB integration
    print("\n5. Testing ChromaDB integration...")
    try:
        stats = hybrid_retriever.vector_store.get_collection_stats()
        print(f"   Collection stats: {stats}")
        
        # Test query embedding generation
        test_embedding = hybrid_retriever.generate_query_embedding("test query")
        print(f"   Query embedding dimension: {len(test_embedding)}")
        
        print("   ✅ ChromaDB integration working")
    except Exception as e:
        print(f"   ❌ ChromaDB integration error: {e}")
    
    # Test query type detection
    print("\n6. Testing query type detection...")
    query_types = [
        ("expense ratio", "numeric"),
        ("investment strategy", "semantic"),
        ("HDFC fund", "scheme-specific"),
        ("performance comparison", "semantic")
    ]
    
    for query, expected_type in query_types:
        detected_type = hybrid_retriever.detect_query_type(query)
        status = "✅" if detected_type == expected_type else "❌"
        print(f"   {status} '{query}' → {detected_type} (expected: {expected_type})")
    
    print("\n" + "=" * 60)
    print("Optimized Phase 2 Retrieval Test Complete!")
    return True

def main():
    """Main test function"""
    success = test_phase2_optimized()
    if success:
        print("\n🎉 Phase 2 optimization test completed!")
        return 0
    else:
        print("\n❌ Phase 2 optimization test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
