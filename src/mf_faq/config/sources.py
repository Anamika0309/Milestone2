"""
Sources Configuration Module
Loads and provides access to sources configuration.
"""

import yaml
import os
from typing import Dict, List, Any


def load_sources(config_dir: str = None) -> Dict[str, Any]:
    """Load sources configuration from YAML file"""
    if config_dir is None:
        config_dir = os.path.join(os.path.dirname(__file__))
    
    sources_file = os.path.join(config_dir, 'sources.yaml')
    
    try:
        with open(sources_file, 'r', encoding='utf-8') as f:
            sources = yaml.safe_load(f)
        
        return sources
        
    except FileNotFoundError:
        # Return default empty sources if file not found
        return {
            'schemes': []
        }
    except Exception as e:
        raise Exception(f"Error loading sources: {e}")


def get_scheme_urls(config_dir: str = None) -> List[str]:
    """Get list of scheme URLs from sources"""
    sources = load_sources(config_dir)
    urls = []
    
    for scheme in sources.get('schemes', []):
        for source in scheme.get('sources', []):
            url = source.get('url')
            if url:
                urls.append(url)
    
    return urls


def get_scheme_by_id(scheme_id: str, config_dir: str = None) -> Dict[str, Any]:
    """Get scheme configuration by ID"""
    sources = load_sources(config_dir)
    
    for scheme in sources.get('schemes', []):
        if scheme.get('id') == scheme_id:
            return scheme
    
    return {}


def get_all_schemes(config_dir: str = None) -> List[Dict[str, Any]]:
    """Get all scheme configurations"""
    sources = load_sources(config_dir)
    return sources.get('schemes', [])
