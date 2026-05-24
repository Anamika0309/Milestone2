#!/usr/bin/env python3
"""
Test ChromaDB Integration
Tests vector database functionality
"""

import sys
import os
sys.path.insert(0, 'src')

from mf_faq.vector_db.chroma_store import ChromaVectorStore
from mf_faq.ingestion.embedder import Embedder

def test_chromadb():
    """Test ChromaDB functionality"""
    print("Testing ChromaDB Integration")
    print("=" * 50)
    
    # Test 1: Initialize ChromaDB
    print("1. Testing ChromaDB initialization...")
    try:
        vector_store = ChromaVectorStore()
        health = vector_store.get_health_status()
        print(f"   Health: {health}")
        print("   ✅ ChromaDB initialized successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Add test embeddings
    print("2. Testing embedding storage...")
    try:
        test_chunks = [
            {
                'chunk_id': 'test-1',
                'text': 'HDFC Equity Fund expense ratio is 1.02%',
                'scheme_id': 'hdfc_equity',
                'section': 'Expense Ratio',
                'embedding': [0.1] * 384,  # Mock 384-dim embedding
                'token_count': 10
            },
            {
                'chunk_id': 'test-2', 
                'text': 'Exit load is 0% if redeemed after 1 year',
                'scheme_id': 'hdfc_equity',
                'section': 'Exit Load',
                'embedding': [0.2] * 384,  # Mock 384-dim embedding
                'token_count': 8
            }
        ]
        
        success = vector_store.add_embeddings(test_chunks)
        if success:
            print("   ✅ Test embeddings added successfully")
        else:
            print("   ❌ Failed to add test embeddings")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Query embeddings
    print("3. Testing embedding query...")
    try:
        query_embedding = [0.15] * 384  # Mock query embedding
        results = vector_store.query_embeddings(query_embedding, 5)
        
        print(f"   Retrieved {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['chunk_id']}: {result['distance']:.3f}")
        
        print("   ✅ Query test successful")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 4: Get collection stats
    print("4. Testing collection stats...")
    try:
        stats = vector_store.get_collection_stats()
        print(f"   Stats: {stats}")
        print("   ✅ Stats test successful")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 5: Test with embedder integration
    print("5. Testing embedder integration...")
    try:
        embedder = Embedder()
        
        # Load test chunks
        test_chunks_file = 'data/processed/test_chunks.json'
        if os.path.exists(test_chunks_file):
            import json
            with open(test_chunks_file, 'r') as f:
                test_chunks = json.load(f)
            
            # Test embedder with ChromaDB
            success = embedder.embed_and_save(test_chunks)
            if success:
                print("   ✅ Embedder integration successful")
            else:
                print("   ❌ Embedder integration failed")
        else:
            print("   ⚠️  Test chunks file not found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("=" * 50)
    print("ChromaDB Integration Test Complete!")
    return True

def main():
    """Main test function"""
    success = test_chromadb()
    if success:
        print("\n🎉 All ChromaDB tests passed!")
        return 0
    else:
        print("\n❌ Some ChromaDB tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
