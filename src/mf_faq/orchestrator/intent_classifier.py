"""
Intent Classifier Module - Phase 3
Classifies query intents (factual vs refusal intents like advisory, comparison, etc.).
"""

import re
import logging
from typing import Dict, List, Any
from ..config import load_refusal_intents

logger = logging.getLogger(__name__)

class IntentClassifier:
    def __init__(self, config_dir: str = None):
        self.config = load_refusal_intents(config_dir)
        self.intents = self.config.get("intents", {})

    def classify(self, text: str) -> str:
        """
        Classify the intent of the incoming query.
        Returns the matching intent key (e.g., 'advisory', 'comparison') or 'factual' if no match.
        """
        if not text:
            return "factual"

        text_lower = text.lower()

        # Iterate through all configured intents and check for matches
        for intent_name, intent_data in self.intents.items():
            patterns = intent_data.get("patterns", [])
            for pattern in patterns:
                # Compile pattern as a case-insensitive regex
                # Using simple word boundary or substring search
                try:
                    # Treat pattern as literal first, but compile it to support regex search if needed
                    # Safe escaping while preserving simple matches
                    escaped_pattern = re.escape(pattern)
                    # If pattern is a single word, require word boundaries to avoid false matching inside other words
                    if " " not in pattern and len(pattern) > 2:
                        regex_str = rf"\b{escaped_pattern}\b"
                    else:
                        regex_str = escaped_pattern
                        
                    regex = re.compile(regex_str, re.IGNORECASE)
                    if regex.search(text_lower):
                        logger.info(f"Intent Classified: {intent_name} (pattern match: '{pattern}')")
                        return intent_name
                except re.error as e:
                    # Fallback to simple substring match if regex compilation fails
                    logger.error(f"Failed to compile pattern {pattern}: {e}")
                    if pattern.lower() in text_lower:
                        logger.info(f"Intent Classified: {intent_name} (substring match fallback: '{pattern}')")
                        return intent_name

        return "factual"
