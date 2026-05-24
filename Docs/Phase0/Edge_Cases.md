# Phase 0 — Foundation & Governance: Edge Cases

**Component**: `sources.yaml`, `refusal_intents.yaml`, `pii_patterns.yaml`, `disclaimer.txt`

---

## EC-0.1: Whitelisted Groww URL Returns 404

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `sources.yaml` → Fetcher (Phase 1.1) |

**Trigger**: A Groww page for one of the 5 schemes is restructured or deleted.

**Impact**: That scheme's corpus is unreachable. All queries about it return "I don't know".

**Mitigation**: Alert admin. Freeze refresh. Manually verify new URL before updating `sources.yaml`.

---

## EC-0.2: `sources.yaml` Entry Count ≠ 5

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `sources.yaml` |

**Trigger**: Manual edit adds a 6th scheme or removes one of the 5.

**Impact**: Off-corpus URL enters citation pool (>5), or a scheme has no corpus (<5).

**Mitigation**: CI gate: `assert len(schemes) == 5`. Reject deployment if count ≠ 5.

---

## EC-0.3: Refusal Regex Blocks Legitimate Factual Query

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | `refusal_intents.yaml` |

**Trigger**: `r".*lock.*"` matches "lock-in period" and refuses it as advisory.

**Impact**: Valid factual queries deflected. Recall drops below 90% pass bar.

**Mitigation**: Use `\b` word boundaries. Maintain factual keyword whitelist.

---

## EC-0.4: Refusal Canned Copy Contains Non-Whitelisted URL

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `refusal_intents.yaml` |

**Trigger**: Editor adds `https://www.amfiindia.com/` as an educational link in a canned response.

**Impact**: Every refusal leaks a non-whitelisted URL. CI compliance gate fails.

**Mitigation**: CI scans all canned copy for URLs not in `sources.yaml`. Block merge if found.

---

## EC-0.5: PII Pattern Gap — New Format Uncovered

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | `pii_patterns.yaml` |

**Trigger**: User submits UPI VPA (`user@hdfc`) which is not in `pii_patterns.yaml`.

**Impact**: PII leaks into retrieval pipeline and structured logs. Regulatory breach.

**Mitigation**: Quarterly regex audit. Zero-tolerance: all ambiguous formats must be blocked.

---

## EC-0.6: `disclaimer.txt` Emptied or Corrupted

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | `disclaimer.txt` |

**Trigger**: Bad git merge empties the file (0 bytes).

**Impact**: All responses emitted without mandatory disclaimer footer. Format check fails.

**Mitigation**: Startup SHA-256 check. Hardcoded fallback constant in post-processor.

---

## EC-0.7: YAML Syntax Error in Config Files

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | All `.yaml` config files |

**Trigger**: Missing colon, wrong indentation in any YAML file.

**Impact**: System crashes on startup. All queries fail with 500.

**Mitigation**: Pre-commit hook + CI step runs `yaml.safe_load()` on all config files.

---

## EC-0.8: Scheme ID Mismatch Between Config and Index

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | `sources.yaml` ↔ Phase 1 Indexer ↔ Phase 2 Scheme Resolver |

**Trigger**: `hdfc_midcap` renamed to `hdfc_mid_cap` in `sources.yaml` but old chunks still use old ID.

**Impact**: Scheme Resolver returns 0 filtered chunks → "I don't know" for all Mid Cap queries.

**Mitigation**: Full re-index mandatory after any scheme ID rename. Post-index ID consistency check.
