# Phase 0 — Foundation & Governance: Implementation Guide

**Status**: ✅ Completed  
**Module path**: `phases/phase_0/`

---

## Files Implemented

| File | Location | Status |
|:--|:--|:--|
| `sources.yaml` | `phases/phase_0/sources.yaml` | ✅ Done |
| `refusal_intents.yaml` | `phases/phase_0/refusal_intents.yaml` | ✅ Done |
| `pii_patterns.yaml` | `phases/phase_0/pii_patterns.yaml` | ✅ Done |
| `disclaimer.txt` | `phases/phase_0/disclaimer.txt` | ✅ Done |

## Locked URLs (Do Not Change)

```
https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
```

## How `sources.yaml` Is Consumed

- **Phase 1.1 Fetcher**: reads `sources.yaml` to get the 5 URLs to fetch
- **Phase 2 Scheme Resolver**: reads scheme IDs and aliases to match query → scheme
- **Phase 3 Post-Processor**: reads all 5 URLs to build the citation whitelist
- **Phase 5 CI Gate**: reads `sources.yaml` to validate every generated answer's URL

## How `refusal_intents.yaml` Works

```
User query
    │
    ▼
Phase 3 Intent Classifier
    │ loads refusal_intents.yaml patterns
    ▼
If match → Refusal Composer
    │ uses canned copy from refusal_intents.yaml
    │ appends ONE whitelisted Groww URL (scheme-matched)
    ▼
Response returned (no retrieval done)
```

## How `pii_patterns.yaml` Works

```
User query
    │
    ▼
Phase 3 PII Guard (first check — before everything else)
    │ loads pii_patterns.yaml regex list
    ▼
If PII detected → pii_block template
    │ ZERO URLs in response
    │ Query NOT forwarded to retrieval
    │ Query NOT stored in logs (hashed only)
    ▼
Response returned
```

## Validation Checklist

```bash
# 1. Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('phases/phase_0/sources.yaml'))"
python -c "import yaml; yaml.safe_load(open('phases/phase_0/refusal_intents.yaml'))"
python -c "import yaml; yaml.safe_load(open('phases/phase_0/pii_patterns.yaml'))"

# 2. Check exactly 5 URL entries
python -c "
import yaml
d = yaml.safe_load(open('phases/phase_0/sources.yaml'))
assert len(d['schemes']) == 5, f'Expected 5, got {len(d[\"schemes\"])}'
print('OK: exactly 5 schemes')
"

# 3. Check disclaimer is non-empty
python -c "assert open('phases/phase_0/disclaimer.txt').read().strip(), 'Empty!'; print('OK')"
```
