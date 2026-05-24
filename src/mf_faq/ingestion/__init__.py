"""
Ingestion Package - Phase 1
This package handles the corpus ingestion pipeline for the Mutual Fund FAQ Assistant.
"""

try:
    from .fetcher import Fetcher, FetchResult
except ImportError:
    Fetcher = None
    FetchResult = None

__all__ = ['Fetcher', 'FetchResult']
