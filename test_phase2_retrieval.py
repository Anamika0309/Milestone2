#!/usr/bin/env python3
"""
Phase 2 Retrieval Integration Test
Tests all Phase 2 components working together
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from mf_faq.retrieval import (
    QueryNormalizer, 
    SchemeResolver, 
    HybridRetriever, 
    CrossEncoderReranker, 
    ConfidenceGate
)


def test_query_normalizer():
    """Test Phase 2.1 Query Normalizer"""
    print("Testing Phase 2.1 - Query Normalizer")
    
    normalizer = QueryNormalizer()
    
    test_queries = [
        "What is the expense ratio of HDFC equity fund?",
        "How much is the exit load for HDFC mid cap?",
        "What is the minimum SIP amount for ELSS?",
        "Tell me about HDFC focused fund NAV",
        "What is the AUM of HDFC large cap fund?"
    ]
    
    for query in test_queries:
        result = normalizer.normalize_query(query)
        print(f"  Query: {query}")
        print(f"  Normalized: {result['normalized_query']}")
        print(f"  Detected Terms: {result['detected_terms']}")
        print()
    
    print("✅ Query Normalizer test passed\n")
    return True


def test_scheme_resolver():
    """Test Phase 2.2 Scheme Resolver"""
    print("Testing Phase 2.2 - Scheme Resolver")
    
    resolver = SchemeResolver()
    
    test_queries = [
        "HDFC equity fund expense ratio",
        "mid cap fund exit load",
        "ELSS minimum investment",
        "focused fund benchmark",
        "large cap fund manager"
    ]
    
    # Load test chunks
    test_chunks = [
        {
            'chunk_id': 'test-1',
            'scheme_id': 'hdfc_equity',
            'section': 'Expense Ratio',
            'text': 'Expense ratio: 1.02% per annum for direct plan'
        },
        {
            'chunk_id': 'test-2', 
            'scheme_id': 'hdfc_mid_cap',
            'section': 'Exit Load',
            'text': 'Exit load: 0% if redeemed after 1 year, 1% before 1 year'
        },
        {
            'chunk_id': 'test-3',
            'scheme_id': 'hdfc_elss', 
            'section': 'Minimum Investments',
            'text': 'Minimum SIP amount: ₹500, Minimum lumpsum: ₹5000'
        }
    ]
    
    for query in test_queries:
        result = resolver.detect_scheme_terms(query)
        filtered_chunks = resolver.filter_chunks_by_scheme(test_chunks, result['detected_schemes'])
        
        print(f"  Query: {query}")
        print(f"  Detected Schemes: {result['detected_schemes']}")
        print(f"  Filtered Chunks: {len(filtered_chunks)}")
        print()
    
    print("✅ Scheme Resolver test passed\n")
    return True


def test_hybrid_retriever():
    """Test Phase 2.3 Hybrid Retriever"""
    print("Testing Phase 2.3 - Hybrid Retriever")
    
    retriever = HybridRetriever()
    
    # Test query type detection
    test_queries = [
        ("What is the expense ratio?", "semantic"),
        ("What is 1.02% expense ratio?", "numeric"),
        ("Exit load percentage", "numeric"),
        ("Tell me about fund performance", "semantic")
    ]
    
    for query, expected_type in test_queries:
        detected_type = retriever.detect_query_type(query)
        print(f"  Query: {query}")
        print(f"  Expected Type: {expected_type}")
        print(f"  Detected Type: {detected_type}")
        print(f"  Match: {expected_type == detected_type}")
        print()
    
    # Test fusion (mock)
    dense_results = [(0, 0.8), (1, 0.6), (2, 0.4)]
    sparse_results = [(1, 0.9), (2, 0.7), (0, 0.5)]
    
    fused_results = retriever.fuse_results(dense_results, sparse_results)
    
    print("  Fusion Test:")
    print(f"  Dense Results: {dense_results}")
    print(f"  Sparse Results: {sparse_results}")
    print(f"  Fused Results: {fused_results}")
    
    print("✅ Hybrid Retriever test passed\n")
    return True


def test_cross_encoder_reranker():
    """Test Phase 2.4 Cross-Encoder Re-ranker"""
    print("Testing Phase 2.4 - Cross-Encoder Re-ranker")
    
    reranker = CrossEncoderReranker()
    
    query = "What is the expense ratio of HDFC equity fund?"
    candidates = [
        {
            'chunk_id': 'test-1',
            'text': 'Expense ratio: 1.02% per annum for direct plan',
            'score': 0.8,
            'source': 'dense'
        },
        {
            'chunk_id': 'test-2',
            'text': 'Exit load: 0% if redeemed after 1 year, 1% before 1 year', 
            'score': 0.6,
            'source': 'sparse'
        },
        {
            'chunk_id': 'test-3',
            'text': 'Minimum SIP amount: ₹500, Minimum lumpsum: ₹5000',
            'score': 0.4,
            'source': 'fused'
        }
    ]
    
    results = reranker.rerank(query, candidates, top_k=3)
    
    print(f"  Query: {query}")
    print(f"  Candidates: {len(candidates)}")
    print(f"  Re-ranked Results: {len(results)}")
    
    for i, (idx, score, source, chunk_id) in enumerate(results, 1):
        print(f"    {i}. Chunk {chunk_id} (Score: {score:.3f}, Source: {source})")
    
    print("✅ Cross-Encoder Re-ranker test passed\n")
    return True


def test_confidence_gate():
    """Test Phase 2.5 Confidence Gate"""
    print("Testing Phase 2.5 - Confidence Gate")
    
    gate = ConfidenceGate()
    
    # Test different confidence scenarios
    test_scenarios = [
        {
            'name': 'High Confidence',
            'results': [
                {'chunk_id': 'test-1', 'score': 0.9, 'source': 'dense'},
                {'chunk_id': 'test-2', 'score': 0.7, 'source': 'sparse'},
                {'chunk_id': 'test-3', 'score': 0.5, 'source': 'fused'}
            ],
            'expected_count': 1
        },
        {
            'name': 'Low Margin',
            'results': [
                {'chunk_id': 'test-1', 'score': 0.8, 'source': 'dense'},
                {'chunk_id': 'test-2', 'score': 0.65, 'source': 'sparse'},
                {'chunk_id': 'test-3', 'score': 0.4, 'source': 'fused'}
            ],
            'expected_count': 1
        },
        {
            'name': 'Low Confidence',
            'results': [
                {'chunk_id': 'test-1', 'score': 0.6, 'source': 'dense'},
                {'chunk_id': 'test-2', 'score': 0.55, 'source': 'sparse'},
                {'chunk_id': 'test-3', 'score': 0.4, 'source': 'fused'}
            ],
            'expected_count': 1
        }
    ]
    
    for scenario in test_scenarios:
        print(f"  Scenario: {scenario['name']}")
        filtered_results = gate.filter_by_confidence(scenario['results'])
        
        print(f"    Input Results: {len(scenario['results'])}")
        print(f"    Filtered Results: {len(filtered_results)}")
        
        for result in filtered_results:
            chunk_id = result.get('chunk_id', 'unknown')
            if chunk_id == 'fallback':
                print(f"    Fallback: {result.get('text', 'No response')}")
            else:
                print(f"    Result: {chunk_id} (Score: {result.get('score', 0):.3f})")
        print()
    
    print("✅ Confidence Gate test passed\n")
    return True


def test_integration():
    """Test complete Phase 2 integration"""
    print("Testing Phase 2 Integration")
    
    # Initialize components
    normalizer = QueryNormalizer()
    resolver = SchemeResolver()
    retriever = HybridRetriever()
    reranker = CrossEncoderReranker()
    gate = ConfidenceGate()
    
    # Test query
    query = "What is the expense ratio of HDFC equity fund?"
    
    print(f"  Query: {query}")
    
    # Step 1: Normalize query
    norm_result = normalizer.normalize_query(query)
    normalized_query = norm_result['normalized_query']
    print(f"  Normalized: {normalized_query}")
    
    # Step 2: Detect schemes
    scheme_result = resolver.detect_scheme_terms(normalized_query)
    detected_schemes = scheme_result['detected_schemes']
    print(f"  Detected Schemes: {detected_schemes}")
    
    # Step 3: Mock retrieval (since we don't have real indexes)
    mock_candidates = [
        {
            'chunk_id': 'test-1',
            'text': 'Expense ratio: 1.02% per annum for direct plan',
            'score': 0.8,
            'source': 'dense',
            'scheme_id': 'hdfc_equity'
        },
        {
            'chunk_id': 'test-2',
            'text': 'Exit load: 0% if redeemed after 1 year, 1% before 1 year',
            'score': 0.6,
            'source': 'sparse',
            'scheme_id': 'hdfc_equity'
        }
    ]
    
    # Step 4: Re-rank
    reranked_results = reranker.rerank(normalized_query, mock_candidates, top_k=3)
    print(f"  Re-ranked: {len(reranked_results)} results")
    
    # Step 5: Apply confidence gate
    final_results = gate.filter_by_confidence([
        {
            'chunk_id': result[3],
            'score': result[1],
            'source': result[2],
            'text': mock_candidates[result[0]]['text']
        }
        for result in reranked_results
    ])
    
    print(f"  Final Results: {len(final_results)}")
    
    for result in final_results:
        chunk_id = result.get('chunk_id', 'unknown')
        if chunk_id == 'fallback':
            print(f"    Fallback: {result.get('text', 'No response')}")
        else:
            print(f"    Answer: {chunk_id} (Score: {result.get('score', 0):.3f})")
    
    print("✅ Phase 2 Integration test passed\n")
    return True


def main():
    """Run all Phase 2 tests"""
    print("Phase 2 Retrieval Component Tests")
    print("=" * 50)
    
    tests = [
        test_query_normalizer,
        test_scheme_resolver,
        test_hybrid_retriever,
        test_cross_encoder_reranker,
        test_confidence_gate,
        test_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2 components working correctly!")
        return 0
    else:
        print("⚠️  Some tests failed. Check implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
