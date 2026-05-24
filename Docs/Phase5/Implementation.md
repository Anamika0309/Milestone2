# Phase 5 — Evaluation, Compliance & Observability: Implementation Guide

**Status**: ✅ Completed & Tested  
**Duration**: 1 day

---

## CI / Automated Testing Setup

- **Test Suite path**: `tests/test_phase5_compliance.py`
- **Execution CLI**:
  ```bash
  # Run compliance test suites
  pytest tests/test_phase5_compliance.py -v
  ```

---

## Observability Logging Service

- **Module**: `src/mf_faq/utils/logger.py`
- **Design**:
  - Structured JSON Logging to `logs/audit.jsonl`.
  - Ensures raw user queries containing sensitive numbers are auto-hashed (`hashlib.sha256`) before printing, avoiding regulatory compliance exposure.
  - Periodic monitoring of log sizes to avoid storage exhausting.

---

## Operational Runbook & Maintenance

1. **Broken URL 404 Alerts**: Periodic health checker curl checks Groww URLs. If a URL returns 404, freezes indexing and alerts the ops team.
2. **Stable Hash Drift Checks**: Daily ingestion cron compares fetched HTML hash. If >=2 URLs drift, flags for human review before updating production database index files.
