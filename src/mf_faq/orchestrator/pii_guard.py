"""
PII Guard Module - Phase 3
Handles detection and redaction of personally identifiable information (PII).
"""

import re
import logging
from typing import Dict, List, Any, Tuple
from ..config import load_pii_patterns

logger = logging.getLogger(__name__)

class PIIGuard:
    def __init__(self, config_dir: str = None):
        self.config = load_pii_patterns(config_dir)
        self.patterns = self._compile_patterns()
        self.redaction_rules = self.config.get("redaction_rules", {})
        self.pii_block_response = self.redaction_rules.get(
            "pii_block_response",
            "I cannot process requests containing personal information like PAN, Aadhaar, phone numbers, or email addresses.\nFor factual mutual fund information, please ask general questions without sharing personal details.\nFacts-only. No investment advice."
        ).strip()

    def _compile_patterns(self) -> List[Dict[str, Any]]:
        compiled = []
        # Load all pattern lists from config
        pattern_keys = [k for k in self.config.keys() if k.endswith("_patterns")]
        
        for key in pattern_keys:
            category = key.replace("_patterns", "")
            pattern_list = self.config.get(key, [])
            if not isinstance(pattern_list, list):
                continue
                
            for idx, item in enumerate(pattern_list):
                if not isinstance(item, dict) or "pattern" not in item:
                    continue
                
                raw_pattern = item["pattern"]
                case_sensitive = item.get("case_sensitive", False)
                flags = 0 if case_sensitive else re.IGNORECASE
                
                try:
                    regex = re.compile(raw_pattern, flags)
                    compiled.append({
                        "category": category,
                        "description": item.get("description", f"{category}_{idx}"),
                        "regex": regex,
                        "context_patterns": item.get("context_patterns", [])
                    })
                except re.error as e:
                    logger.error(f"Failed to compile pattern {raw_pattern}: {e}")
                    
        return compiled

    def detect(self, text: str) -> bool:
        """
        Detects if PII is present in the text.
        Applies context keywords check when required.
        """
        if not text:
            return False
            
        for pat in self.patterns:
            matches = list(pat["regex"].finditer(text))
            if not matches:
                continue
                
            # If context patterns are defined, we require one of them to exist in the text
            context_patterns = pat["context_patterns"]
            if context_patterns:
                text_lower = text.lower()
                context_matched = any(kw.lower() in text_lower for kw in context_patterns)
                if not context_matched:
                    continue  # Ignore match since context words are missing
            
            logger.warning(f"PII Detected: {pat['description']} (Category: {pat['category']})")
            return True
            
        return False

    def redact(self, text: str) -> str:
        """
        Redacts PII tokens in the text using redaction rules from configuration.
        """
        if not text:
            return text
            
        redacted_text = text
        log_redaction_rules = self.redaction_rules.get("log_redaction", [])
        
        for rule in log_redaction_rules:
            pattern = rule.get("pattern")
            replacement = rule.get("replacement", "[REDACTED]")
            if pattern:
                try:
                    redacted_text = re.sub(pattern, replacement, redacted_text, flags=re.IGNORECASE)
                except re.error as e:
                    logger.error(f"Failed to apply redaction pattern {pattern}: {e}")
                    
        return redacted_text
