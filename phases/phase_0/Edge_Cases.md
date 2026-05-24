# Phase 0: Governance & Configuration — Edge Cases

This document lists all known edge cases specific to the **Phase 0 Governance** layer — the configuration files that control corpus scope, PII detection, refusal intents, and disclaimer enforcement.

---

## EC-0.1: Source URL Structure Changes

| Field | Detail |
|---|---|
| **ID** | EC-0.1 |
| **Priority** | 🔴 Critical |
| **Component** | `sources.yaml` |

**Description**  
One or more of the 5 whitelisted Groww URLs changes path structure (e.g., Groww rebrand, URL slug change) or returns HTTP 404.

**Example Trigger**
```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth  →  404 Not Found
```

**Impact**  
- Corpus becomes stale/incomplete.  
- Retrieval returns outdated or empty results for the affected scheme.

**Detection**  
- HTTP status monitoring on all 5 whitelisted URLs.  
- Content hash drift → 0 bytes returned.

**Mitigation**  
- Alert administrator immediately.  
- Freeze corpus refresh until `sources.yaml` is manually updated and re-verified.  
- Do **not** auto-substitute with any unlisted URL.

---

## EC-0.2: Refusal Intent Pattern Conflicts

| Field | Detail |
|---|---|
| **ID** | EC-0.2 |
| **Priority** | 🟠 High |
| **Component** | `refusal_intents.yaml` |

**Description**  
A regex pattern in `refusal_intents.yaml` overlaps with a factual query category, causing valid factual questions to be refused.

**Example Trigger**
```
User: "What is the lock-in period for ELSS?"
→ Pattern: r".*lock.*" matches advisory regex, blocked incorrectly.
```

**Impact**  
- Legitimate factual queries get deflected.  
- Recall drops. Users receive unhelpful refusals.

**Detection**  
- Track false-refusal rate in eval suite.  
- Golden-set factual queries failing as refusals.

**Mitigation**  
- Refine regex with word-boundary anchors (`\b`).  
- Add whitelist of explicitly-allowed factual keywords.
- Run regression tests after every `refusal_intents.yaml` update.

---

## EC-0.3: PII Pattern Gaps — New Document Formats

| Field | Detail |
|---|---|
| **ID** | EC-0.3 |
| **Priority** | 🔴 Critical |
| **Component** | `pii_patterns.yaml` |

**Description**  
New PII formats emerge that are not covered by current regex patterns (e.g., new masked Aadhaar format `XXXX-XXXX-1234`, new UPI VPA formats).

**Example Trigger**
```
User query: "My VPA is user@hdfc, what fund is best?"
→ VPA not in pii_patterns.yaml → leaks through undetected.
```

**Impact**  
- PII leaks into system logs or response generation pipeline.  
- Compliance/SEBI/AMFI regulatory breach.

**Detection**  
- Periodic regex audit against UIDAI/NPCI new format announcements.  
- Fuzz test PII detector with synthetic edge-case strings.

**Mitigation**  
- Add new regex patterns to `pii_patterns.yaml` immediately.  
- Run full PII sweep on recent query logs (redacted check).  
- Zero-tolerance policy: **all ambiguous patterns must be blocked**.

---

## EC-0.4: Disclaimer Text Modification

| Field | Detail |
|---|---|
| **ID** | EC-0.4 |
| **Priority** | 🟡 Medium |
| **Component** | `disclaimer.txt` |

**Description**  
`disclaimer.txt` gets accidentally truncated or overwritten, causing the disclaimer footer to be empty or malformed in responses.

**Example Trigger**
```
disclaimer.txt → empty (0 bytes)
→ Every response emitted without the required disclaimer footer.
```

**Impact**  
- All responses are non-compliant.  
- Every response violates the "facts-only" disclosure requirement.

**Detection**  
- Startup integrity check: verify `disclaimer.txt` is non-empty and matches expected SHA-256.  
- Post-generation compliance scanner validates footer presence.

**Mitigation**  
- Store disclaimer content as a hardcoded fallback constant in the post-processor.  
- Add file integrity check to CI pipeline.

---

## EC-0.5: Schema Validation Failures in YAML Files

| Field | Detail |
|---|---|
| **ID** | EC-0.5 |
| **Priority** | 🟠 High |
| **Component** | All `.yaml` config files |

**Description**  
Manual edits to `sources.yaml`, `refusal_intents.yaml`, or `pii_patterns.yaml` introduce invalid YAML syntax, causing the system to crash on startup.

**Example Trigger**
```yaml
# Missing colon causes parse error
schemes
  - id: hdfc_mid_cap
```

**Impact**  
- System fails to initialize.  
- All queries return 500/unhandled errors.

**Detection**  
- YAML schema validation on every startup.  
- CI pipeline runs `python -c "import yaml; yaml.safe_load(open(f))"` on all config files.

**Mitigation**  
- Validate all YAML files before deploying.  
- Keep a versioned backup of last-known-good config files.

---

## EC-0.6: Scheme ID Mismatch Between Config and Index

| Field | Detail |
|---|---|
| **ID** | EC-0.6 |
| **Priority** | 🟠 High |
| **Component** | `sources.yaml` ↔ Ingestion / Retrieval |

**Description**  
The scheme `id` field in `sources.yaml` is renamed (e.g., `hdfc_midcap` → `hdfc_mid_cap`) but existing indexed chunks still carry the old ID, causing retrieval to return 0 results for that scheme.

**Example Trigger**
```yaml
# sources.yaml updated:
id: hdfc_mid_cap   # was: hdfc_midcap
# But all indexed chunks still tagged: scheme_id = "hdfc_midcap"
```

**Impact**  
- Scheme resolver cannot match query → 0 chunks returned.  
- Confidence gate triggers "I don't know" for all Mid Cap queries.

**Detection**  
- Post-index integrity check: cross-reference all chunk `scheme_id` values against `sources.yaml`.

**Mitigation**  
- Enforce a strict migration step: re-index all chunks whenever a scheme ID is renamed.  
- Add automated ID consistency check to the indexer health report.
