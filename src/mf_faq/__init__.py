"""
Mutual Fund FAQ Assistant - Main Package
A facts-only RAG-based Q&A assistant for HDFC Mutual Fund schemes.

Phases:
0 - Foundation & Governance: Configuration and guardrails
1 - Ingestion & Corpus Build: Data processing pipeline
2 - Retrieval Layer: Hybrid search and ranking
3 - Reasoning & Guardrails: Intent classification and generation
4 - User Interface: FastAPI web application
5 - Evaluation & Compliance: Testing and monitoring
"""

__version__ = "1.0.0"
__author__ = "MF FAQ Assistant Team"

# Automatically load environment variables from root-level .env file if it exists
import os
try:
    # Walk up from src/mf_faq to find root workspace
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    dotenv_path = os.path.join(root_dir, ".env")
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                        val = val[1:-1]
                    # Only set if not already set by system environment
                    if key and val and key not in os.environ:
                        os.environ[key] = val
except Exception:
    pass

# Import main components
from .config import load_sources, validate_url_whitelist
from .ingestion import Fetcher, FetchResult
from .orchestrator import PIIGuard, IntentClassifier, RefusalComposer, OrchestratorService

__all__ = [
    'load_sources',
    'validate_url_whitelist', 
    'Fetcher',
    'FetchResult',
    'PIIGuard',
    'IntentClassifier',
    'RefusalComposer',
    'OrchestratorService'
]

