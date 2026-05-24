"""
Phase 2.1 - Query Normalizer (Standalone Phase Copy)
Purpose: Normalize user queries for consistent retrieval
"""

import re
import os
import unicodedata
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class QueryNormalizer:
    """Normalizes user queries for consistent retrieval"""
    
    def __init__(self, config_dir: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_dir = config_dir or os.path.join(base_dir, 'phases', 'phase_0')
        if not os.path.exists(self.config_dir):
            self.config_dir = os.path.join(base_dir, 'src', 'mf_faq', 'config')
        
        # Financial term mappings
        self.currency_map = {
            'rs.': '₹',
            'rs': '₹',
            'inr': '₹',
            'rupee': '₹',
            'percent': '%',
            'percentage': '%',
            'p.c.': '%',
            'per cent': '%',
        }
        
        # MF token mappings
        self.mf_tokens = {
            'elss': 'Equity Linked Savings Scheme',
            'sip': 'Systematic Investment Plan',
            'nav': 'Net Asset Value',
            'aum': 'Assets Under Management'
        }
        
        logger.info(f"Initialized standalone query normalizer (Config: {self.config_dir})")
    
    def normalize_text(self, text: str) -> str:
        """Apply NFKC normalization and clean text"""
        # NFKC normalization
        normalized = unicodedata.normalize('NFKC', text)
        
        # Lowercase
        normalized = normalized.lower()
        
        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Strip leading/trailing whitespace
        normalized = normalized.strip()
        
        return normalized
    
    def standardize_currency(self, text: str) -> str:
        """Standardize currency symbols to ₹"""
        for old_currency, new_currency in self.currency_map.items():
            text = text.replace(old_currency, new_currency)
        
        return text
    
    def standardize_percentages(self, text: str) -> str:
        """Standardize percentage formats"""
        text = re.sub(r'(\d+)\s*percent', r'\1%', text)
        text = re.sub(r'(\d+)\s*percentage', r'\1%', text)
        text = re.sub(r'(\d+)\s*per\s*cent', r'\1%', text)
        text = re.sub(r'(\d+)\s*p\.c\.', r'\1%', text)
        
        return text
    
    def expand_mf_tokens(self, text: str) -> str:
        """Expand mutual fund abbreviations"""
        text_lower = text.lower()
        
        for token, expansion in self.mf_tokens.items():
            # Replace whole word matches
            pattern = r'\b' + re.escape(token) + r'\b'
            text_lower = re.sub(pattern, expansion, text_lower)
        
        return text_lower
    
    def normalize_financial_terms(self, text: str) -> str:
        """Normalize financial terminology"""
        text = self.standardize_currency(text)
        text = self.standardize_percentages(text)
        text = self.expand_mf_tokens(text)
        
        return text
    
    def normalize_query(self, query: str) -> Dict[str, Any]:
        """Main normalization function"""
        try:
            logger.info(f"Normalizing query: {query}")
            
            # Apply all normalizations
            normalized = self.normalize_text(query)
            normalized = self.normalize_financial_terms(normalized)
            
            # Extract detected terms
            detected_terms = {
                'currency_symbols': bool(re.search(r'[₹%]', normalized)),
                'percentages': bool(re.search(r'\d+%', normalized)),
                'mf_tokens': any(token in normalized for token in self.mf_tokens.keys()),
                'financial_terms': bool(re.search(r'(expense|ratio|exit\s*load|nav|aum|sip|lumpsum)', normalized))
            }
            
            result = {
                'original_query': query,
                'normalized_query': normalized,
                'detected_terms': detected_terms,
                'processing_steps': [
                    'NFKC normalization',
                    'Lowercase conversion',
                    'Whitespace collapse',
                    'Currency standardization',
                    'Percentage normalization',
                    'MF token expansion',
                    'Financial term detection'
                ]
            }
            
            logger.info(f"Query normalized: {normalized}")
            return result
            
        except Exception as e:
            logger.error(f"Error normalizing query: {e}")
            return {
                'original_query': query,
                'normalized_query': query,
                'detected_terms': {},
                'processing_steps': [],
                'error': str(e)
            }


# CLI interface for standalone execution
def main():
    """CLI interface for query normalizer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Normalize user queries')
    parser.add_argument('--query', required=True, help='Query to normalize')
    parser.add_argument('--config-dir', help='Configuration directory path')
    
    args = parser.parse_args()
    
    normalizer = QueryNormalizer(args.config_dir)
    result = normalizer.normalize_query(args.query)
    
    print(f"Original Query: {result['original_query']}")
    print(f"Normalized Query: {result['normalized_query']}")
    print(f"Detected Terms: {result['detected_terms']}")
    print(f"Processing Steps: {', '.join(result['processing_steps'])}")


if __name__ == "__main__":
    main()
