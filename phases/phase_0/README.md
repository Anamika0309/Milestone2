# Phase 0: Governance & Foundation

This directory establishes the structural compliance boundaries, policies, and static data assets for the **Facts-Only Mutual Fund FAQ Assistant**.

---

## 🔒 Locked Corpus — These 5 URLs Only

> **HARD CONSTRAINT:** For this project, we ingest, process, and cite **ONLY** the following 5 Groww URLs. No other URLs may ever appear in any response, index, or log.

```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
```

| # | Scheme | Category |
|:--|:--|:--|
| 1 | HDFC Mid Cap Fund — Direct Growth | Mid Cap |
| 2 | HDFC Equity Fund — Direct Growth | Flexi Cap |
| 3 | HDFC Focused Fund — Direct Growth | Focused |
| 4 | HDFC ELSS Tax Saver — Direct Plan Growth | ELSS |
| 5 | HDFC Large Cap Fund — Direct Growth | Large Cap |

---

## What is in this Folder?

1. **`sources.yaml`**: The source registry defining the strict, closed corpus of exactly 5 whitelisted Groww URLs above.
2. **`refusal_intents.yaml`**: Regex intent classifiers and canned response templates to deflect advisory, prediction, performance, tax, or comparative queries.
3. **`pii_patterns.yaml`**: Pre-compiled regex definitions and redaction policies to detect, log, and immediately block Indian personal data (PAN, Aadhaar, email, mobile phone, OTP, cards, etc.).
4. **`disclaimer.txt`**: The constant, mandatory disclaimer text appended to every compliant response: `Facts-only. No investment advice.`

## Governance Principles Enforced

* **Strict Closed Corpus**: The system only operates on and cites the 5 allowed URLs above — nothing else.
* **Defensive PII Guard**: Any queries containing personal identifiers are blocked instantly with 0 URLs returned.
* **No Unsolicited Advice**: Any advisory or speculative inquiries are redirected to educational resources using the refusal templates.
* **Single Citation Policy**: Compliant responses must cite exactly 1 whitelisted URL (except PII and general "Don't know" blocks which cite 0).
* **Length Restraints**: Factual responses are limited to at most 3 sentences.

