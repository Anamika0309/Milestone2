"""
Phase 2.5 - Confidence Gate (Standalone Phase Copy)
Purpose: Threshold-based filtering with fallback responses
"""

import logging
import os
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ConfidenceGate:
    """Confidence gate for filtering low-confidence responses"""
    
    def __init__(self, config_dir: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_dir = config_dir or os.path.join(base_dir, 'phases', 'phase_0')
        if not os.path.exists(self.config_dir):
            self.config_dir = os.path.join(base_dir, 'src', 'mf_faq', 'config')
        
        # Default confidence threshold τ (tau)
        self.confidence_threshold = 0.7
        self.low_margin_threshold = 0.2
        
        logger.info(f"Initialized standalone confidence gate with threshold τ={self.confidence_threshold}")
    
    def set_confidence_threshold(self, threshold: float):
        """Set confidence threshold"""
        self.confidence_threshold = threshold
        logger.info(f"Updated confidence threshold to {threshold}")
    
    def filter_by_confidence(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter results based on confidence threshold and low margin"""
        filtered_results = []
        
        if len(results) < 2:
            return results
        
        # Support both 'score' and 'confidence' keys
        top_score = results[0].get('score', results[0].get('confidence', 0.0))
        second_score = results[1].get('score', results[1].get('confidence', 0.0)) if len(results) > 1 else 0.0
        
        # Calculate confidence margin
        if top_score > 0:
            confidence_margin = (top_score - second_score) / top_score
        else:
            confidence_margin = 0.0
        
        # Apply confidence threshold
        if top_score >= self.confidence_threshold:
            filtered_results.append(results[0])
            logger.info(f"High confidence result: score={top_score:.3f}")
        elif confidence_margin > self.low_margin_threshold:
            filtered_results.append(results[0])
            logger.warning(f"Low confidence margin: {confidence_margin:.3f}, returning top result")
        else:
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
        """Alias for compatibility with different test suites"""
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
def main():
    """CLI interface for confidence gate"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Apply confidence threshold to retrieval results (Standalone)')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--threshold', type=float, default=0.7, help='Confidence threshold τ')
    parser.add_argument('--results', help='Retrieval results JSON string')
    
    args = parser.parse_args()
    
    gate = ConfidenceGate(args.config_dir)
    
    if args.threshold:
        gate.set_confidence_threshold(args.threshold)
    
    try:
        results = json.loads(args.results)
    except Exception:
        results = [
            {'chunk_id': 'c1', 'score': 0.8, 'text': 'High confidence result'},
            {'chunk_id': 'c2', 'score': 0.5, 'text': 'Lower confidence result'}
        ]
        
    filtered_results = gate.filter_results(results)
    
    print(f"\nConfidence Gate Results:")
    print(f"Threshold: {gate.confidence_threshold}")
    print(f"Original Results: {len(results)}")
    print(f"Filtered Results: {len(filtered_results)}")
    for i, r in enumerate(filtered_results, 1):
        print(f"{i}. Chunk: {r.get('chunk_id')}, Score: {r.get('score', r.get('confidence'))}")


if __name__ == "__main__":
    main()
