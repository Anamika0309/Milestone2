# Phase 0 — Foundation & Governance: Architecture

**Status**: ✅ Completed  
**Duration**: 0.5 day  
**Purpose**: Lock down scope, sources, and guardrails before writing any code.

---

## 🔒 Locked Corpus — Exactly These 5 URLs

> **HARD CONSTRAINT**: For this project, ONLY these 5 URLs are ingested, processed, or cited. No exceptions.

```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
```

## Scheme Registry

| # | Scheme | Category | URL |
|:--|:--|:--|:--|
| 1 | HDFC Mid Cap Fund — Direct Growth | Mid Cap | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |
| 2 | HDFC Equity Fund — Direct Growth | Flexi Cap | `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| 3 | HDFC Focused Fund — Direct Growth | Focused | `https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth` |
| 4 | HDFC ELSS Tax Saver — Direct Plan Growth | ELSS | `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| 5 | HDFC Large Cap Fund — Direct Growth | Large Cap | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |

## Components

| File | Purpose |
|:--|:--|
| `config/sources.yaml` | Registry of exactly 5 whitelisted URLs with scheme metadata |
| `config/refusal_intents.yaml` | Regex patterns + canned copy for non-factual query deflection |
| `config/pii_patterns.yaml` | Regex deny-list for Indian PII (PAN, Aadhaar, email, phone, OTP) |
| `config/disclaimer.txt` | Mandatory footer: `"Facts-only. No investment advice."` |

## Architectural Principles Established Here

1. **Facts-over-Intelligence** — retrieval grounds every answer
2. **Single source of truth** — exactly one citation URL per response
3. **Closed corpus** — only these 5 whitelisted URLs are ever ingested or cited
4. **Refusal by default** — advisory/opinion queries deflected with educational redirect
5. **PII-free** — no PAN, Aadhaar, OTPs, emails, or phones collected/logged/processed
6. **Determinism > Creativity** — low temperature, hard answer-length caps (≤ 3 sentences)
7. **Auditability** — every response traceable to chunk, document, URL, and timestamp

## Citation Rules (enforced by Phase 3)

| Situation | URLs in reply |
|:--|:--|
| PII detected | **Zero** — `pii_block` template only |
| Low confidence / don't know | **Zero** — `dont_know_without_link` only |
| Advisory/comparison refusal | **Exactly one** — matching whitelisted Groww URL |
| Factual answer | **Exactly one** — `source_url` from top retrieved chunk |

## `sources.yaml` Structure

```yaml
schemes:
  - id: hdfc_mid_cap
    name: HDFC Mid Cap Fund - Direct Growth
    category: Mid Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
        doc_type: Product_Page
  - id: hdfc_equity
    name: HDFC Equity Fund - Direct Growth
    category: Flexi Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
        doc_type: Product_Page
  - id: hdfc_focused
    name: HDFC Focused Fund - Direct Growth
    category: Focused
    sources:
      - url: https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
        doc_type: Product_Page
  - id: hdfc_elss
    name: HDFC ELSS Tax Saver - Direct Plan Growth
    category: ELSS
    sources:
      - url: https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
        doc_type: Product_Page
  - id: hdfc_large_cap
    name: HDFC Large Cap Fund - Direct Growth
    category: Large Cap
    sources:
      - url: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
        doc_type: Product_Page
# Hard rule: any URL not in this file MUST NOT appear in any answer.
```

## Exit Criteria

- [ ] `sources.yaml` contains exactly 5 entries — these 5 Groww URLs — nothing else
- [ ] Reviewer can diff URL list against problem statement and confirm 1:1 match
- [ ] Refusal copy and "I don't know" copy never reference any URL outside the 5
- [ ] All YAML files pass schema validation
- [ ] `disclaimer.txt` is non-empty and hash-verified
