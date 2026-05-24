"""
Refusal Composer Module - Phase 3
Generates canned refusal responses citing exactly ONE relevant whitelisted URL.
"""

import logging
from typing import Dict, Any
from ..config import load_refusal_intents
from ..retrieval.scheme_resolver import SchemeResolver

logger = logging.getLogger(__name__)

class RefusalComposer:
    def __init__(self, config_dir: str = None, scheme_resolver: SchemeResolver = None):
        self.config = load_refusal_intents(config_dir)
        self.intents = self.config.get("intents", {})
        self.scheme_mapping = self.config.get("scheme_mapping", {})
        self.default_url = self.config.get(
            "default_educational_url", 
            "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth"
        )
        self.resolver = scheme_resolver or SchemeResolver()

    def compose(self, query: str, intent: str) -> str:
        """
        Composes a canned refusal response for a non-factual intent.
        Identifies scheme from query and formats response template with exactly one whitelisted URL.
        """
        intent_data = self.intents.get(intent)
        if not intent_data:
            intent_data = self.intents.get("advisory", {}) # Fallback

        template = intent_data.get("response_template", "")
        
        # 1. Resolve scheme in the query to find the relevant educational URL
        resolved_scheme_id = self.resolver.resolve(query)
        
        scheme_url = self.default_url
        if resolved_scheme_id:
            scheme_url = self.scheme_mapping.get(resolved_scheme_id, self.default_url)
            logger.info(f"Refusal Composer: mapped query to scheme '{resolved_scheme_id}' -> {scheme_url}")
        else:
            logger.info(f"Refusal Composer: no scheme resolved, using default URL -> {scheme_url}")

        # 2. Format the template with the URL
        response = template.format(scheme_url=scheme_url).strip()
        return response
