"""
Configuration Package - Phase 0
This package handles all configuration files for the Mutual Fund FAQ Assistant.

Configuration Files:
- sources.yaml: Exclusive corpus of 5 HDFC URLs
- refusal_intents.yaml: Patterns and templates for non-factual queries
- disclaimer.txt: Core disclaimer text
- pii_patterns.yaml: PII detection and redaction rules
- governance_rules.md: Complete governance framework
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any


def load_sources(config_dir: str = None) -> Dict[str, Any]:
    """Load sources configuration from YAML file"""
    if config_dir is None:
        config_dir = Path(__file__).parent
    else:
        config_dir = Path(config_dir)
    
    sources_file = config_dir / 'sources.yaml'
    
    try:
        with open(sources_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Sources configuration not found: {sources_file}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in sources configuration: {e}")


def load_refusal_intents(config_dir: str = None) -> Dict[str, Any]:
    """Load refusal intents configuration from YAML file"""
    if config_dir is None:
        config_dir = Path(__file__).parent
    else:
        config_dir = Path(config_dir)
    
    intents_file = config_dir / 'refusal_intents.yaml'
    
    try:
        with open(intents_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Refusal intents configuration not found: {intents_file}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in refusal intents configuration: {e}")


def load_pii_patterns(config_dir: str = None) -> Dict[str, Any]:
    """Load PII patterns configuration from YAML file"""
    if config_dir is None:
        config_dir = Path(__file__).parent
    else:
        config_dir = Path(config_dir)
    
    pii_file = config_dir / 'pii_patterns.yaml'
    
    try:
        with open(pii_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"PII patterns configuration not found: {pii_file}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in PII patterns configuration: {e}")


def load_disclaimer(config_dir: str = None) -> str:
    """Load disclaimer text from file"""
    if config_dir is None:
        config_dir = Path(__file__).parent
    else:
        config_dir = Path(config_dir)
    
    disclaimer_file = config_dir / 'disclaimer.txt'
    
    try:
        with open(disclaimer_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Disclaimer file not found: {disclaimer_file}")


def get_whitelisted_urls(config_dir: str = None) -> List[str]:
    """Extract list of whitelisted URLs from sources configuration"""
    sources = load_sources(config_dir)
    urls = []
    
    for scheme in sources.get('schemes', []):
        for source in scheme.get('sources', []):
            url = source.get('url')
            if url:
                urls.append(url)
    
    return urls


def validate_url_whitelist(urls: List[str]) -> bool:
    """Validate that all URLs are in the whitelist"""
    try:
        whitelisted_urls = get_whitelisted_urls()
        for url in urls:
            if url not in whitelisted_urls:
                return False
        return True
    except Exception:
        return False


def get_scheme_mapping(config_dir: str = None) -> Dict[str, str]:
    """Get mapping of scheme IDs to URLs"""
    sources = load_sources(config_dir)
    mapping = {}
    
    for scheme in sources.get('schemes', []):
        scheme_id = scheme.get('id')
        for source in scheme.get('sources', []):
            url = source.get('url')
            if url:
                mapping[scheme_id] = url
                break
    
    return mapping


__all__ = [
    'load_sources',
    'load_refusal_intents', 
    'load_pii_patterns',
    'load_disclaimer',
    'get_whitelisted_urls',
    'validate_url_whitelist',
    'get_scheme_mapping'
]
