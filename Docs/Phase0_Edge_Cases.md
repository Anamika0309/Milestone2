# Phase 0 — Foundation & Governance: Edge Cases

**Source**: `Architecture.md` → Phase 0  
**Components**: `sources.yaml`, `refusal_intents.yaml`, `pii_patterns.yaml`, `disclaimer.txt`

The corpus for this project is locked to exactly these 5 URLs — no exceptions:
```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
```

---

## EC-0.1: Groww URL Structure Changes

| Field | Detail |
|:--|:--|
| **ID** | EC-0.1 |
| **Priority** | 🔴 Critical |
| **Component** | `sources.yaml` |
| **Architecture ref** | Phase 0 — Locked Corpus, Exit Criteria |

**Description**  
One or more of the 5 whitelisted Groww URLs changes slug or returns HTTP 404 (e.g., after a Groww site redesign or rebrand).

**Example**
```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth  →  404 Not Found
```

**Impact**  
- Corpus for that scheme becomes unreachable. Fetcher (Phase 1.1) fails for that URL.  
- Any cached corpus is now stale with no refresh path.

**Detection**  
- HTTP status monitoring on all 5 whitelisted URLs at each refresh cycle.  
- `meta.json` reports `http_status != 200` for the affected URL.

**Mitigation**  
- Freeze the corpus refresh for that scheme immediately — do not auto-substitute with any unverified URL.  
- Alert administrator. Manually identify the new URL, verify it is still an official Groww page, update `sources.yaml`, and re-run ingestion.  
- **Hard rule**: the replacement URL must pass the same whitelist governance review before being added to `sources.yaml`.

---

## EC-0.2: `sources.yaml` Contains Fewer or More Than 5 Entries

| Field | Detail |
|:--|:--|
| **ID** | EC-0.2 |
| **Priority** | 🔴 Critical |
| **Component** | `sources.yaml` |
| **Architecture ref** | Phase 0 — Exit Criteria: "sources.yaml contains exactly 5 entries" |

**Description**  
A manual edit accidentally adds a 6th URL (e.g., an AMFI page, AMC PDF, or extra Groww page) or removes one of the 5, leaving only 4.

**Example**
```yaml
# Accidentally added:
- id: hdfc_bluechip
  sources:
    - url: https://groww.in/mutual-funds/hdfc-bluechip-fund  # NOT in scope
```

**Impact**  
- If >5: off-corpus URL enters the citation pool, breaking the closed-corpus guarantee.  
- If <5: one scheme has no corpus → retrieval returns empty for all queries about it.

**Detection**  
- Startup validation: `assert len(sources.schemes) == 5`.  
- CI gate (Phase 5) counts entries and fails the build if count ≠ 5.

**Mitigation**  
- Schema-validate `sources.yaml` on every startup and in CI.  
- Reject any deployment where the URL count ≠ 5.

---

## EC-0.3: Refusal Pattern Matches Legitimate Factual Query

| Field | Detail |
|:--|:--|
| **ID** | EC-0.3 |
| **Priority** | 🟠 High |
| **Component** | `refusal_intents.yaml` |
| **Architecture ref** | Phase 0 — Refusal taxonomy; Phase 3 — Intent Classifier |

**Description**  
A regex in `refusal_intents.yaml` is too broad and matches a valid factual query, causing it to be refused instead of answered.

**Example**
```
User: "What is the lock-in period for ELSS?"
→ Pattern: r".*lock.*" matches "lock-in" → flagged as advisory → refused ❌
```

**Impact**  
- Valid factual queries are deflected. Users receive unhelpful refusals.  
- Recall drops on the factual Q&A eval suite (pass bar: ≥ 90%).

**Detection**  
- Factual golden-set queries failing as refusals in the Phase 5 eval harness.  
- Refusal rate > 10% on known-factual query set.

**Mitigation**  
- Use `\b` word-boundary anchors in all refusal regexes.  
- Maintain a whitelist of always-allowed factual keywords (`lock-in`, `expense ratio`, `exit load`, `minimum SIP`).  
- Run regression tests against `refusal_intents.yaml` after every change.

---

## EC-0.4: Refusal Canned Copy Contains a Non-Whitelisted URL

| Field | Detail |
|:--|:--|
| **ID** | EC-0.4 |
| **Priority** | 🔴 Critical |
| **Component** | `refusal_intents.yaml` |
| **Architecture ref** | Phase 0 — Citation rule; Phase 3 — URL Policy table |

**Description**  
The canned refusal copy in `refusal_intents.yaml` accidentally includes a non-whitelisted URL (e.g., an AMFI educational link, SEBI circular, or AMC website).

**Example**
```yaml
refusal_copy: "For more information, visit https://www.amfiindia.com/investor-corner"
# ❌ amfiindia.com is not in sources.yaml
```

**Impact**  
- Every refusal response leaks a non-whitelisted URL.  
- Phase 5 CI compliance gate fails: "URL ∉ sources.yaml" check triggers for all refusal responses.

**Detection**  
- CI compliance gate scans all canned copy text for `http(s)://` strings not in `sources.yaml`.  
- Refusal suite (Phase 5) — 100% pass bar — fails immediately.

**Mitigation**  
- All educational links in refusal copy must be one of the 5 whitelisted Groww URLs.  
- The scheme most relevant to the query is chosen; if none detected, use the first scheme URL as default.  
- CI scan validates all YAML canned copy before merge.

---

## EC-0.5: PII Pattern Gap — New Format Not Covered

| Field | Detail |
|:--|:--|
| **ID** | EC-0.5 |
| **Priority** | 🔴 Critical |
| **Component** | `pii_patterns.yaml` |
| **Architecture ref** | Phase 0 — PII deny-list; Phase 3 — PII guard |

**Description**  
A new PII format emerges that is not covered by the current regex patterns (e.g., new UPI VPA formats, masked Aadhaar with dashes, new card number formats).

**Example**
```
User: "My VPA is user@hdfc, what is the expense ratio?"
→ VPA not in pii_patterns.yaml → leaks through, stored in logs ❌
```

**Impact**  
- PII leaks into the retrieval pipeline and structured logs.  
- SEBI/AMFI regulatory compliance breach.

**Detection**  
- Periodic fuzz-test of PII detector with synthetic edge-case strings.  
- Log audit: scan for patterns resembling PII using an independent scanner.

**Mitigation**  
- Zero-tolerance policy: all ambiguous new formats must be added immediately.  
- PII patterns reviewed quarterly against UIDAI / NPCI / RBI format updates.

---

## EC-0.6: `disclaimer.txt` Empty or Corrupted

| Field | Detail |
|:--|:--|
| **ID** | EC-0.6 |
| **Priority** | 🟠 High |
| **Component** | `disclaimer.txt` |
| **Architecture ref** | Phase 0 — Deliverables; Phase 3 — Post-Processor footer check |

**Description**  
`disclaimer.txt` is accidentally emptied or corrupted (e.g., 0-byte file after a bad git merge), causing responses to be emitted without the required disclaimer footer.

**Impact**  
- All responses are non-compliant — no `"Facts-only. No investment advice."` footer.  
- Phase 5 format check (100% pass bar) fails immediately.

**Detection**  
- Startup integrity check: `assert os.path.getsize("disclaimer.txt") > 0`.  
- SHA-256 hash of `disclaimer.txt` compared against known-good value on startup.

**Mitigation**  
- Store disclaimer content as a hardcoded fallback constant in the post-processor.  
- CI pipeline validates `disclaimer.txt` is non-empty and hash-matches on every build.

---

## EC-0.7: `sources.yaml` YAML Parse Error

| Field | Detail |
|:--|:--|
| **ID** | EC-0.7 |
| **Priority** | 🔴 Critical |
| **Component** | All `.yaml` config files |
| **Architecture ref** | Phase 0 — Deliverables; entire system startup |

**Description**  
A manual edit introduces invalid YAML syntax, causing the system to crash on startup before any query is processed.

**Example**
```yaml
# Missing colon — invalid YAML
schemes
  - id: hdfc_mid_cap
```

**Impact**  
- System fails to initialize. All queries return unhandled 500 errors.

**Detection**  
- `python -c "import yaml; yaml.safe_load(open('sources.yaml'))"` in CI.  
- Pre-commit hook validates all YAML files before merge.

**Mitigation**  
- All YAML files validated against schema on every startup and CI run.  
- Versioned backup of last-known-good config files in `.github/` or a locked branch.

---

## EC-0.8: Scheme ID Mismatch Between Config and Indexed Chunks

| Field | Detail |
|:--|:--|
| **ID** | EC-0.8 |
| **Priority** | 🟠 High |
| **Component** | `sources.yaml` ↔ Phase 1 Indexer ↔ Phase 2 Scheme Resolver |
| **Architecture ref** | Phase 0 — `scheme_id`; Phase 2 — Scheme Resolver filter |

**Description**  
The `id` field in `sources.yaml` is renamed (e.g., `hdfc_midcap` → `hdfc_mid_cap`) but existing indexed chunks still carry the old ID.

**Impact**  
- Phase 2 Scheme Resolver cannot match `scheme_id` → returns 0 filtered chunks.  
- Confidence Gate triggers "I don't know" for all queries about that scheme.

**Detection**  
- Post-index integrity check: cross-reference all chunk `scheme_id` values against `sources.yaml` IDs.  
- Mismatch count > 0 triggers a build failure.

**Mitigation**  
- Enforce a strict migration: whenever a scheme ID is renamed, trigger a full re-index of all chunks for that scheme.  
- ID renaming requires a two-step process: update `sources.yaml` → re-run Phase 1 pipeline → verify integrity.
