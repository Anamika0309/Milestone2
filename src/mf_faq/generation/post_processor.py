"""
Compliance Post-Processor Module - Phase 3
Enforces ≤ 3 sentences, whitelisted URL counts, banned words audit, and secondary PII scans on final response.
"""

import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class CompliancePostProcessor:
    def __init__(self, pii_guard, whitelisted_urls: List[str], scheme_mapping: dict, disclaimer: str, safe_template: str, dont_know_template: str):
        self.pii_guard = pii_guard
        self.whitelisted_urls = whitelisted_urls
        self.scheme_mapping = scheme_mapping
        self.disclaimer = disclaimer
        self.safe_template = safe_template
        self.dont_know_template = dont_know_template
        
        self.banned_tokens = [
            "recommend", "invest", "outperform", "better than", "best fund", 
            "should invest", "will outperform", "superior", "guaranteed profit", 
            "massive returns", "highest return"
        ]

    def process(self, draft_answer: str, chunk_text: str, scheme_url: str, date: str, generation_mode: str) -> Tuple[str, bool]:
        """
        Runs rigorous post-checks to guarantee ≤ 3 sentences, banned token filtering,
        exact URL rules, date footer, and secondary PII scans.
        """
        passed = True
        
        # If model answered "I don't know" or similar
        if "don't know" in draft_answer.lower() or "i do not know" in draft_answer.lower() or "not enough information" in draft_answer.lower():
            logger.warning("Factual model returned 'I don't know' reply. Routing to zero-URL response.")
            return self.dont_know_template.strip(), True

        # 1. Banned Token Check
        for token in self.banned_tokens:
            if re.search(rf"\b{re.escape(token)}\b", draft_answer, re.IGNORECASE):
                logger.warning(f"Banned token '{token}' detected in draft response. Using safe template fallback.")
                passed = False
                break
                
        # 2. Sentence Count (cap body at 3 sentences)
        clean_draft = re.sub(r'https?://\S+', '', draft_answer).strip()
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_draft) if s.strip()]
        
        if len(sentences) > 3:
            logger.warning(f"Draft answer has {len(sentences)} sentences (exceeds ≤ 3 limit). Truncating.")
            factual_body = " ".join(sentences[:3])
        else:
            factual_body = " ".join(sentences)

        # 3. Defensive PII Scan on output
        if self.pii_guard.detect(factual_body):
            logger.error("PII leakage detected in generated draft response! Aborting and returning zero-URL PII block.")
            return self.pii_guard.pii_block_response.strip(), False

        # 4. Formulate the response
        final_answer = (
            f"{factual_body}\n"
            f"Source: {scheme_url}\n"
            f"Last updated from sources: {date}"
        )
        
        # 5. URL Compliance Verification
        urls_found = re.findall(r'https?://\S+', final_answer)
        if len(urls_found) != 1 or urls_found[0] != scheme_url:
            logger.error(f"URL Compliance Violation: expected exactly 1 URL '{scheme_url}', found {urls_found}")
            passed = False
            
        # If any check failed, return the bulletproof safe template
        if not passed:
            logger.info("Compliance checks failed. Formulating response via safe fallback template.")
            final_answer = self.safe_template.format(scheme_url=scheme_url, date=date)
            
        return final_answer.strip(), passed
