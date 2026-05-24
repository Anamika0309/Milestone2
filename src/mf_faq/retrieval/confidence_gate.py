"""
Phase 2.5 - Confidence Gate
Purpose: Threshold-based filtering with fallback responses

Responsibilities:
- Threshold-based filtering
- Low margin (top - 2nd) triggers "I don't know" path
- Configurable confidence threshold τ
- Fallback to safe refusal when confidence low

Exit Criteria: Sub-second response times for typical queries
"""

import logging
import os
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ConfidenceGate:
    """Confidence gate for filtering low-confidence responses"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        
        # Default confidence threshold
        self.confidence_threshold = 0.7  # τ (tau)
        self.low_margin_threshold = 0.2  # Low margin between top-1 and top-2
        
        logger.info(f"Initialized confidence gate with threshold τ={self.confidence_threshold}")
    
    def set_confidence_threshold(self, threshold: float):
        """Set confidence threshold"""
        self.confidence_threshold = threshold
        logger.info(f"Updated confidence threshold to {threshold}")
    
    def filter_by_confidence(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter results based on confidence threshold and low margin"""
        filtered_results = []
        
        if len(results) < 2:
            # Always return if we have less than 2 results
            return results
        
        # Check if we have a clear winner
        top_score = results[0].get('score', 0.0)
        second_score = results[1].get('score', 0.0) if len(results) > 1 else 0.0
        
        # Calculate confidence margin
        if top_score > 0:
            confidence_margin = (top_score - second_score) / top_score
        else:
            confidence_margin = 0.0
        
        # Apply confidence threshold
        if top_score >= self.confidence_threshold:
            # High confidence - return top result
            filtered_results.append(results[0])
            logger.info(f"High confidence result: score={top_score:.3f}")
        elif confidence_margin > self.low_margin_threshold:
            # Low margin - return top result but with warning
            filtered_results.append(results[0])
            logger.warning(f"Low confidence margin: {confidence_margin:.3f}, returning top result")
        else:
            # Low confidence - trigger fallback
            logger.warning(f"Low confidence: top={top_score:.3f}, second={second_score:.3f}, threshold={self.confidence_threshold}")
            filtered_results.append({
                'chunk_id': 'fallback',
                'score': 0.0,
                'source': 'confidence_gate',
                'query_type': 'fallback',
                'text': "I don't have enough information to answer your question about mutual funds. Please provide more specific details or try rephrasing your question."
            })
        
        return filtered_results
        
    def filter_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Wrapper method for backward compatibility in tests"""
        return self.filter_by_confidence(results)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of confidence gate"""
        try:
            health_report = {
                'confidence_threshold': self.confidence_threshold,
                'low_margin_threshold': self.low_margin_threshold,
                'health': 'ok'
            }
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting confidence gate health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for confidence gate"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply confidence threshold to retrieval results')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--threshold', type=float, default=0.7, help='Confidence threshold τ')
    parser.add_argument('--results', help='Retrieval results JSON file')
    
    args = parser.parse_args()
    
    gate = ConfidenceGate(args.config_dir)
    
    if args.threshold:
        gate.set_confidence_threshold(args.threshold)
    
    if args.results:
        import json
        with open(args.results, 'r') as f:
            results = json.load(f)
        
        filtered_results = gate.filter_by_confidence(results)
        
        print(f"\nConfidence Gate Results:")
        print(f"Threshold: {gate.confidence_threshold}")
        print(f"Original Results: {len(results)}")
        print(f"Filtered Results: {len(filtered_results)}")
        
        for i, result in enumerate(filtered_results, 1):
            chunk_id = result.get('chunk_id', 'unknown')
            score = result.get('score', 0.0)
            source = result.get('source', 'unknown')
            
            if chunk_id == 'fallback':
                print(f"{i}. FALLBACK: {result.get('text', 'No response available')}")
            else:
                print(f"{i}. Chunk {chunk_id} (Score: {score:.3f}, Source: {source})")
    
    else:
        print("No results provided for filtering")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
