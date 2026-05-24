# Governance Rules and Policies
# This document defines the governance framework for HDFC Mutual Fund FAQ Assistant
# All components must adhere to these rules strictly

## Core Governance Principles

### 1. Facts-Only Policy
- **Rule:** System must only provide factual, verifiable information
- **Scope:** No investment advice, recommendations, or opinions
- **Enforcement:** Intent classification + refusal composer
- **Exception:** None - policy is absolute

### 2. Closed Corpus Policy
- **Rule:** Only 5 whitelisted HDFC URLs may be ingested or cited
- **Sources:** Exactly the URLs defined in sources.yaml
- **Enforcement:** URL whitelist validation in Phase 3 post-processor
- **Exception:** None - policy is absolute

### 3. PII Protection Policy
- **Rule:** No personal data collection, storage, or processing
- **Scope:** PAN, Aadhaar, email, phone, OTP, account numbers
- **Enforcement:** PII detection + immediate rejection
- **Exception:** None - policy is absolute

### 4. Single Citation Policy
- **Rule:** Each response must contain exactly one source URL
- **Scope:** Factual answers get one citation, refusals get one educational link
- **Enforcement:** Post-processor URL count validation
- **Exception:** PII blocks get zero URLs

### 5. Response Length Policy
- **Rule:** Factual answers limited to maximum 3 sentences
- **Scope:** Applies to answer body before Source line
- **Enforcement:** Post-processor sentence count validation
- **Exception:** None - policy is absolute

## URL Governance Rules

### URL Whitelist Enforcement
```yaml
# Only these URLs are permitted:
allowed_urls:
  - https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
  - https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
```

### URL Citation Rules by Response Type
| Response Type | URL Count | URL Source | Example |
|---------------|------------|-------------|----------|
| Factual Answer | 1 | Retrieved chunk source | Source: [whitelisted URL] |
| Advisory Refusal | 1 | Most relevant scheme | Educational: [whitelisted URL] |
| PII Block | 0 | None | No URL provided |
| "Don't Know" | 0 | None | No URL provided |

### CI/CD Enforcement
- **Build Failure:** Any answer citing non-whitelisted URL
- **Automated Check:** URL whitelist validation in CI pipeline
- **Remediation:** Manual review + code fix before merge

## Content Governance Rules

### Factual Answer Requirements
1. **Source Verification:** Every fact must come from retrieved chunk
2. **Citation Accuracy:** Cited URL must contain the fact
3. **No Extrapolation:** Cannot infer beyond source content
4. **Numeric Accuracy:** Numbers must match source exactly
5. **No Synthesis:** Cannot combine facts from multiple chunks

### Refusal Requirements
1. **Polite Language:** Professional, helpful tone
2. **Educational Value:** Provide relevant official link
3. **Factual Limitation:** Clearly state facts-only constraint
4. **No Alternative Sources:** Never suggest non-whitelisted URLs
5. **Consistent Messaging:** Use approved templates

### PII Handling Requirements
1. **Immediate Rejection:** Block before any processing
2. **No Logging:** Never store PII in any log
3. **No Redaction:** Reject entirely, don't redact and continue
4. **User Education:** Explain why request was blocked
5. **Pattern Updates:** Regular PII pattern reviews

## Quality Governance Rules

### Response Validation Checklist
- [ ] Response type correctly identified (factual vs refusal)
- [ ] URL count matches policy requirements
- [ ] Sentence count ≤ 3 for factual answers
- [ ] All URLs are from approved whitelist
- [ ] No PII in any response or log
- [ ] No banned tokens (recommend, should invest, etc.)
- [ ] Footer present on factual answers
- [ ] Disclaimer included where required

### Content Quality Standards
1. **Accuracy:** Facts must match source exactly
2. **Clarity:** Simple, direct language
3. **Completeness:** Answer the specific question asked
4. **Consistency:** Same format across all responses
5. **Transparency:** Clear source attribution

## Operational Governance Rules

### Change Management
1. **URL Changes:** Require review board approval
2. **Pattern Updates:** Must be tested before deployment
3. **Policy Changes:** Documented with version control
4. **Rollback:** Ability to revert changes quickly

### Monitoring Requirements
1. **Compliance Alerts:** Immediate notification of violations
2. **Quality Metrics:** Track accuracy and user satisfaction
3. **Performance Monitoring:** Response times and availability
4. **Security Monitoring:** PII leakage detection

### Audit Requirements
1. **Response Audits:** Regular manual review of outputs
2. **Log Audits:** Ensure no PII in logs
3. **Configuration Audits:** Verify governance rules enforced
4. **Source Audits:** Confirm only whitelisted URLs used

## Enforcement Mechanisms

### Automated Enforcement
```python
# Example validation function
def validate_response(response, sources_whitelist):
    violations = []
    
    # Check URL count
    url_count = len(extract_urls(response))
    if response.type == 'factual' and url_count != 1:
        violations.append("factual_response_wrong_url_count")
    elif response.type == 'refusal' and url_count != 1:
        violations.append("refusal_response_wrong_url_count")
    elif response.type == 'pii_block' and url_count != 0:
        violations.append("pii_block_wrong_url_count")
    
    # Check URL whitelist
    for url in extract_urls(response):
        if url not in sources_whitelist:
            violations.append("non_whitelisted_url")
    
    # Check sentence count
    if response.type == 'factual' and count_sentences(response.text) > 3:
        violations.append("excessive_sentence_count")
    
    # Check PII
    if contains_pii(response.text):
        violations.append("pii_in_response")
    
    return violations
```

### Manual Review Process
1. **Daily Review:** Sample of responses checked manually
2. **Weekly Audit:** Full compliance review
3. **Monthly Assessment:** Governance rule effectiveness
4. **Quarterly Update:** Rules and patterns updated

## Compliance Matrix

| Requirement | Phase | Enforcement Method | Success Criteria |
|-------------|----------|-------------------|------------------|
| URL Whitelist | 0, 3, 5 | sources.yaml + CI validation | 100% compliance |
| PII Protection | 3, 5 | PII detection + blocking | 0 PII leakage |
| Response Length | 3 | Post-processor validation | ≤3 sentences |
| Single Citation | 3 | URL count validation | Exactly 1 URL |
| Facts-Only | 3 | Intent classification | 0 advice content |
| Source Attribution | 3 | Citation validation | 100% accurate |

## Version Control and Documentation

### Rule Versioning
- **Current Version:** 1.0
- **Update Process:** Semantic versioning
- **Change Log:** Document all modifications
- **Review Required:** All changes need approval

### Documentation Requirements
1. **Rule Documentation:** This file always current
2. **Implementation Notes:** Code comments explain enforcement
3. **Training Materials:** Team education on governance
4. **Audit Trails:** All changes tracked and reviewable

---

## Conclusion

These governance rules ensure the HDFC Mutual Fund FAQ Assistant operates within strict compliance boundaries while providing valuable factual information to users. All team members must understand and implement these rules consistently across all system components.

Regular reviews and updates of these rules are essential as regulations evolve and new edge cases emerge.
