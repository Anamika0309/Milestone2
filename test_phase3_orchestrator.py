#!/usr/bin/env python3
"""
Phase 3 Orchestrator Integration & Guardrails Test Suite
Tests PII blocking, intent classification, refusal composition, factual synthesis,
banned word filtering, sentence length caps, and strict URL compliance.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mf_faq.orchestrator import PIIGuard, IntentClassifier, RefusalComposer, OrchestratorService
from mf_faq.config import get_whitelisted_urls

class TestPhase3Orchestrator(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.config_dir = os.path.join(os.path.dirname(__file__), 'src', 'mf_faq', 'config')
        cls.whitelisted_urls = get_whitelisted_urls(cls.config_dir)
        cls.service = OrchestratorService(cls.config_dir)

    def test_pii_guard_positive(self):
        """Test that various Indian PII formats are successfully blocked with exactly 0 URLs"""
        pii_queries = [
            "My Aadhaar card is 1234 5678 9012. Can you help me?",
            "Please check my PAN number ABCDE1234F details.",
            "Send the updates to client@example.com immediately.",
            "Reach out to me at +91 9876543210 for investment assistance.",
            "Verify code: 123456"
        ]
        
        for q in pii_queries:
            with self.subTest(query=q):
                res = self.service.ask(q)
                self.assertEqual(res["intent"], "pii_blocked")
                # Assert exactly 0 URLs in the answer to prevent link exposure in personal contexts
                urls = [url for url in self.whitelisted_urls if url in res["answer"]]
                self.assertEqual(len(urls), 0, f"Blocked query should contain 0 whitelisted URLs, got {urls}")
                self.assertNotIn("http", res["answer"].lower())
                print(f"  ✓ blocked PII: '{q[:30]}...' -> OK (0 URLs)")

    def test_pii_guard_negative(self):
        """Test that legitimate queries (like expense ratios or AUM values) are NOT blocked (false positive check)"""
        safe_queries = [
            "What is the expense ratio of HDFC Equity Fund?",
            "What is the minimum SIP amount for ELSS tax saver?",
            "Is the exit load 1.25% or 1% if redeemed within 1 year?",
            "Can I invest Rs. 500 in this fund?"
        ]
        
        for q in safe_queries:
            with self.subTest(query=q):
                res = self.service.ask(q)
                self.assertNotEqual(res["intent"], "pii_blocked", f"Query should not be blocked as PII: {q}")
                print(f"  ✓ passed safe query: '{q}' -> OK")

    def test_intent_classification_and_refusal(self):
        """Test that advisory, comparison, and prediction queries are correctly deflected with exactly 1 whitelisted URL"""
        advisory_queries = [
            ("Should I invest in HDFC Mid Cap Fund?", "advisory", "hdfc_mid_cap"),
            ("Which is better: HDFC Equity vs HDFC Focused?", "comparison", "hdfc_equity"),
            ("Will HDFC Large Cap outperform next year?", "prediction", "hdfc_large_cap")
        ]
        
        for q, expected_intent, expected_scheme in advisory_queries:
            with self.subTest(query=q):
                res = self.service.ask(q)
                self.assertEqual(res["intent"], expected_intent)
                
                # Check for exactly 1 whitelisted URL in response matching the scheme
                urls_found = [url for url in self.whitelisted_urls if url in res["answer"]]
                self.assertEqual(len(urls_found), 1, f"Should have exactly 1 whitelisted URL, found {urls_found}")
                
                expected_url = self.service.scheme_mapping[expected_scheme]
                self.assertEqual(urls_found[0], expected_url, f"Expected URL {expected_url}, got {urls_found[0]}")
                print(f"  ✓ deflected {expected_intent}: '{q}' -> Refusal OK with exact URL: {urls_found[0]}")

    def test_dont_know_low_confidence_path(self):
        """Test that ungrounded queries/empty retrievals route to 'dont_know' with exactly 0 URLs"""
        # Force empty retrieval by mocking the retriever to return []
        with patch.object(self.service.retriever, 'retrieve', return_value=[]):
            res = self.service.ask("What is the rank of HDFC Mid Cap Fund?")
            self.assertEqual(res["intent"], "dont_know")
            self.assertEqual(res["source_url"], None)
            self.assertNotIn("http", res["answer"].lower())
            print("  ✓ deflected empty retrieval: 'I don't know' -> OK (0 URLs)")

    def test_banned_words_fallback(self):
        """Test that responses containing banned advisory tokens are demoted to the safe template fallback"""
        # Set up mock retrieval result containing a banned word
        mock_chunk = {
            "chunk_id": "chunk_1",
            "text": "HDFC Mid Cap Fund is the best fund that will outperform other mid cap funds. We recommend you should invest in it today.",
            "score": 0.95,
            "source": "dense",
            "scheme_id": "hdfc_mid_cap",
            "section": "Overview",
            "last_updated": "2026-05-12"
        }
        
        with patch.object(self.service.retriever, 'retrieve', return_value=[("chunk_1", 0.95, "dense")]), \
             patch.object(self.service, '_get_chunk_details', return_value=mock_chunk), \
             patch.object(self.service.confidence_gate, 'filter_by_confidence', return_value=[mock_chunk]):
                 
             res = self.service.ask("Tell me about HDFC Mid Cap portfolio", use_groq=False)
             # Should pass confidence but fail post-processing banned words check, falling back to safe template
             self.assertFalse(res["checks_passed"])
             self.assertIn("HDFC Mutual Fund schemes offer factual details", res["answer"])
             self.assertIn(self.service.scheme_mapping["hdfc_mid_cap"], res["answer"])
             
             # URL compliance must still be 100% (exactly 1 whitelisted URL present)
             urls_found = [url for url in self.whitelisted_urls if url in res["answer"]]
             self.assertEqual(len(urls_found), 1)
             print("  ✓ banned token filtered -> fallback to safe template OK")

    def test_sentence_length_truncation(self):
        """Test that factual responses exceeding 3 sentences are truncated to exactly 3 sentences"""
        long_text = "HDFC Equity Fund has a history of 25 years. It is a flexi cap scheme. The minimum SIP is ₹500. The exit load is 1% if redeemed within a year. AUM is ₹30000 Cr."
        mock_chunk = {
            "chunk_id": "chunk_2",
            "text": long_text,
            "score": 0.95,
            "source": "dense",
            "scheme_id": "hdfc_equity",
            "section": "About",
            "last_updated": "2026-05-12"
        }
        
        with patch.object(self.service.retriever, 'retrieve', return_value=[("chunk_2", 0.95, "dense")]), \
             patch.object(self.service, '_get_chunk_details', return_value=mock_chunk), \
             patch.object(self.service.confidence_gate, 'filter_by_confidence', return_value=[mock_chunk]):
                 
             res = self.service.ask("What is HDFC Equity Fund details?", use_groq=False)
             self.assertTrue(res["checks_passed"])
             
             # Split response by newline to extract the factual body (before Source: ...)
             body_part = res["answer"].split("Source:")[0].strip()
             import re
             sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body_part) if s.strip()]
             
             self.assertTrue(len(sentences) <= 3, f"Factual body should have <= 3 sentences, got {len(sentences)}")
             self.assertIn("Last updated from sources: 2026-05-12", res["answer"])
             print(f"  ✓ response length capped at {len(sentences)} sentences (limit <= 3) -> OK")

def run_tests():
    print("\n" + "="*60)
    print("RUNNING PHASE 3 REASONING & GUARDRAILS TESTS")
    print("="*60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase3Orchestrator)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    print("="*60)
    print(f"Results: {result.testsRun} run, {len(result.failures)} failed, {len(result.errors)} errors")
    print("="*60 + "\n")
    
    if result.wasSuccessful():
        print("🎉 ALL REASONING & GUARDRAILS COMPLIANCE TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TEST CASES FAILED compliance validation. Review logs.")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
