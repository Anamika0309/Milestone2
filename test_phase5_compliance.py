#!/usr/bin/env python3
"""
Phase 5 Comprehensive Compliance & Evaluation Test Suite
Verifies 35+ Golden Q&A scenarios (exit loads, expense ratios, AUM, lock-ins, min investments),
and strictly tests sentence count limits (<=3), PII protection, refusal paths, whitelisted URLs,
and structured transactional logging.
"""

import os
import re
import sys
import json
import unittest
from unittest.mock import patch
from uuid import UUID

# Ensure src/ is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mf_faq.orchestrator import OrchestratorService
from mf_faq.config import get_whitelisted_urls

# A comprehensive mapping of factual queries to high-quality mock chunks to isolate
# and test the compliance post-processor and secure logging engine deterministically.
MOCK_CHUNKS = {
    "What is the exit load of HDFC Mid Cap Fund?": {
        "chunk_id": "chunk_mid_cap_exit",
        "text": "HDFC Mid Cap Fund Direct Growth charges an exit load of 1% if redeemed within 1 year; no exit load applies thereafter.",
        "scheme_id": "hdfc_mid_cap",
        "section": "Exit Load",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the exit load of HDFC Equity Fund?": {
        "chunk_id": "chunk_equity_exit",
        "text": "HDFC Equity Fund Direct Growth charges an exit load of 1% if redeemed within 1 year; no exit load applies thereafter.",
        "scheme_id": "hdfc_equity",
        "section": "Exit Load",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the exit load of HDFC Focused Fund?": {
        "chunk_id": "chunk_focused_exit",
        "text": "HDFC Focused Fund Direct Growth charges an exit load of 1% if redeemed within 1 year; no exit load applies thereafter.",
        "scheme_id": "hdfc_focused",
        "section": "Exit Load",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the exit load of HDFC ELSS Tax Saver?": {
        "chunk_id": "chunk_elss_exit",
        "text": "HDFC ELSS Tax Saver Direct Plan Growth charges an exit load of 0%; there is no exit load for this scheme.",
        "scheme_id": "hdfc_elss",
        "section": "Exit Load",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the exit load of HDFC Large Cap Fund?": {
        "chunk_id": "chunk_large_cap_exit",
        "text": "HDFC Large Cap Fund Direct Growth charges an exit load of 1% if redeemed within 1 year; no exit load applies thereafter.",
        "scheme_id": "hdfc_large_cap",
        "section": "Exit Load",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the expense ratio of HDFC Mid Cap Fund?": {
        "chunk_id": "chunk_mid_cap_expense",
        "text": "The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.85% per annum for the direct plan.",
        "scheme_id": "hdfc_mid_cap",
        "section": "Expense Ratio",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the expense ratio of HDFC Equity Fund?": {
        "chunk_id": "chunk_equity_expense",
        "text": "The expense ratio of HDFC Equity Fund Direct Growth is 1.02% per annum for the direct plan.",
        "scheme_id": "hdfc_equity",
        "section": "Expense Ratio",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the expense ratio of HDFC Focused Fund?": {
        "chunk_id": "chunk_focused_expense",
        "text": "The expense ratio of HDFC Focused Fund Direct Growth is 0.98% per annum for the direct plan.",
        "scheme_id": "hdfc_focused",
        "section": "Expense Ratio",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the expense ratio of HDFC ELSS Tax Saver?": {
        "chunk_id": "chunk_elss_expense",
        "text": "The expense ratio of HDFC ELSS Tax Saver Direct Plan Growth is 1.15% per annum for the direct plan.",
        "scheme_id": "hdfc_elss",
        "section": "Expense Ratio",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the expense ratio of HDFC Large Cap Fund?": {
        "chunk_id": "chunk_large_cap_expense",
        "text": "The expense ratio of HDFC Large Cap Fund Direct Growth is 0.88% per annum for the direct plan.",
        "scheme_id": "hdfc_large_cap",
        "section": "Expense Ratio",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "Is there a lock-in period for HDFC ELSS Tax Saver?": {
        "chunk_id": "chunk_elss_lockin",
        "text": "HDFC ELSS Tax Saver Direct Plan Growth has a mandatory lock-in period of 3 years from the date of allotment.",
        "scheme_id": "hdfc_elss",
        "section": "Overview",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the lock-in period of HDFC Mid Cap?": {
        "chunk_id": "chunk_mid_cap_lockin",
        "text": "There is no lock-in period for HDFC Mid Cap Fund Direct Growth; investors can redeem units at any time.",
        "scheme_id": "hdfc_mid_cap",
        "section": "Overview",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the lock-in period of HDFC Equity?": {
        "chunk_id": "chunk_equity_lockin",
        "text": "There is no lock-in period for HDFC Equity Fund Direct Growth; investors can redeem units at any time.",
        "scheme_id": "hdfc_equity",
        "section": "Overview",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the lock-in period of HDFC Large Cap Fund?": {
        "chunk_id": "chunk_large_cap_lockin",
        "text": "There is no lock-in period for HDFC Large Cap Fund Direct Growth; investors can redeem units at any time.",
        "scheme_id": "hdfc_large_cap",
        "section": "Overview",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the minimum investment for HDFC Focused Fund?": {
        "chunk_id": "chunk_focused_min",
        "text": "The minimum investment for HDFC Focused Fund Direct Growth is Rs. 5,000 for lumpsum and Rs. 500 for monthly SIP.",
        "scheme_id": "hdfc_focused",
        "section": "Minimum Investment",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the minimum SIP of HDFC Large Cap?": {
        "chunk_id": "chunk_large_cap_min",
        "text": "The minimum monthly SIP investment amount for HDFC Large Cap Fund Direct Growth is Rs. 500.",
        "scheme_id": "hdfc_large_cap",
        "section": "Minimum Investment",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the minimum SIP of HDFC Mid Cap?": {
        "chunk_id": "chunk_mid_cap_min",
        "text": "The minimum monthly SIP investment amount for HDFC Mid Cap Fund Direct Growth is Rs. 500.",
        "scheme_id": "hdfc_mid_cap",
        "section": "Minimum Investment",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "Who is the fund manager of HDFC Mid Cap?": {
        "chunk_id": "chunk_mid_cap_manager",
        "text": "The fund manager of HDFC Mid Cap Fund Direct Growth is Mr. Chirag Setalvad, managing the fund since 2013.",
        "scheme_id": "hdfc_mid_cap",
        "section": "Fund Manager",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "Who is the fund manager of HDFC Focused Fund?": {
        "chunk_id": "chunk_focused_manager",
        "text": "The fund manager of HDFC Focused Fund Direct Growth is Mr. Gopal Agrawal, managing the fund since 2020.",
        "scheme_id": "hdfc_focused",
        "section": "Fund Manager",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the benchmark of HDFC Large Cap Fund?": {
        "chunk_id": "chunk_large_cap_benchmark",
        "text": "The benchmark index of HDFC Large Cap Fund Direct Growth is NIFTY 100 Total Returns Index (TRI).",
        "scheme_id": "hdfc_large_cap",
        "section": "Overview",
        "last_updated": "2026-05-12",
        "score": 0.95
    },
    "What is the category of HDFC ELSS Tax Saver?": {
        "chunk_id": "chunk_elss_category",
        "text": "HDFC ELSS Tax Saver Direct Plan Growth is in the Equity Linked Savings Scheme (ELSS) category.",
        "scheme_id": "hdfc_elss",
        "section": "Overview",
        "last_updated": "2026-05-12",
        "score": 0.95
    }
}

class TestPhase5Compliance(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.config_dir = os.path.join(os.path.dirname(__file__), 'src', 'mf_faq', 'config')
        cls.whitelisted_urls = get_whitelisted_urls(cls.config_dir)
        cls.service = OrchestratorService(cls.config_dir)
        cls.audit_log_path = os.path.join(os.path.dirname(__file__), 'logs', 'audit.jsonl')

    def test_golden_qa_scenarios(self):
        """
        Verify 35+ golden scenarios under strict RAG, formatting, and safety checks.
        """
        golden_scenarios = [
            # --- 1. Factual Queries (Factual answers traceable to exactly 1 URL) ---
            ("What is the exit load of HDFC Mid Cap Fund?", "factual", "hdfc_mid_cap"),
            ("What is the exit load of HDFC Equity Fund?", "factual", "hdfc_equity"),
            ("What is the exit load of HDFC Focused Fund?", "factual", "hdfc_focused"),
            ("What is the exit load of HDFC ELSS Tax Saver?", "factual", "hdfc_elss"),
            ("What is the exit load of HDFC Large Cap Fund?", "factual", "hdfc_large_cap"),
            
            ("What is the expense ratio of HDFC Mid Cap Fund?", "factual", "hdfc_mid_cap"),
            ("What is the expense ratio of HDFC Equity Fund?", "factual", "hdfc_equity"),
            ("What is the expense ratio of HDFC Focused Fund?", "factual", "hdfc_focused"),
            ("What is the expense ratio of HDFC ELSS Tax Saver?", "factual", "hdfc_elss"),
            ("What is the expense ratio of HDFC Large Cap Fund?", "factual", "hdfc_large_cap"),
            
            ("Is there a lock-in period for HDFC ELSS Tax Saver?", "factual", "hdfc_elss"),
            ("What is the lock-in period of HDFC Mid Cap?", "factual", "hdfc_mid_cap"),
            ("What is the lock-in period of HDFC Equity?", "factual", "hdfc_equity"),
            ("What is the lock-in period of HDFC Large Cap Fund?", "factual", "hdfc_large_cap"),
            
            ("What is the minimum investment for HDFC Focused Fund?", "factual", "hdfc_focused"),
            ("What is the minimum SIP of HDFC Large Cap?", "factual", "hdfc_large_cap"),
            ("What is the minimum SIP of HDFC Mid Cap?", "factual", "hdfc_mid_cap"),
            
            ("Who is the fund manager of HDFC Mid Cap?", "factual", "hdfc_mid_cap"),
            ("Who is the fund manager of HDFC Focused Fund?", "factual", "hdfc_focused"),
            ("What is the benchmark of HDFC Large Cap Fund?", "factual", "hdfc_large_cap"),
            ("What is the category of HDFC ELSS Tax Saver?", "factual", "hdfc_elss"),

            # --- 2. PII Queries (100% rejection, exactly 0 URLs) ---
            ("My PAN card is ABCDE1234F. What are my HDFC scheme details?", "pii_blocked", None),
            ("My phone number is +91 9999988888. Can you call me to discuss HDFC Equity?", "pii_blocked", None),
            ("Email me at client@hdfc.com with HDFC Mid Cap facts.", "pii_blocked", None),
            ("Verify code: 123456", "pii_blocked", None),
            ("My Aadhaar card number is 9999 8888 7777. What is my exit load?", "pii_blocked", None),

            # --- 3. Refusal Queries (Intent deflection, exactly 1 URL) ---
            ("Should I buy HDFC Mid Cap Fund?", "advisory", "hdfc_mid_cap"),
            ("What is the future outlook for HDFC Focused Fund?", "prediction", "hdfc_focused"),
            ("Is HDFC Large Cap Fund worth investing?", "advisory", "hdfc_large_cap"),
            ("Can you recommend HDFC Equity Fund?", "advisory", "hdfc_equity"),
            ("Which is better: HDFC Mid Cap vs HDFC Large Cap?", "comparison", "hdfc_mid_cap"),
            ("Will HDFC ELSS Fund perform well next year?", "prediction", "hdfc_elss"),

            # --- 4. Out of Corpus / Low Confidence (Exactly 0 URLs) ---
            ("What is the weather in Mumbai today?", "dont_know", None),
            ("What is the price of gold in India?", "dont_know", None),
            ("Who is the Prime Minister of India?", "dont_know", None),
        ]
        
        # Verify that we have defined at least 30+ golden Q&A scenarios
        self.assertGreaterEqual(len(golden_scenarios), 35, "Golden scenarios must be at least 35")
        
        print(f"\nEvaluating {len(golden_scenarios)} golden compliance scenarios...")
        
        for idx, (query, expected_intent, expected_scheme) in enumerate(golden_scenarios, 1):
            with self.subTest(idx=idx, query=query):
                # 1. Execute query. We patch the retriever for factual queries so that we return
                # high-quality structured chunks deterministically.
                if query in MOCK_CHUNKS:
                    mock_chunk = MOCK_CHUNKS[query]
                    with patch.object(self.service.retriever, 'retrieve', return_value=[(mock_chunk["chunk_id"], 0.95, "dense")]), \
                         patch.object(self.service, '_get_chunk_details', return_value=mock_chunk), \
                         patch.object(self.service.confidence_gate, 'filter_by_confidence', return_value=[mock_chunk]):
                        res = self.service.ask(query, use_groq=False)
                else:
                    res = self.service.ask(query, use_groq=False)
                
                # Assertions based on expected intent
                if expected_intent == "pii_blocked":
                    self.assertEqual(res["intent"], "pii_blocked")
                    self.assertIsNone(res["source_url"])
                    self.assertNotIn("http", res["answer"].lower())
                    
                elif expected_intent == "dont_know":
                    self.assertEqual(res["intent"], "dont_know")
                    self.assertIsNone(res["source_url"])
                    self.assertNotIn("http", res["answer"].lower())
                    
                elif expected_intent in ["advisory", "comparison", "prediction"]:
                    # Support general deflection intents as long as it correctly routes to a refusal class
                    self.assertIn(res["intent"], ["advisory", "comparison", "prediction", "performance"])
                    self.assertIsNotNone(res["source_url"])
                    self.assertIn(res["source_url"], self.whitelisted_urls)
                    if expected_scheme:
                        expected_url = self.service.scheme_mapping[expected_scheme]
                        self.assertEqual(res["source_url"], expected_url)
                        
                else: # Factual answers
                    self.assertEqual(res["intent"], "factual")
                    self.assertTrue(res["checks_passed"])
                    self.assertIsNotNone(res["source_url"])
                    self.assertIn(res["source_url"], self.whitelisted_urls)
                    if expected_scheme:
                        expected_url = self.service.scheme_mapping[expected_scheme]
                        self.assertEqual(res["source_url"], expected_url)
                    
                    # Sentence Cap: generated response body must be <= 3 sentences (excluding headers/footers)
                    body_part = res["answer"].split("Source:")[0].strip()
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body_part) if s.strip()]
                    self.assertLessEqual(len(sentences), 3, f"Factual body exceeds 3 sentences limit: {sentences}")
                    
                    # Ensure the mandatory date footer is appended
                    self.assertIn("Last updated from sources:", res["answer"])
                    
                # Verify that transaction is logged correctly
                self.assertIn("request_id", res)
                self.assertIsNotNone(res["request_id"])
                
                try:
                    UUID(res["request_id"], version=4)
                except ValueError:
                    self.fail(f"request_id '{res['request_id']}' is not a valid UUIDv4")
                
                print(f"  [{idx:02d}] query='{query[:40]}...' intent='{res['intent']}' checks_passed={res['checks_passed']} -> PASSED")

    def test_audit_logs_integrity(self):
        """
        Verify Phase 5 Observability: audit.jsonl exists, is non-empty,
        and enforces PII / query hashing with zero raw query leakages.
        """
        self.assertTrue(os.path.exists(self.audit_log_path), f"Audit log file not found at {self.audit_log_path}")
        
        entries = []
        with open(self.audit_log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
                    
        self.assertGreater(len(entries), 0, "Audit log file is empty")
        
        for idx, entry in enumerate(entries):
            required_keys = [
                "timestamp", "request_id", "query_hash", "resolved_scheme_id",
                "intent_detected", "confidence_score", "top_chunk_id",
                "latency_ms", "compliance_checks_passed"
            ]
            for key in required_keys:
                self.assertIn(key, entry, f"Missing key '{key}' in audit log entry {idx}")
                
            # Assert query hash starts with 'sha256:' and is hashed (length 71: 'sha256:' is 7 + 64 char hex = 71)
            self.assertTrue(entry["query_hash"].startswith("sha256:"), f"Invalid query hash format in entry {idx}")
            self.assertEqual(len(entry["query_hash"]), 71, f"Invalid query hash length in entry {idx}")
            
            raw_data_dump = json.dumps(entry)
            self.assertNotIn("Aadhaar", raw_data_dump)
            self.assertNotIn("PAN", raw_data_dump)
            self.assertNotIn("phone", raw_data_dump)
            
        print(f"\nAudit logs integrity check passed! Verified {len(entries)} transaction records successfully.")

def run_compliance_suite():
    print("\n" + "="*70)
    print("RUNNING PHASE 5 COMPLIANCE & ACCURACY HARNESS")
    print("="*70)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase5Compliance)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    print("="*70)
    print(f"Summary: {result.testsRun} main test methods run.")
    print(f"Failures: {len(result.failures)} | Errors: {len(result.errors)}")
    print("="*70 + "\n")
    
    if result.wasSuccessful():
        print("100% COMPLIANCE SUCCESS! System meets all regulatory and architecture gates.")
        return 0
    else:
        print("SYSTEM NON-COMPLIANCE DETECTED! Check test failure outputs.")
        return 1

if __name__ == '__main__':
    sys.exit(run_compliance_suite())
