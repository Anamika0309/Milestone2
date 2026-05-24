# Phase 5 — Evaluation, Compliance & Observability: Edge Cases

**Component**: `test_phase5_compliance.py`, `logger.py`, CI/CD workflow

---

## EC-5.1: Test Data / Golden Q&A Drift

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | pytest suite (`test_phase5_compliance.py`) |

**Trigger**: Fund details (e.g. exit load) change on Groww, making the golden test questions outdated.

**Impact**: Tests fail on correct code, or pass on incorrect code due to mismatch.

**Detection**: Scheduled test suite failures, content hash updates.

**Mitigation**: Dynamic verification against raw snapshots or automated golden set generation.

---

## EC-5.2: Compliance Rule Evolution

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | CI/CD pipeline |

**Trigger**: SEBI/AMFI updates guidelines, necessitating new guardrails or stricter limits.

**Impact**: The app becomes non-compliant despite passing old test suites.

**Detection**: Regulatory audits, system compliance score drops.

**Mitigation**: Modular guardrail structure, easy-to-update YAML files for intent and PII patterns.

---

## EC-5.3: Log Storage Exhaustion

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | Logger service (`logger.py`) |

**Trigger**: Large traffic volume generates millions of audit log rows.

**Impact**: Disk partition fills up, crashing the application.

**Detection**: Disk space threshold warning.

**Mitigation**: Structured JSON logging, daily log rotation, and automatic compression (gzipped backups).

---

## EC-5.4: Monitoring Alert Fatigue

| | |
|:--|:--|
| **Priority** | 🟡 Medium |
| **Component** | Ops alerting |

**Trigger**: Too many non-critical alerts triggered by network blips or minor latencies.

**Impact**: Critical errors ignored by the development team.

**Detection**: Average alert response time increases.

**Mitigation**: Tiered alerting (info, warning, critical), deduplication, and anomaly detection rather than static thresholds.

---

## EC-5.5: Log Leakage of Hashed Indian PII

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | Logger service (`logger.py`) |

**Trigger**: User inputs PII which is saved directly in plain-text logs.

**Impact**: Compliance breach (sensitive data exposure).

**Detection**: Automated pre-logging regex scanner.

**Mitigation**: Pre-log regex parsing; hash PII values (SHA-256 with salt) or replace with `[REDACTED]`.
