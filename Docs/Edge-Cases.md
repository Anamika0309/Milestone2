# Edge Cases - Mutual Fund FAQ Assistant

This document outlines comprehensive edge cases and failure scenarios for each phase of the Mutual Fund FAQ Assistant project. Each edge case includes description, impact, detection method, and mitigation strategy.

---

## Phase 0 - Foundation & Governance Edge Cases

### EC-0.1: Source URL Changes
**Description:** One or more of the 5 whitelisted URLs change structure or become unavailable  
**Impact:** Corpus becomes incomplete or broken  
**Detection:** URL monitoring, 404 errors, content hash changes  
**Mitigation:** Alert system, manual URL review, sources.yaml update

### EC-0.2: Governance Rule Conflicts
**Description:** Refusal taxonomy conflicts with factual query classification  
**Impact:** Legitimate factual queries get refused  
**Detection:** User feedback, eval suite failures  
**Mitigation:** Refine intent patterns, add factual query examples

### EC-0.3: PII Pattern Evolution
**Description:** New PII patterns emerge (e.g., new document formats)  
**Impact:** PII leakage into logs or responses  
**Detection:** Log scanning, user reports  
**Mitigation:** Update PII regex patterns, expand deny-list

### EC-0.4: Category Ambiguity
**Description:** Scheme categories overlap or change (e.g., new fund categories)  
**Impact:** Incorrect scheme classification, poor retrieval  
**Detection:** Content analysis, scheme metadata changes  
**Mitigation:** Update category mappings, expand resolver logic

---

## Phase 1 - Ingestion & Corpus Build Edge Cases

### Sub-phase 1.1 - Fetcher Edge Cases

#### EC-1.1: Robots.txt Blocking
**Description:** Groww updates robots.txt to block automated access  
**Impact:** Fetcher cannot retrieve content, corpus becomes stale  
**Detection:** HTTP 403/401 errors, robots.txt parsing failures  
**Mitigation:** Respect robots.txt, alert administrators, manual review

#### EC-1.2: Rate Limiting (429)
**Description:** Groww implements aggressive rate limiting  
**Impact:** Incomplete corpus, failed refresh cycles  
**Detection:** HTTP 429 responses, timeout patterns  
**Mitigation:** Exponential backoff, respect Retry-After headers

#### EC-1.3: ETag/Cache Invalidation
**Description:** ETag headers inconsistent or missing  
**Impact:** Unnecessary re-fetches, bandwidth waste  
**Detection:** ETag analysis, fetch logs  
**Mitigation:** Fallback to content-hash comparison

#### EC-1.4: Redirect Chains
**Description:** URLs redirect through multiple hops  
**Impact:** Content from unexpected sources, governance violations  
**Detection:** 301/302 response tracking  
**Mitigation:** Reject redirects >1 hop, manual URL verification

### Sub-phase 1.2 - Extractor Edge Cases

#### EC-1.5: JavaScript-Heavy Content
**Description:** Groww increases JS-rendered content dependency  
**Impact:** Extractor misses critical information  
**Detection:** Low text extraction yields, missing must-have anchors  
**Mitigation:** Playwright fallback, extended render wait times

#### EC-1.6: Dynamic Content Loading
**Description:** Content loads via AJAX after page load  
**Impact:** Incomplete extraction, missing facts  
**Detection:** Section content gaps, extraction health degraded  
**Mitigation:** Wait strategies, multiple content snapshots

#### EC-1.7: Anti-Scraping Measures
**Description:** Groww implements CAPTCHA or bot detection  
**Impact:** Fetcher blocked, corpus updates fail  
**Detection:** CAPTCHA responses, access denied patterns  
**Mitigation:** User-Agent rotation, request pattern randomization

### Sub-phase 1.3 - Cleaner Edge Cases

#### EC-1.8: Boilerplate Evolution
**Description:** New boilerplate patterns emerge  
**Impact:** Noisy chunks, poor retrieval quality  
**Detection:** Chunk analysis, retrieval performance degradation  
**Mitigation:** Update strip-list, machine learning classification

#### EC-1.9: Content Format Changes
**Description:** Groww changes HTML structure or data formats  
**Impact:** Cleaner fails to process content correctly  
**Detection:** Extraction errors, content hash anomalies  
**Mitigation:** Robust parsing, multiple selector strategies

#### EC-1.10: Volatile Field Explosion
**Description:** NAV/AUM data appears in unexpected places  
**Impact:** Unstable content hashes, excessive re-indexing  
**Detection:** Hash change analysis, refresh frequency spikes  
**Mitigation:** Expand volatile field detection, regex patterns

### Sub-phase 1.4 - Chunker Edge Cases

#### EC-1.11: Section Boundary Ambiguity
**Description:** HTML sections don't align with logical content boundaries  
**Impact:** Facts split across chunks, poor retrieval  
**Detection:** Chunk size analysis, content integrity checks  
**Mitigation:** Semantic boundary detection, overlap strategies

#### EC-1.12: Table Fragmentation
**Description:** Tabular data split across chunks  
**Impact:** Corrupted financial data, incorrect answers  
**Detection:** Numeric fact validation, table structure analysis  
**Mitigation:** Atomic table row preservation, table-aware chunking

### Sub-phase 1.5 - Embedder Edge Cases

#### EC-1.13: Model Version Mismatch
**Description:** Embedding model updates without index rebuild  
**Impact:** Retrieval failures, vector space incompatibility  
**Detection:** Embedder.json version mismatch, retrieval errors  
**Mitigation:** Version validation, automatic rebuild triggers

#### EC-1.14: Embedding API Limits
**Description:** Rate limits or quota exceeded on embedding service  
**Impact:** Incomplete corpus, failed refresh cycles  
**Detection:** API error monitoring, queue buildup  
**Mitigation:** Local embedding fallback, batch processing

### Sub-phase 1.6 - Indexer Edge Cases

#### EC-1.15: Index Corruption
**Description:** Vector or sparse index files become corrupted  
**Impact:** Retrieval failures, system downtime  
**Detection:** Index integrity checks, CRC validation  
**Mitigation:** Atomic swaps, backup index rotation

#### EC-1.16: Memory Constraints
**Description:** Index size exceeds available memory  
**Impact:** System crashes, performance degradation  
**Detection:** Memory usage monitoring, OOM errors  
**Mitigation:** Streaming indexes, memory-mapped files

### Sub-phase 1.7 - Refresh & Health Edge Cases

#### EC-1.17: Concurrent Refresh Conflicts
**Description:** Multiple refresh jobs run simultaneously  
**Impact:** Index corruption, race conditions  
**Detection:** Job monitoring, lock file analysis  
**Mitigation:** Distributed locks, job queue management

#### EC-1.18: Partial Update Failures
**Description:** Some URLs update successfully, others fail  
**Impact:** Inconsistent corpus state  
**Detection:** Per-URL health monitoring, hash validation  
**Mitigation:** Atomic operations, rollback mechanisms

---

## Phase 2 - Retrieval Layer Edge Cases

### EC-2.1: Query Ambiguity
**Description:** User query matches multiple schemes or concepts  
**Impact:** Wrong scheme selection, irrelevant results  
**Detection:** Low confidence scores, user feedback  
**Mitigation:** Disambiguation prompts, scheme clarification

### EC-2.2: Scheme Name Variations
**Description:** Users refer to schemes with unofficial names or abbreviations  
**Impact:** Scheme resolver fails, poor retrieval  
**Detection:** Resolver failure logs, empty results  
**Mitigation:** Alias expansion, fuzzy matching, user suggestions

### EC-2.3: Hybrid Retrieval Imbalance
**Description:** Dense and sparse retrieval disagree significantly  
**Impact:** Fusion produces poor results, low confidence  
**Detection:** Score distribution analysis, confidence gaps  
**Mitigation:** Adaptive weighting, confidence-based fusion

### EC-2.4: Cross-encoder Failures
**Description:** Re-ranker model unavailable or errors  
**Impact:** No re-ranking, poor precision  
**Detection:** Model health checks, API error monitoring  
**Mitigation:** Fallback to fusion results, model redundancy

### EC-2.5: Section Mismatch
**Description:** Retrieved chunks from wrong document sections  
**Impact:** Incorrect answers, citation errors  
**Detection:** Section metadata analysis, user validation  
**Mitigation:** Section-aware retrieval, content validation

### EC-2.6: Empty Results
**Description:** No chunks meet confidence threshold  
**Impact:** "I don't know" responses for valid queries  
**Detection:** Result count monitoring, confidence analysis  
**Mitigation:** Threshold tuning, query reformulation

---

## Phase 3 - Reasoning & Guardrails Edge Cases

### EC-3.1: PII False Positives
**Description:** Legitimate financial data mistaken for PII  
**Impact:** Valid queries blocked, poor user experience  
**Detection:** User complaints, blocked query analysis  
**Mitigation:** Refined PII patterns, context-aware detection

### EC-3.2: Intent Classification Errors
**Description:** Factual queries classified as advisory  
**Impact:** Unnecessary refusals, user frustration  
**Detection:** Refusal rate analysis, manual review  
**Mitigation:** Training data expansion, model recalibration

### EC-3.3: Confidence Gate Failures
**Description:** High confidence for incorrect chunks  
**Impact:** Wrong answers presented as factual  
**Detection:** Answer validation, user feedback loops  
**Mitigation:** Multiple confidence signals, answer verification

### EC-3.4: Groq API Issues
**Description:** Groq service unavailable or rate limited  
**Impact:** Generation failures, system downtime  
**Detection:** API health monitoring, error rate tracking  
**Mitigation:** Extractive fallback, multiple LLM providers

### EC-3.5: Post-Processor Over-Strictness
**Description:** Valid answers rejected by post-processing rules  
**Impact:** False negatives, reduced answer coverage  
**Detection:** Answer rejection rate analysis  
**Mitigation:** Rule refinement, exception handling

### EC-3.6: URL Policy Violations
**Description:** Generator produces non-whitelisted URLs  
**Impact:** Compliance violations, governance breaches  
**Detection:** URL validation scans, automated compliance checks  
**Mitigation:** Template enforcement, URL whitelist validation

### EC-3.7: Length Constraint Failures
**Description:** Generated answers exceed 3-sentence limit  
**Impact:** Policy violations, inconsistent responses  
**Detection:** Length validation, automated testing  
**Mitigation:** Hard truncation, length-aware generation

---

## Phase 4 - User Interface Edge Cases

### EC-4.1: Browser Compatibility Issues
**Description:** UI breaks on specific browsers or versions  
**Impact:** Poor user experience, accessibility issues  
**Detection:** Browser testing, user agent analysis  
**Mitigation:** Progressive enhancement, cross-browser testing

### EC-4.2: Network Latency
**Description:** Slow API responses cause UI timeouts  
**Impact:** User abandonment, poor perceived performance  
**Detection:** Response time monitoring, user behavior analysis  
**Mitigation:** Loading states, timeout handling, optimistic UI

### EC-4.3: Concurrent Requests
**Description:** Users submit multiple queries simultaneously  
**Impact:** Server overload, response mixing  
**Detection:** Request rate monitoring, session analysis  
**Mitigation:** Request queuing, rate limiting, deduplication

### EC-4.4: Malicious Input
**Description:** Users submit XSS, SQL injection, or other attacks  
**Impact:** Security vulnerabilities, data exposure  
**Detection:** Input validation logs, security scanning  
**Mitigation:** Input sanitization, output encoding, CSP headers

### EC-4.5: Accessibility Failures
**Description:** UI not accessible to users with disabilities  
**Impact:** Legal compliance issues, exclusion of users  
**Detection:** Accessibility testing, WCAG compliance scans  
**Mitigation:** ARIA labels, keyboard navigation, screen reader support

---

## Phase 5 - Evaluation, Compliance & Observability Edge Cases

### EC-5.1: Test Data Drift
**Description:** Evaluation questions become outdated or irrelevant  
**Impact:** False sense of system quality  
**Detection:** Answer accuracy monitoring, user feedback  
**Mitigation:** Regular test suite updates, golden set refresh

### EC-5.2: Compliance Rule Evolution
**Description:** Regulatory requirements change over time  
**Impact:** System becomes non-compliant  
**Detection:** Regulatory monitoring, compliance audits  
**Mitigation:** Rule update processes, automated compliance checks

### EC-5.3: Log Storage Exhaustion
**Description:** Log volumes exceed storage capacity  
**Impact:** Monitoring failures, audit trail loss  
**Detection:** Storage monitoring, log rotation analysis  
**Mitigation:** Log compaction, archival policies, storage scaling

### EC-5.4: Monitoring Alert Fatigue
**Description:** Too many false positive alerts  
**Impact:** Real issues ignored, alert desensitization  
**Detection:** Alert rate analysis, response time tracking  
**Mitigation:** Alert tuning, severity classification, alert grouping

### EC-5.5: Dashboard Performance Issues
**Description:** Observability dashboard becomes slow or unresponsive  
**Impact:** Poor operational visibility  
**Detection:** Dashboard response time monitoring  
**Mitigation:** Data aggregation, caching, query optimization

### EC-5.6: Evaluation Environment Differences
**Description:** Test environment doesn't match production  
**Impact:** Inconsistent behavior, false test results  
**Detection:** Environment comparison, configuration drift  
**Mitigation:** Infrastructure as code, environment parity

### EC-5.7: Source Change Detection Failures
**Description:** Content hash changes not detected properly  
**Impact:** Stale data, outdated answers  
**Detection:** Manual content audits, freshness monitoring  
**Mitigation:** Multiple hash strategies, change detection tuning

### EC-5.8: CI/CD Pipeline Failures
**Description:** Automated testing or deployment fails  
**Impact:** Development delays, quality issues  
**Detection:** Pipeline monitoring, build failure analysis  
**Mitigation:** Pipeline redundancy, manual override procedures

---

## Cross-Phase Systemic Edge Cases

### EC-SYS.1: Cascading Failures
**Description:** Failure in one phase triggers failures in downstream phases  
**Impact:** System-wide outage, data corruption  
**Detection:** System-wide monitoring, dependency mapping  
**Mitigation:** Circuit breakers, graceful degradation, isolation

### EC-SYS.2: Resource Exhaustion
**Description:** System resources (CPU, memory, disk) become exhausted  
**Impact:** Performance degradation, system crashes  
**Detection:** Resource monitoring, alerting systems  
**Mitigation:** Resource scaling, load balancing, auto-scaling

### EC-SYS.3: Data Consistency Issues
**Description:** Data becomes inconsistent across phases or components  
**Impact:** Incorrect answers, system unreliability  
**Detection:** Data validation, consistency checks  
**Mitigation:** Transactional operations, data reconciliation

### EC-SYS.4: Security Breaches
**Description:** Unauthorized access to system or data  
**Impact:** Data exposure, system compromise  
**Detection:** Security monitoring, intrusion detection  
**Mitigation:** Access controls, encryption, audit logging

### EC-SYS.5: Regulatory Compliance Changes
**Description:** Financial regulations or compliance requirements change  
**Impact:** System becomes non-compliant, legal issues  
**Detection:** Regulatory monitoring, compliance reviews  
**Mitigation:** Flexible architecture, rapid update processes

---

## Edge Case Handling Framework

### Detection Methods
1. **Automated Monitoring:** Real-time system health checks
2. **Log Analysis:** Pattern recognition in system logs
3. **User Feedback:** Direct user reports and complaints
4. **Testing:** Comprehensive test suites covering edge cases
5. **Manual Review:** Regular manual audits and inspections

### Mitigation Strategies
1. **Prevention:** Design systems to avoid edge cases
2. **Detection:** Early identification of edge case occurrence
3. **Response:** Automated or manual mitigation procedures
4. **Recovery:** System restoration and data recovery
5. **Prevention:** Learn from incidents to prevent recurrence

### Priority Classification
- **Critical:** System-wide impact, data loss, security breaches
- **High:** Significant user impact, compliance violations
- **Medium:** Partial functionality loss, performance degradation
- **Low:** Minor issues, cosmetic problems

### Response Time Targets
- **Critical:** < 5 minutes detection, < 30 minutes resolution
- **High:** < 15 minutes detection, < 2 hours resolution
- **Medium:** < 1 hour detection, < 4 hours resolution
- **Low:** < 4 hours detection, < 24 hours resolution

---

## Conclusion

This comprehensive edge case analysis ensures the Mutual Fund FAQ Assistant can handle unexpected scenarios gracefully while maintaining system reliability, compliance, and user trust. Regular review and updating of edge cases is essential as the system evolves and new challenges emerge.

Each edge case should have corresponding monitoring, alerting, and automated mitigation where possible. Human oversight and manual intervention procedures should be clearly documented for scenarios requiring judgment and decision-making beyond automated capabilities.
