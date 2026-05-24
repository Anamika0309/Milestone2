"""
Phase 2.2 - Scheme Resolver
Purpose: Pre-filter chunks by scheme relevance based on query terms

Responsibilities:
- Pre-filter chunks by scheme relevance based on query terms
- Boost scheme-specific results in fusion
- NER-lite for scheme name detection
- Longest substring matching against sources.yaml
- Alias support for common abbreviations

Exit Criteria: Query terms match correct scheme for ≥90% of scheme-specific queries
"""

import re
import logging
import os
from typing import Dict, List, Optional, Any, Set

from ..config.sources import load_sources


logger = logging.getLogger(__name__)


class SchemeResolver:
    """Resolves scheme relevance and filters chunks accordingly"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        self.sources = load_sources(self.config_dir)
        
        # Build scheme name mappings
        self.scheme_names = {}
        self.scheme_aliases = {}
        self.scheme_keywords = {}
        
        for scheme in self.sources.get('schemes', []):
            scheme_id = scheme.get('id')
            scheme_name = scheme.get('name')
            
            # Store full name and variations
            self.scheme_names[scheme_id] = scheme_name.lower()
            self.scheme_names[scheme_name.lower()] = scheme_id
            
            # Create aliases (first word, common abbreviations)
            name_parts = scheme_name.split()
            aliases = set()
            
            # Add full name
            aliases.add(scheme_name.lower())
            
            # Add first word variations
            if len(name_parts) > 1:
                aliases.add(name_parts[0].lower())
            
            # Add common abbreviations
            if 'equity' in scheme_name.lower():
                aliases.add('equity')
            if 'mid cap' in scheme_name.lower():
                aliases.add('midcap')
            if 'large cap' in scheme_name.lower():
                aliases.add('largecap')
            if 'focused' in scheme_name.lower():
                aliases.add('focused')
            if 'elss' in scheme_name.lower():
                aliases.add('elss')
            if 'tax saver' in scheme_name.lower():
                aliases.add('taxsaver')
            
            self.scheme_aliases[scheme_id] = aliases
            
            # Build keyword mappings
            keywords = []
            keywords.extend(scheme_name.lower().split())
            keywords.extend(list(aliases))
            
            self.scheme_keywords[scheme_id] = keywords
        
        logger.info(f"Initialized scheme resolver with {len(self.scheme_names)} schemes")
    
    def detect_scheme_terms(self, query: str) -> Dict[str, Any]:
        """Detect scheme-related terms in query"""
        query_lower = query.lower()
        detected_terms = []
        
        # Track first occurrence index of any keyword for each scheme
        scheme_first_index = {}
        
        for scheme_id, keywords in self.scheme_keywords.items():
            for keyword in keywords:
                # Exclude generic words like "hdfc", "fund", "direct", "growth"
                if keyword in ["hdfc", "fund", "direct", "growth", "-", "plan"]:
                    continue
                if keyword in query_lower:
                    idx = query_lower.find(keyword)
                    if scheme_id not in scheme_first_index or idx < scheme_first_index[scheme_id]:
                        scheme_first_index[scheme_id] = idx
                        
                    detected_terms.append({
                        'term': keyword,
                        'scheme_id': scheme_id,
                        'scheme_name': self.get_scheme_name(scheme_id)
                    })
                    
        # Sort detected schemes by their first appearance in the query
        sorted_schemes = sorted(scheme_first_index.keys(), key=lambda x: scheme_first_index[x])
        
        return {
            'detected_schemes': sorted_schemes,
            'detected_terms': detected_terms,
            'query_lower': query_lower
        }

    
    def resolve_schemes(self, query: str) -> List[str]:
        """Wrapper method for backward compatibility in tests"""
        return self.detect_scheme_terms(query).get('detected_schemes', [])
    
    def resolve(self, query: str) -> Optional[str]:
        """Resolve query to a single scheme ID, or None if not found"""
        schemes = self.resolve_schemes(query)
        return schemes[0] if schemes else None

    
    def get_scheme_name(self, scheme_id: str) -> str:
        """Get scheme name from ID"""
        for scheme in self.sources.get('schemes', []):
            if scheme.get('id') == scheme_id:
                return scheme.get('name')
        return scheme_id
    
    def get_scheme_id(self, scheme_name: str) -> str:
        """Get scheme ID from name"""
        scheme_name_lower = scheme_name.lower()
        
        for scheme_id, name in self.scheme_names.items():
            if name == scheme_name_lower:
                return scheme_id
        
        return None
    
    def filter_chunks_by_scheme(self, chunks: List[Dict[str, Any]], detected_schemes: Set[str]) -> List[Dict[str, Any]]:
        """Filter and rank chunks by scheme relevance"""
        filtered_chunks = []
        
        for chunk in chunks:
            chunk_scheme_id = chunk.get('scheme_id', '')
            chunk_section = chunk.get('section', '').lower()
            
            # Boost score if chunk matches detected scheme
            boost_factor = 2.0 if chunk_scheme_id in detected_schemes else 1.0
            scheme_boost_factor = 1.5 if chunk_scheme_id in detected_schemes else 1.0
            
            # Additional scoring factors
            score_boost = boost_factor * scheme_boost_factor
            
            # Check section relevance
            section_relevance = self._calculate_section_relevance(chunk_section, detected_schemes)
            
            filtered_chunk = chunk.copy()
            filtered_chunk['relevance_boost'] = score_boost
            filtered_chunk['section_relevance'] = section_relevance
            filtered_chunk['detected_scheme'] = chunk_scheme_id in detected_schemes
            
            filtered_chunks.append(filtered_chunk)
        
        # Sort by relevance score
        filtered_chunks.sort(key=lambda x: (
            x.get('relevance_boost', 1.0) * 
            x.get('section_relevance', 1.0) * 
            (2.0 if x.get('detected_scheme', False) else 1.0)
        ), reverse=True)
        
        logger.info(f"Filtered {len(chunks)} chunks, {len([c for c in filtered_chunks if c.get('detected_scheme')])} match detected schemes")
        return filtered_chunks
    
    def _calculate_section_relevance(self, section: str, detected_schemes: Set[str]) -> float:
        """Calculate relevance score for section based on detected schemes"""
        section_lower = section.lower()
        
        # High relevance sections
        high_relevance_sections = {
            'scheme details', 'fund house', 'about', 'fund manager'
        }
        
        # Medium relevance sections
        medium_relevance_sections = {
            'expense ratio', 'exit load', 'minimum investments', 'benchmark'
        }
        
        # Low relevance sections
        low_relevance_sections = {
            'riskometer'
        }
        
        if section_lower in high_relevance_sections:
            return 3.0
        elif section_lower in medium_relevance_sections:
            return 2.0
        elif section_lower in low_relevance_sections:
            return 1.5
        else:
            return 1.0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of scheme resolver"""
        try:
            health_report = {
                'total_schemes': len(self.scheme_names),
                'total_aliases': sum(len(aliases) for aliases in self.scheme_aliases.values()),
                'scheme_keywords_loaded': len(self.scheme_keywords) > 0,
                'health': 'ok'
            }
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting scheme resolver health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for scheme resolver"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Resolve scheme relevance from queries')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--query', required=True, help='Query to analyze')
    parser.add_argument('--chunks', help='Chunks file to filter')
    
    args = parser.parse_args()
    
    resolver = SchemeResolver(args.config_dir)
    
    if args.chunks:
        import json
        with open(args.chunks, 'r') as f:
            chunks = json.load(f)
        
        result = resolver.detect_scheme_terms(args.query)
        filtered_chunks = resolver.filter_chunks_by_scheme(chunks, result['detected_schemes'])
        
        print(f"Query: {args.query}")
        print(f"Detected Schemes: {result['detected_schemes']}")
        print(f"Filtered Chunks: {len(filtered_chunks)}/{len(chunks)}")
        print(f"Scheme Matches: {sum(1 for c in filtered_chunks if c.get('detected_scheme'))}")
    else:
        # Interactive mode
        print("Scheme Resolver ready for interactive queries")
        print(f"Loaded {len(resolver.scheme_names)} schemes")
        print(f"Total aliases: {sum(len(aliases) for aliases in resolver.scheme_aliases.values())}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
